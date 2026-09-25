"""Webcam -> MediaPipe -> gesto estável, em duas threads daemon. Não importa pygame.

_Capture lê a câmera sem parar e guarda só o frame mais novo: nunca há fila no driver.
HandTracker pega o frame mais novo, detecta em 320x240 e classifica.
Atributos públicos são reatribuídos inteiros a cada frame (tuplas/strings/bytes),
então o loop do pygame lê sem lock.
"""
import os
import threading
import time

from .gestures import SIDES, Debouncer, classify, load_calibration

MODEL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "assets", "hand_landmarker.task")
DETECT_SIZE = (320, 240)   # o modelo usa 224x224 por dentro; mais que isso só custa tempo
PREVIEW_SIZE, BIG_SIZE = (200, 150), (480, 360)


class _Capture(threading.Thread):
    def __init__(self, cap):
        super().__init__(daemon=True)
        self.cap = cap
        self.latest = None   # (frame BGR, t_capture)
        self.failed = False
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            ok, frame = self.cap.read()
            if not ok:
                self.failed = True
                break
            self.latest = (frame, time.monotonic())

    def stop(self):
        self._stop.set()


class HandTracker(threading.Thread):
    def __init__(self, camera=0):
        super().__init__(daemon=True)
        self.camera = camera
        self.thresh = load_calibration()
        self.debouncers = {s: Debouncer() for s in SIDES}
        # por lado ("L" = mão da esquerda da tela, "R" = da direita); tudo reatribuído inteiro por frame
        self.gesture = {s: "NONE" for s in SIDES}
        self.stable = {s: "NONE" for s in SIDES}
        self.fingers = {s: (False,) * 5 for s in SIDES}
        self.metrics = {s: (0.0,) * 5 for s in SIDES}
        self.landmarks = {}        # lado -> [(x, y) normalizados], só das mãos vistas neste frame
        self.preview = self.preview_big = None   # (bytes RGB, (w, h))
        self.want_big = False      # a cena de calibração liga; evita um resize a mais no jogo
        self.fps = 0.0
        self.latency_ms = 0.0      # captura -> gesto classificado
        self.error = None
        self.status = "iniciando"
        self.ready = False
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def _update_hands(self, res, now):
        """Atribui lado a cada mão vista e classifica. 2 mãos: a mais à esquerda da tela é "L".
        1 mão: usa a handedness do MediaPipe (a imagem já está espelhada, então o rótulo bate)."""
        hands = [[(p.x, p.y) for p in h] for h in res.hand_landmarks]
        if len(hands) >= 2:
            hands = sorted(hands[:2], key=lambda lm: lm[0][0])
            seen = dict(zip(SIDES, hands))
        elif hands:
            label = res.handedness[0][0].category_name if res.handedness and res.handedness[0] else ""
            side = "L" if label == "Left" else "R" if label == "Right" else ("L" if hands[0][0][0] < 0.5 else "R")
            seen = {side: hands[0]}
        else:
            seen = {}
        gesture, fingers, metrics = dict(self.gesture), dict(self.fingers), dict(self.metrics)
        for side in SIDES:
            if side in seen:
                gesture[side], fingers[side], metrics[side] = classify(seen[side], self.thresh)
            else:
                gesture[side] = "NONE"
        self.landmarks = seen
        self.gesture, self.fingers, self.metrics = gesture, fingers, metrics
        self.stable = {s: self.debouncers[s].update(gesture[s], now) for s in SIDES}

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
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.status = "carregando modelo"
        try:
            landmarker = HandLandmarker.create_from_options(HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=MODEL), running_mode=RunningMode.VIDEO,
                num_hands=2, min_hand_detection_confidence=0.5, min_tracking_confidence=0.5))
        except Exception as e:  # noqa: BLE001 - qualquer falha do modelo vira mensagem na tela
            self.error = f"falha ao carregar o modelo: {e}"
            cap.release()
            return
        capture = _Capture(cap)
        capture.start()
        self.ready, self.status = True, "ok"
        t0 = time.monotonic()
        last_fps, frames, last_frame = t0, 0, None
        try:
            while not self._stop.is_set():
                item = capture.latest
                if item is None or item is last_frame:
                    if capture.failed:
                        self.error = "camera parou de responder"
                        break
                    time.sleep(0.002)
                    continue
                last_frame = item
                frame, t_cap = item
                small = cv2.resize(cv2.flip(frame, 1), DETECT_SIZE)  # espelho + tamanho de detecção
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                now = time.monotonic()
                res = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                                                  int((now - t0) * 1000))
                self._update_hands(res, now)
                self.latency_ms = (time.monotonic() - t_cap) * 1000
                self.preview = (cv2.resize(rgb, PREVIEW_SIZE).tobytes(), PREVIEW_SIZE)
                if self.want_big:
                    self.preview_big = (cv2.resize(rgb, BIG_SIZE, interpolation=cv2.INTER_NEAREST).tobytes(), BIG_SIZE)
                frames += 1
                if now - last_fps >= 1:
                    self.fps, frames, last_fps = frames / (now - last_fps), 0, now
        except Exception as e:  # noqa: BLE001
            self.error = f"erro na camera: {e}"
        finally:
            capture.stop()
            cap.release()
            landmarker.close()
            self.ready = False
