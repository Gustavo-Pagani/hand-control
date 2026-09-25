"""Player, inimigos e projéteis: só estado e movimento. Desenho fica em game.py."""
import math

import pygame

from .config import (BEE_AMPL, BEE_RANGE, BEE_SPEED, CANNON_INTERVAL, CANNON_RANGE, COYOTE_TIME, ENEMY_SIZE,
                     ENEMY_SPEED, HOP_INTERVAL, HOP_SPEED, JUMP_BUFFER, JUMP_SPEED, PLAYER_H, PLAYER_W,
                     ROCK_SPEED, SHIELD_INVULN, SPEED, TILE)
from .inputs import Input
from .physics import move_body


class Player:
    def __init__(self, x, y, shield=False, jump_mult=1.0):
        self.rect = pygame.Rect(x, y + TILE - PLAYER_H, PLAYER_W, PLAYER_H)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.vx = self.vy = 0.0
        self.on_ground = self.hit_wall = False
        self.hit_ceiling = None
        self.prev_bottom = self.rect.bottom
        self.coyote = self.jump_buf = 0.0
        self.facing = 1
        self.shield = shield
        self.jump_mult = jump_mult
        self.invuln = 0.0

    def update(self, inp: Input, dt: float, solids: list[pygame.Rect]):
        self.prev_bottom = self.rect.bottom
        self.invuln = max(0.0, self.invuln - dt)
        self.vx = inp.move * SPEED
        if inp.move:
            self.facing = inp.move
        self.coyote = COYOTE_TIME if self.on_ground else self.coyote - dt
        self.jump_buf = JUMP_BUFFER if inp.jump else self.jump_buf - dt
        if self.jump_buf > 0 and self.coyote > 0:
            self.vy = -JUMP_SPEED * self.jump_mult
            self.coyote = self.jump_buf = 0.0
        move_body(self, dt, solids)

    def hit(self) -> str:
        """Toque letal. -> 'ignored' (invencível), 'shield' (escudo absorveu) ou 'dead'."""
        if self.invuln > 0:
            return "ignored"
        if self.shield:
            self.shield = False
            self.invuln = SHIELD_INVULN
            return "shield"
        return "dead"


class Rock:
    """Pedra do canhão: reta, sem gravidade, some na parede."""

    def __init__(self, x, y, direction):
        self.rect = pygame.Rect(0, 0, 16, 16)
        self.rect.center = (x, y)
        self.x = float(self.rect.x)
        self.vx = ROCK_SPEED * direction
        self.alive = True

    def update(self, dt, solids):
        self.x += self.vx * dt
        self.rect.x = round(self.x)
        if self.rect.collidelist(solids) != -1:
            self.alive = False


class Enemy:
    def __init__(self, x, y, kind):
        self.kind = kind
        w, h = ENEMY_SIZE[kind]
        self.rect = pygame.Rect(x + (TILE - w) // 2, y + TILE - h, w, h)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.x0, self.y0 = self.x, self.y
        self.vx, self.vy = (0.0 if kind == "cannon" else -ENEMY_SPEED if kind != "bee" else -BEE_SPEED), 0.0
        self.on_ground = self.hit_wall = False
        self.hit_ceiling = None
        self.timer = HOP_INTERVAL if kind == "hopper" else CANNON_INTERVAL
        self.recoil = 0.0
        self.t = 0.0
        self.facing = -1

    def update(self, dt: float, solids: list[pygame.Rect], player_rect=None):
        """Retorna uma Rock nova quando o canhão atira, senão None."""
        self.t += dt
        if self.kind == "bee":
            self.x += self.vx * dt
            if abs(self.x - self.x0) > BEE_RANGE:
                self.vx = -self.vx
                self.x = self.x0 + math.copysign(BEE_RANGE, self.x - self.x0)
            self.y = self.y0 + math.sin(self.t * 3) * BEE_AMPL
            self.rect.topleft = (round(self.x), round(self.y))
            self.facing = 1 if self.vx > 0 else -1
            return None
        move_body(self, dt, solids)
        if self.kind == "cannon":
            self.recoil = max(0.0, self.recoil - dt)
            self.timer -= dt
            if player_rect is not None:
                self.facing = 1 if player_rect.centerx > self.rect.centerx else -1
                if self.timer <= 0 and abs(player_rect.centerx - self.rect.centerx) < CANNON_RANGE:
                    self.timer, self.recoil = CANNON_INTERVAL, 0.2
                    return Rock(self.rect.centerx + self.facing * 20, self.rect.centery, self.facing)
            return None
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
        self.facing = 1 if self.vx > 0 else -1
        return None
