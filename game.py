import math
import re
from dataclasses import dataclass, field

import pygame

TILE = 32
WIDTH, HEIGHT = 960, 544  # 30 x 17 tiles
SPEED = 300         # px/s
GRAVITY = 1800      # px/s²
JUMP_SPEED = 650    # px/s  -> altura ≈ 117 px ≈ 3,6 tiles; alcance ≈ 216 px ≈ 6,7 tiles
MAX_FALL = 900      # px/s
COYOTE_TIME = 0.10  # s: ainda pode pular depois de sair da beirada
JUMP_BUFFER = 0.12  # s: pulo comandado antes de tocar o chão executa ao tocar
ENEMY_SPEED = 80
HOP_INTERVAL = 1.4
HOP_SPEED = 450
STOMP_BOUNCE = 0.6
DEATH_TIME = 1.0
SIZE = 32
ENEMY_SIZE = 28

GREEN = (60, 170, 80)
GREEN_DARK = (40, 120, 60)
BLUE = (60, 120, 230)
RED = (220, 60, 60)
ORANGE = (240, 150, 40)
YELLOW = (250, 210, 60)
GRAY = (140, 140, 150)
SPIKE = (225, 225, 235)
POLE = (200, 200, 210)

VALID = "#P.EH^oG"


@dataclass
class Input:
    move: int   # -1 esquerda, 0 parado, +1 direita
    jump: bool  # True só no frame em que o pulo foi comandado (borda de subida)


@dataclass
class LevelData:
    solids: list = field(default_factory=list)
    enemies: list = field(default_factory=list)   # (x, y, kind)
    spikes: list = field(default_factory=list)
    coins: list = field(default_factory=list)
    spawn: tuple = (0, 0)
    goal: pygame.Rect = None
    w: int = 0
    h: int = 0


def load_level(rows: list[str]) -> LevelData:
    assert len(rows) * TILE == HEIGHT, f"mapa precisa de {HEIGHT // TILE} linhas, tem {len(rows)}"
    assert len({len(r) for r in rows}) == 1, "todas as linhas do mapa precisam ter o mesmo comprimento"
    assert len(rows[0]) * TILE >= WIDTH, "fase mais estreita que a janela"
    lv = LevelData(w=len(rows[0]) * TILE, h=len(rows) * TILE)
    spawns, goals = [], []
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch not in VALID:
                raise ValueError(f"caractere {ch!r} inválido no mapa: linha {r}, coluna {c}")
            x, y = c * TILE, r * TILE
            if ch == "P":
                spawns.append((x, y))
            elif ch in "EH":
                lv.enemies.append((x, y, "walker" if ch == "E" else "hopper"))
            elif ch == "^":
                lv.spikes.append(pygame.Rect(x, y + TILE - 12, TILE, 12))
            elif ch == "o":
                lv.coins.append(pygame.Rect(x + 8, y + 8, 16, 16))
            elif ch == "G":
                goals.append(pygame.Rect(x, y, TILE, TILE))
        # funde '#' vizinhos numa linha: 1 Rect por sequência, não por tile
        for m in re.finditer("#+", line):
            lv.solids.append(pygame.Rect(m.start() * TILE, r * TILE, len(m[0]) * TILE, TILE))
    if len(spawns) != 1:
        raise ValueError(f"mapa precisa de exatamente um 'P', tem {len(spawns)}")
    if not goals:
        raise ValueError("mapa precisa de pelo menos um 'G'")
    lv.spawn = spawns[0]
    lv.goal = goals[0].unionall(goals[1:])
    return lv


def move_body(body, dt: float, solids: list[pygame.Rect]):
    """Gravidade, move X e resolve, move Y e resolve. Seta on_ground e hit_wall."""
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


class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.rect = pygame.Rect(x, y, SIZE, SIZE)
        self.vx = self.vy = 0.0
        self.on_ground = self.hit_wall = False
        self.prev_bottom = self.rect.bottom
        self.coyote = self.jump_buf = 0.0

    def update(self, inp: Input, dt: float, solids: list[pygame.Rect]):
        self.prev_bottom = self.rect.bottom
        self.vx = inp.move * SPEED
        self.coyote = COYOTE_TIME if self.on_ground else self.coyote - dt
        self.jump_buf = JUMP_BUFFER if inp.jump else self.jump_buf - dt
        if self.jump_buf > 0 and self.coyote > 0:
            self.vy = -JUMP_SPEED
            self.coyote = self.jump_buf = 0.0
        move_body(self, dt, solids)


