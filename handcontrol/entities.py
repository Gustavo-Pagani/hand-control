"""Player e inimigos: só estado e movimento. Desenho fica em game.py."""
import pygame

from .config import (COYOTE_TIME, ENEMY_SIZE, ENEMY_SPEED, HOP_INTERVAL, HOP_SPEED, JUMP_BUFFER, JUMP_SPEED,
                     PLAYER_H, PLAYER_W, SPEED, TILE)
from .inputs import Input
from .physics import move_body


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y + TILE - PLAYER_H, PLAYER_W, PLAYER_H)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.vx = self.vy = 0.0
        self.on_ground = self.hit_wall = False
        self.prev_bottom = self.rect.bottom
        self.coyote = self.jump_buf = 0.0
        self.facing = 1

    def update(self, inp: Input, dt: float, solids: list[pygame.Rect]):
        self.prev_bottom = self.rect.bottom
        self.vx = inp.move * SPEED
        if inp.move:
            self.facing = inp.move
        self.coyote = COYOTE_TIME if self.on_ground else self.coyote - dt
        self.jump_buf = JUMP_BUFFER if inp.jump else self.jump_buf - dt
        if self.jump_buf > 0 and self.coyote > 0:
            self.vy = -JUMP_SPEED
            self.coyote = self.jump_buf = 0.0
        move_body(self, dt, solids)


class Enemy:
    def __init__(self, x, y, kind):
        self.kind = kind
        w, h = ENEMY_SIZE[kind]
        self.rect = pygame.Rect(x + (TILE - w) // 2, y + TILE - h, w, h)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.vx, self.vy = -ENEMY_SPEED, 0.0
        self.on_ground = self.hit_wall = False
        self.timer = HOP_INTERVAL

    def update(self, dt: float, solids: list[pygame.Rect]):
        move_body(self, dt, solids)
        if self.hit_wall:
            self.vx = -self.vx
        if self.on_ground:
            foot_x = self.rect.left if self.vx < 0 else self.rect.right - 2
            probe = pygame.Rect(foot_x, self.rect.bottom + 1, 2, 2)
            if probe.collidelist(solids) == -1:   # beirada: vira antes de cair
                self.vx = -self.vx
            if self.kind == "hopper":
                self.timer -= dt
                if self.timer <= 0:
                    self.vy = -HOP_SPEED
                    self.timer = HOP_INTERVAL
