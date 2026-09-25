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
    """Gesto estável -> Input.

    INDEX anda para frente, THUMB para trás, L (polegar+indicador) pula uma vez na borda de subida.
    Durante o L a direção anterior é mantida, senão não dá para pular buracos; do punho direto
    para o L o pulo é parado. FIST, OPEN e NONE param.
    """

    MOVE = {"INDEX": 1, "THUMB": -1}

    def __init__(self):
        self.prev = "NONE"
        self.hold_dir = 0

    def read(self, stable: str) -> Input:
        jump = stable == "L" and self.prev != "L"
        self.prev = stable
        if stable == "L":
            move = self.hold_dir
        else:
            move = self.hold_dir = self.MOVE.get(stable, 0)
        return Input(move, jump)


def merge(a: Input, b: Input) -> Input:
    return Input(a.move or b.move, a.jump or b.jump)
