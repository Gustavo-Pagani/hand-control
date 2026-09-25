import math
from dataclasses import dataclass

import pygame

WIDTH, HEIGHT = 960, 540
SPEED = 300       # px/s
GRAVITY = 1800    # px/s²
JUMP_SPEED = 650  # px/s
MAX_FALL = 900    # px/s
SIZE = 32
GROUND_H = 64
BG = (30, 30, 40)
GREEN = (60, 170, 80)
BLUE = (60, 120, 230)


@dataclass
class Input:
    move: int   # -1 esquerda, 0 parado, +1 direita
    jump: bool  # True só no frame em que o pulo foi comandado (borda de subida)


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
        self.player = Player(WIDTH // 2 - SIZE // 2, HEIGHT // 2)
        self.solids = [pygame.Rect(0, HEIGHT - GROUND_H, WIDTH, GROUND_H)]

    def update(self, inp: Input, dt: float):
        p = self.player
        p.update(inp, dt, self.solids)
        # ponytail: clamp lateral temporário, a câmera da Etapa 2 substitui
        p.x = max(0, min(p.x, WIDTH - SIZE))
        p.rect.x = round(p.x)

    def draw(self, surface):
        surface.fill(BG)
        for s in self.solids:
            pygame.draw.rect(surface, GREEN, s)
        pygame.draw.rect(surface, BLUE, self.player.rect)
