"""Cores, texto e painel: o kit de desenho que todas as cenas usam."""
import pygame

from . import assets

WHITE = (250, 250, 250)
DIM = (200, 200, 210)
YELLOW = (255, 215, 80)
RED = (235, 80, 80)
GREEN = (110, 220, 120)
BLUE = (110, 170, 255)
PANEL = (28, 26, 40)
SHADOW = (30, 30, 45)


def draw_text(surface, txt, size, color, pos, shadow=True, align="center"):
    f = assets.font(size)
    img = f.render(txt, False, color)
    rect = img.get_rect(**{align: pos})
    if shadow:
        surface.blit(f.render(txt, False, SHADOW), rect.move(3, 3))
    surface.blit(img, rect)


def draw_panel(surface, rect, border=YELLOW):
    pygame.draw.rect(surface, PANEL, rect, border_radius=8)
    pygame.draw.rect(surface, border, rect, 3, border_radius=8)


def dim(surface, alpha=160):
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    layer.fill((0, 0, 0, alpha))
    surface.blit(layer, (0, 0))


def draw_star(surface, center, r, filled):
    import math
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((center[0] + math.cos(a) * rr, center[1] + math.sin(a) * rr))
    if filled:
        pygame.draw.polygon(surface, YELLOW, pts)
    pygame.draw.polygon(surface, YELLOW if filled else DIM, pts, 2)


def fmt_time(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"
