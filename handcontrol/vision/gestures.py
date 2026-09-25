"""Landmarks da mão -> gesto. Regras geométricas, sem rede neural, sem pygame.

Duas mãos. Esquerda: INDEX (frente), THUMB (trás). Direita: INDEX (pulo). FIST/OPEN/NONE = parado.
Menus: número de dedos na direita escolhe o item; sinal de OK (qualquer mão) segurado = confirmar;
THREE na esquerda = voltar.
O polegar é ignorado quando o indicador está levantado: é o dedo que o modelo mais erra.
"""
import json
import math
import os

CALIB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "calibration.json")
THRESH = {"fingers": 1.3, "thumb": 1.0}
DEBOUNCE = 0.08   # s: gesto precisa ficar constante antes de virar comando (2-3 frames a 30 fps)
GESTURES = ("OK", "FIVE", "OPEN", "INDEX", "ONE", "TWO", "THREE", "THUMB", "FIST", "NONE")
ONE_FINGER = ("INDEX", "ONE")   # um dedo so levantado (qualquer um): pulo
OK_PINCH = 0.35   # ponta do polegar e do indicador mais perto que isso (em palmas) = círculo do OK
COUNT = {"INDEX": 1, "ONE": 1, "TWO": 2, "THREE": 3, "OPEN": 4, "FIVE": 5}   # dedos levantados -> número
SIDES = ("L", "R")
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
    middle, ring, pinky = others
    palm = _dist(lm[0], lm[9]) or 1e-6
    if all(others) and _dist(lm[4], lm[8]) / palm < OK_PINCH:   # polegar encosta no indicador, resto aberto
        g = "OK"
    elif index and all(others):
        g = "FIVE" if thumb else "OPEN"
    elif index and not any(others):          # polegar tanto faz
        g = "INDEX"
    elif not index and sum(others) == 1:     # um outro dedo sozinho (medio, anelar ou minimo)
        g = "ONE"
    elif index and middle and not ring and not pinky:
        g = "TWO"
    elif index and middle and ring and not pinky:
        g = "THREE"
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
