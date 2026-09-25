import math
import re
from dataclasses import dataclass

import pygame

TILE = 32
WIDTH, HEIGHT = 960, 544  # 30 x 17 tiles
SPEED = 300       # px/s
GRAVITY = 1800    # px/s²
JUMP_SPEED = 650  # px/s
MAX_FALL = 900    # px/s
SIZE = 32
BG = (30, 30, 40)
GREEN = (60, 170, 80)
BLUE = (60, 120, 230)

# '#' sólido, 'P' início do jogador, '.' vazio
LEVEL = [
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    ".......................................................................................................................#",
    "........................................#####..........................................................................#",
    ".................###.............####...........###.................##.................................................#",
    "...P...........#######..............................................##.................................................#",
    "############################..##########################....############################################################",
]


@dataclass
class Input:
    move: int   # -1 esquerda, 0 parado, +1 direita
    jump: bool  # True só no frame em que o pulo foi comandado (borda de subida)


def load_level(rows: list[str]) -> tuple[list[pygame.Rect], tuple[int, int]]:
    assert len(rows) * TILE == HEIGHT, f"mapa precisa de {HEIGHT // TILE} linhas, tem {len(rows)}"
    assert len({len(r) for r in rows}) == 1, "todas as linhas do mapa precisam ter o mesmo comprimento"
    assert len(rows[0]) * TILE >= WIDTH, "fase mais estreita que a janela"
    solids, spawns = [], []
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch not in "#P.":
                raise ValueError(f"caractere {ch!r} inválido no mapa: linha {r}, coluna {c}")
            if ch == "P":
                spawns.append((c * TILE, r * TILE))
        # funde '#' vizinhos numa linha: 1 Rect por sequência, não por tile
        for m in re.finditer("#+", line):
            solids.append(pygame.Rect(m.start() * TILE, r * TILE, len(m[0]) * TILE, TILE))
    if len(spawns) != 1:
        raise ValueError(f"mapa precisa de exatamente um 'P', tem {len(spawns)}")
    return solids, spawns[0]


class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.rect = pygame.Rect(x, y, SIZE, SIZE)
        self.vx = self.vy = 0.0
        self.on_ground = False

    def update(self, inp: Input, dt: float, solids: list[pygame.Rect]):
        self.vx = inp.move * SPEED
        if inp.jump and self.on_ground:
            self.vy = -JUMP_SPEED
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)

        self.x += self.vx * dt
        self.rect.x = round(self.x)
        for s in solids:
            if self.rect.colliderect(s):
                if self.vx > 0:
                    self.rect.right = s.left
                elif self.vx < 0:
                    self.rect.left = s.right
                self.x = self.rect.x

        self.y += self.vy * dt
        # ponytail: arredonda na direção do movimento; com round/int os 0,5 px/frame
        # de gravidade parado no chão não encostam e on_ground piscaria frame sim, frame não
        self.rect.y = math.ceil(self.y) if self.vy > 0 else math.floor(self.y)
        self.on_ground = False
        for s in solids:
            if self.rect.colliderect(s):
                if self.vy > 0:
                    self.rect.bottom = s.top
                    self.on_ground = True
                else:
                    self.rect.top = s.bottom
                self.vy = 0
                self.y = self.rect.y


class Game:
    def __init__(self):
        self.solids, self.spawn = load_level(LEVEL)
        self.level_w = len(LEVEL[0]) * TILE
        self.level_h = len(LEVEL) * TILE
        self.player = Player(*self.spawn)
        self.camera_x = 0

    def update(self, inp: Input, dt: float):
        p = self.player
        p.update(inp, dt, self.solids)
        p.x = pygame.math.clamp(p.x, 0, self.level_w - SIZE)
        p.rect.x = round(p.x)
        if p.rect.top > self.level_h:  # temporário: vira morte na etapa 5
            self.player = p = Player(*self.spawn)
        self.camera_x = pygame.math.clamp(p.rect.centerx - WIDTH // 2, 0, self.level_w - WIDTH)

    def draw(self, surface):
        surface.fill(BG)
        cx = self.camera_x
        for s in self.solids:
            if s.right >= cx and s.left <= cx + WIDTH:
                pygame.draw.rect(surface, GREEN, s.move(-cx, 0))
        pygame.draw.rect(surface, BLUE, self.player.rect.move(-cx, 0))
