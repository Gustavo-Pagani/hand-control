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
    """Gestos estáveis das duas mãos -> Input.

    Mão esquerda: INDEX anda para frente, THUMB para trás, resto para.
    Mão direita: INDEX pula uma vez na borda de subida (segurar não repete).
    """

    MOVE = {"INDEX": 1, "THUMB": -1}

    def __init__(self):
        self.prev_right = "NONE"

    def read(self, stable: dict) -> Input:
        right = stable.get("R", "NONE")
        jump = right == "INDEX" and self.prev_right != "INDEX"
        self.prev_right = right
        return Input(self.MOVE.get(stable.get("L", "NONE"), 0), jump)


def merge(a: Input, b: Input) -> Input:
    return Input(a.move or b.move, a.jump or b.jump)