class Enemy:
    def __init__(self, x, y, kind):
        self.kind = kind
        self.x, self.y = float(x + (SIZE - ENEMY_SIZE) // 2), float(y + SIZE - ENEMY_SIZE)
        self.rect = pygame.Rect(self.x, self.y, ENEMY_SIZE, ENEMY_SIZE)
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
            if probe.collidelist(solids) == -1:
                self.vx = -self.vx
            if self.kind == "hopper":
                self.timer -= dt
                if self.timer <= 0:
                    self.vy = -HOP_SPEED
                    self.timer = HOP_INTERVAL


class Game:
    """Uma tentativa em uma fase. state: playing -> dead -> dead_done, ou playing -> won."""

    def __init__(self, rows: list[str], bg=(30, 30, 40)):
        self.level = load_level(rows)
        self.bg = bg
        self.player = Player(*self.level.spawn)
        self.enemies = [Enemy(*e) for e in self.level.enemies]
        self.coins = list(self.level.coins)
        self.coins_total = len(self.coins)
        self.collected = 0
        self.elapsed = 0.0
        self.state = "playing"
        self.timer = 0.0
        self.camera_x = 0

    def die(self):
        self.state = "dead"
        self.timer = DEATH_TIME
        self.player.vy = -400.0

    def update(self, inp: Input, dt: float):
        p, lv = self.player, self.level
        if self.state == "dead":
            p.vy += GRAVITY * dt
            p.y += p.vy * dt
            p.rect.y = round(p.y)
            self.timer -= dt
            if self.timer <= 0:
                self.state = "dead_done"
            return
        if self.state != "playing":
            return

        self.elapsed += dt
        p.update(inp, dt, lv.solids)
        p.x = pygame.math.clamp(p.x, 0, lv.w - SIZE)
        p.rect.x = round(p.x)
        for e in self.enemies:
            e.update(dt, lv.solids)
        self.enemies = [e for e in self.enemies if e.rect.top <= lv.h]

        for e in self.enemies:
            if p.rect.colliderect(e.rect):
                if p.vy > 0 and p.prev_bottom <= e.rect.top:
                    self.enemies.remove(e)
                    p.rect.bottom = e.rect.top
                    p.y = p.rect.y
                    p.vy = -JUMP_SPEED * STOMP_BOUNCE
                    break
                self.die()
                return
        if p.rect.collidelist(lv.spikes) != -1 or p.rect.top > lv.h:
            self.die()
            return
        for c in p.rect.collidelistall(self.coins)[::-1]:
            del self.coins[c]
            self.collected += 1
        if p.rect.colliderect(lv.goal):
            self.state = "won"
        self.camera_x = pygame.math.clamp(p.rect.centerx - WIDTH // 2, 0, lv.w - WIDTH)

    def draw(self, surface):
        surface.fill(self.bg)
        cx, lv = self.camera_x, self.level
        visible = pygame.Rect(cx, 0, WIDTH, HEIGHT)
        for s in lv.solids:
            if s.colliderect(visible):
                r = s.move(-cx, 0)
                pygame.draw.rect(surface, GREEN, r)
                pygame.draw.rect(surface, GREEN_DARK, r, 2)
        for s in lv.spikes:
            if s.colliderect(visible):
                x, base = s.x - cx, s.bottom
                for i in range(3):
                    x0 = x + i * 11
                    pygame.draw.polygon(surface, SPIKE, [(x0, base), (x0 + 5, base - 12), (x0 + 10, base)])
        for c in self.coins:
            if c.colliderect(visible):
                pygame.draw.circle(surface, YELLOW, c.move(-cx, 0).center, 8)
        g = lv.goal.move(-cx, 0)
        pygame.draw.rect(surface, POLE, (g.x + 4, g.y, 4, g.h))
        pygame.draw.polygon(surface, YELLOW, [(g.x + 8, g.y), (g.x + 30, g.y + 10), (g.x + 8, g.y + 20)])
        for e in self.enemies:
            if e.rect.colliderect(visible):
                pygame.draw.rect(surface, RED if e.kind == "walker" else ORANGE, e.rect.move(-cx, 0))
        pygame.draw.rect(surface, GRAY if self.state != "playing" else BLUE, self.player.rect.move(-cx, 0))
