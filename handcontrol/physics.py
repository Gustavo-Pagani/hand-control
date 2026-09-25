"""Gravidade e colisão por eixo, compartilhadas por player, inimigos e decoração do menu."""
import math

import pygame

from .config import GRAVITY, MAX_FALL


def move_body(body, dt: float, solids: list[pygame.Rect]):
    """body tem x, y (float), vx, vy, rect, on_ground, hit_wall. Move X e resolve, move Y e resolve."""
    body.vy = min(body.vy + GRAVITY * dt, MAX_FALL)

    body.x += body.vx * dt
    body.rect.x = round(body.x)
    body.hit_wall = False
    for s in solids:
        if body.rect.colliderect(s):
            if body.vx > 0:
                body.rect.right = s.left
            elif body.vx < 0:
                body.rect.left = s.right
            body.x = body.rect.x
            body.hit_wall = True

    body.y += body.vy * dt
    # ponytail: arredonda na direção do movimento; com round/int os 0,5 px/frame
    # de gravidade parado no chão não encostam e on_ground piscaria frame sim, frame não
    body.rect.y = math.ceil(body.y) if body.vy > 0 else math.floor(body.y)
    body.on_ground = False
    for s in solids:
        if body.rect.colliderect(s):
            if body.vy > 0:
                body.rect.bottom = s.top
                body.on_ground = True
            else:
                body.rect.top = s.bottom
            body.vy = 0
            body.y = body.rect.y
