"""Desenha o preview da webcam com os landmarks das duas mãos e o comando de cada uma."""
import pygame

from .ui import BLUE, DIM, GREEN, PANEL, RED, WHITE, YELLOW, draw_text
from .vision import CONNECTIONS

# (cor, rótulo) por lado e gesto estável
LEFT = {"INDEX": (GREEN, "frente"), "THUMB": (BLUE, "tras"), "NONE": (RED, "sem mao"), "THREE": (BLUE, "tres: voltar"),
        "FIST": (DIM, "punho"), "OK": (YELLOW, "OK")}
RIGHT = {"INDEX": (YELLOW, "1 / pulo"), "ONE": (YELLOW, "1 / pulo"), "TWO": (YELLOW, "2"), "THREE": (YELLOW, "3"), "OPEN": (YELLOW, "4"),
         "FIVE": (YELLOW, "5"), "NONE": (RED, "sem mao"), "FIST": (DIM, "punho"), "OK": (YELLOW, "OK")}
SIDE_NAME = {"L": "E", "R": "D"}


def describe(side, gesture):
    return (LEFT if side == "L" else RIGHT).get(gesture, (DIM, "parado"))


def draw_camera(screen, tracker, x, y, big=False):
    data = tracker.preview_big if big else tracker.preview
    if tracker.error or not data:
        w, h = (480, 360) if big else (200, 150)
        pygame.draw.rect(screen, PANEL, (x, y, w, h))
        pygame.draw.rect(screen, RED if tracker.error else DIM, (x, y, w, h), 3)
        draw_text(screen, tracker.error or f"camera: {tracker.status}...", 22 if big else 18,
                  RED if tracker.error else DIM, (x + w // 2, y + h // 2))
        return
    raw, (w, h) = data
    screen.blit(pygame.image.frombuffer(raw, (w, h), "RGB"), (x, y))
    pygame.draw.line(screen, DIM, (x + w // 2, y), (x + w // 2, y + h), 1)
    for side, lm in tracker.landmarks.items():
        color, _ = describe(side, tracker.stable[side])
        pts = [(x + int(px * w), y + int(py * h)) for px, py in lm]
        for a, b in CONNECTIONS:
            pygame.draw.line(screen, WHITE, pts[a], pts[b], 2)
        for p in pts:
            pygame.draw.circle(screen, color, p, 4 if big else 3)
        draw_text(screen, SIDE_NAME[side], 26 if big else 20, color, (pts[0][0], pts[0][1] + (18 if big else 12)))
    pygame.draw.rect(screen, DIM, (x, y, w, h), 3)
    size, dy = (30, 22) if big else (22, 12)
    for side, cx in (("L", x + w // 4), ("R", x + 3 * w // 4)):
        color, label = describe(side, tracker.stable[side])
        draw_text(screen, f"{SIDE_NAME[side]}: {label}", size, color, (cx, y + h - dy))
