"""O contrato entre quem controla (teclado, gestos) e o jogo: Input."""
from dataclasses import dataclass

import pygame


@dataclass
class Input:
    move: int   # -1 esquerda, 0 parado, +1 direita
    jump: bool  # True só no frame em que o pulo foi comandado (borda de subida)


def read_keyboard(events) -> Input:
    keys = pygame.key.get_pressed()
    move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
    jump = any(e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_w) for e in events)
    return Input(move, jump)


class GestureInput:
    """Gesto estável -> Input. Pulo só na borda de subida da mão aberta: um pulo por abertura."""

    MOVE = {"INDEX": 1, "THUMB": -1}

    def __init__(self):
        self.prev = "NONE"

    def read(self, stable: str) -> Input:
        jump = stable == "OPEN" and self.prev != "OPEN"
        self.prev = stable
        return Input(self.MOVE.get(stable, 0), jump)


def merge(a: Input, b: Input) -> Input:
    return Input(a.move or b.move, a.jump or b.jump)
