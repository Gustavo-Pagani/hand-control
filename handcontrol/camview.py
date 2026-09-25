"""Desenha o preview da webcam com os landmarks e o gesto atual (HUD do jogo e tela de calibração)."""
import pygame

from .ui import BLUE, DIM, GREEN, PANEL, RED, WHITE, YELLOW, draw_text
from .vision import CONNECTIONS

GESTURE_COLOR = {"L": YELLOW, "INDEX": GREEN, "THUMB": BLUE, "OPEN": DIM, "FIST": DIM, "NONE": RED}
GESTURE_LABEL = {"L": "POLEGAR + INDICADOR = pulo", "INDEX": "INDICADOR = frente", "THUMB": "POLEGAR = tras",
                 "OPEN": "MAO ABERTA = parado", "FIST": "PUNHO = parado", "NONE": "sem mao"}


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
    if tracker.landmarks:
        pts = [(x + int(px * w), y + int(py * h)) for px, py in tracker.landmarks]
        for a, b in CONNECTIONS:
            pygame.draw.line(screen, WHITE, pts[a], pts[b], 2)
        for p in pts:
            pygame.draw.circle(screen, GREEN, p, 4 if big else 3)
    color = GESTURE_COLOR[tracker.stable]
    pygame.draw.rect(screen, color, (x, y, w, h), 3)
    label = GESTURE_LABEL[tracker.stable] if big else tracker.stable
    draw_text(screen, label, 30 if big else 24, color, (x + w // 2, y + h - (22 if big else 14)))
