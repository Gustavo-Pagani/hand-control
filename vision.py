"""Webcam -> MediaPipe -> gesto estável. Não importa pygame.

Gestos: OPEN (parado), INDEX (frente), THUMB (trás), FIST (pulo), NONE (sem mão / indefinido).
Rodar `python vision.py` abre uma janela OpenCV de depuração.
"""
import json
import math
import os
import threading
import time

DIR = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(DIR, "assets", "hand_landmarker.task")
CALIB_FILE = os.path.join(DIR, "calibration.json")
THRESH = {"fingers": 1.3, "thumb": 1.0}
DEBOUNCE = 0.2   # s: gesto precisa ficar constante antes de virar comando
GESTURES = ("OPEN", "INDEX", "THUMB", "FIST", "NONE")
FINGER_NAMES = ("polegar", "indicador", "medio", "anelar", "minimo")
# ponta e articulação PIP de cada dedo (índices dos 21 landmarks do MediaPipe)
TIPS, PIPS = (8, 12, 16, 20), (6, 10, 14, 18)
CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
               (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]


def load_calibration():
    try:
        with open(CALIB_FILE, encoding="utf-8") as f:
            return {**THRESH, **json.load(f)}
    except (OSError, ValueError):
        return dict(THRESH)


def save_calibration(thresh):
    with open(CALIB_FILE, "w", encoding="utf-8") as f:
        json.dump(thresh, f, indent=2)


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def metrics(lm):
    """5 razões (polegar, ind, med, an, min). Invariantes a rotação e escala da mão."""
    wrist, palm = lm[0], _dist(lm[0], lm[9]) or 1e-6
    thumb = _dist(lm[4], lm[17]) / palm
    fingers = [_dist(lm[t], wrist) / (_dist(lm[p], wrist) or 1e-6) for t, p in zip(TIPS, PIPS)]
    return (thumb, *fingers)


def classify(lm, thresh=THRESH):
    """-> (gesto, dedos estendidos (5 bools), métricas (5 floats))."""
    m = metrics(lm)
    ext = (m[0] > thresh["thumb"], *(x > thresh["fingers"] for x in m[1:]))
    thumb, index, others = ext[0], ext[1], ext[2:]
    if index and all(others):
        g = "OPEN"
    elif not thumb and index and not any(others):
        g = "INDEX"
    elif thumb and not index and not any(others):
        g = "THUMB"
    elif not thumb and not index and not any(others):
        g = "FIST"
    else:
        g = "NONE"
    return g, ext, m


class Debouncer:
    def __init__(self, hold=DEBOUNCE):
        self.hold = hold
        self.candidate = self.stable = "NONE"
        self.since = 0.0

    def update(self, gesture, now):
        if gesture != self.candidate:
            self.candidate, self.since = gesture, now
        elif now - self.since >= self.hold:
            self.stable = gesture
        return self.stable


class HandTracker(threading.Thread):
    """Thread daemon. Atributos públicos são reatribuídos inteiros a cada frame
    (tuplas/strings/bytes), então o loop do pygame lê sem lock."""

    def __init__(self, camera=0, preview_size=(200, 150), big_size=(480, 360)):
        super().__init__(daemon=True)
        self.camera = camera
        self.preview_size, self.big_size = preview_size, big_size
        self.thresh = load_calibration()
        self.debouncer = Debouncer()
        self.gesture = self.stable = "NONE"
        self.fingers = (False,) * 5
        self.metrics = (0.0,) * 5
        self.landmarks = None      # [(x, y) normalizados] da 1ª mão, ou None
        self.hands = 0
        self.preview = self.preview_big = None   # (bytes RGB, (w, h))
        self.fps = 0.0
        self.error = None
        self.status = "iniciando"
        self.ready = False
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        self.status = "carregando mediapipe"
        try:
            import cv2
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
        except ImportError as e:
            self.error = f"mediapipe/opencv nao instalado ({e.name})"
            return
        if not os.path.exists(MODEL):
            self.error = "modelo hand_landmarker.task nao encontrado em assets/"
            return
        self.status = "abrindo camera"
        cap = cv2.VideoCapture(self.camera, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.error = "camera nao encontrada"
            return
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.status = "carregando modelo"
        try:
            landmarker = HandLandmarker.create_from_options(HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=MODEL), running_mode=RunningMode.VIDEO,
                num_hands=2, min_hand_detection_confidence=0.6, min_tracking_confidence=0.5))
        except Exception as e:  # noqa: BLE001 - qualquer falha do modelo vira mensagem na tela
            self.error = f"falha ao carregar o modelo: {e}"
            cap.release()
            return
        self.ready = True
        self.status = "ok"
        t0 = time.monotonic()
        last, frames = t0, 0
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    self.error = "camera parou de responder"
                    break
                frame = cv2.flip(frame, 1)  # espelho: mover a mão para a direita move para a direita na tela
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                now = time.monotonic()
                res = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                                                  int((now - t0) * 1000))
                self.hands = len(res.hand_landmarks)
                if self.hands:
                    lm = [(p.x, p.y) for p in res.hand_landmarks[0]]
                    self.gesture, self.fingers, self.metrics = classify(lm, self.thresh)
                    self.landmarks = lm
                else:
                    self.gesture, self.landmarks = "NONE", None
                self.stable = self.debouncer.update(self.gesture, now)
                self.preview = (cv2.resize(rgb, self.preview_size).tobytes(), self.preview_size)
                self.preview_big = (cv2.resize(rgb, self.big_size).tobytes(), self.big_size)
                frames += 1
                if now - last >= 1:
                    self.fps, frames, last = frames / (now - last), 0, now
        except Exception as e:  # noqa: BLE001
            self.error = f"erro na camera: {e}"
        finally:
            cap.release()
            landmarker.close()
            self.ready = False


if __name__ == "__main__":
    import cv2
    import numpy as np

    tr = HandTracker()
    tr.start()
    while True:
        if tr.error:
            print(tr.error)
            break
        if tr.preview_big:
            data, (w, h) = tr.preview_big
            img = cv2.cvtColor(np.frombuffer(data, np.uint8).reshape(h, w, 3), cv2.COLOR_RGB2BGR).copy()
            if tr.landmarks:
                for a, b in CONNECTIONS:
                    cv2.line(img, (int(tr.landmarks[a][0] * w), int(tr.landmarks[a][1] * h)),
                             (int(tr.landmarks[b][0] * w), int(tr.landmarks[b][1] * h)), (0, 255, 0), 1)
            cv2.putText(img, f"{tr.gesture} -> {tr.stable}  {tr.fps:.0f} fps", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.imshow("vision debug (q sai)", img)
        if cv2.waitKey(30) & 0xFF == ord("q"):
            break
    tr.stop()
