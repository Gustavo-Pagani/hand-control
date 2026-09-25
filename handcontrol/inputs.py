"""O contrato entre quem controla (gestos; teclado só como reserva silenciosa) e o jogo: Input."""
from dataclasses import dataclass

import pygame


@dataclass
class Input:
    move: int = 0          # -1 esquerda, 0 parado, +1 direita (menus: -1 anterior, +1 próximo)
    jump: bool = False     # True só no frame em que o pulo foi comandado (borda de subida)
    confirm: bool = False  # menus: confirmar / comprar / continuar (borda)
    back: bool = False     # menus: voltar / sair (borda)
    select: int = 0        # menus: item escolhido pelo número de dedos da mão direita (1-5), 0 = nenhum


def read_keyboard(events) -> Input:
    """Reserva para testes: A/D, espaço, ENTER e BACKSPACE. Nenhuma tela anuncia teclas."""
    keys = pygame.key.get_pressed()
    down = [e.key for e in events if e.type == pygame.KEYDOWN]
    move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
    select = next((k - pygame.K_0 for k in down if pygame.K_1 <= k <= pygame.K_5), 0)
    return Input(move, pygame.K_SPACE in down or pygame.K_w in down,
                 pygame.K_RETURN in down, pygame.K_BACKSPACE in down, select)


class Hold:
    """Gesto que precisa ser segurado por `seconds` para valer (evita confirmar sem querer).
    update(active, dt) -> True uma vez, no frame em que completa. progress em [0, 1]."""

    def __init__(self, seconds):
        self.seconds = seconds
        self.t = 0.0
        self.fired = False

    def update(self, active, dt) -> bool:
        if not active:
            self.t, self.fired = 0.0, False
            return False
        self.t += dt
        if self.t >= self.seconds and not self.fired:
            self.fired = True
            return True
        return False

    def reset(self):
        self.t, self.fired = 0.0, False

    @property
    def progress(self):
        return min(1.0, self.t / self.seconds) if not self.fired else 0.0


class GestureInput:
    """Gestos estáveis das duas mãos -> Input.

    Jogo: esquerda INDEX anda para frente, THUMB para trás, resto para; direita com um dedo só levantado
    (qualquer dedo) pula uma vez (borda).
    Menus: número de dedos da direita escolhe o item (select); sinal de OK em qualquer mão, segurado, confirma;
    THREE na esquerda segurado volta.
    """

    MOVE = {"INDEX": 1, "THUMB": -1}
    COUNT = {"INDEX": 1, "ONE": 1, "TWO": 2, "THREE": 3, "OPEN": 4, "FIVE": 5}
    ONE_FINGER = ("INDEX", "ONE")

    def __init__(self, confirm_seconds=0.6, back_seconds=0.8):
        self.prev_right = "NONE"
        self.confirm = Hold(confirm_seconds)
        self.back = Hold(back_seconds)

    def read(self, stable: dict, dt: float = 1 / 60) -> Input:
        left, right = stable.get("L", "NONE"), stable.get("R", "NONE")
        jump = right in self.ONE_FINGER and self.prev_right not in self.ONE_FINGER
        self.prev_right = right
        confirm = self.confirm.update(left == "OK" or right == "OK", dt)
        back = self.back.update(left == "THREE", dt)
        return Input(self.MOVE.get(left, 0), jump, confirm, back, self.COUNT.get(right, 0))


def merge(a: Input, b: Input) -> Input:
    return Input(a.move or b.move, a.jump or b.jump, a.confirm or b.confirm, a.back or b.back, a.select or b.select)
