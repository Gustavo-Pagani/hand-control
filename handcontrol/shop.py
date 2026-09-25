"""Loja entre fases: gasta as moedas da campanha em coração, escudo ou pulo alto."""
import pygame

from . import assets, sound
from .config import HEIGHT, MAX_LIVES, SHOP, WIDTH
from .run import Run
from .ui import BLUE, DIM, GREEN, RED, WHITE, YELLOW, dim, draw_panel, draw_text

ITEMS = SHOP + [("go", "Continuar", 0, "proxima fase")]


class Cursor:
    """Cursor de menu: indicador esquerdo = próximo, polegar esquerdo = anterior (um passo por gesto)."""

    def __init__(self, n):
        self.n, self.idx, self.prev_move = n, 0, 0

    def update(self, inp):
        step = inp.move if inp.move and inp.move != self.prev_move else 0
        self.prev_move = inp.move
        if step:
            self.idx = (self.idx + step) % self.n
        return step


class Shop:
    def __init__(self, run: Run, background_game):
        self.run = run
        self.bg_game = background_game
        self.cursor = Cursor(len(ITEMS))
        self.msg = ""
        self.t = 0.0

    def update(self, inp):
        """-> 'next' quando o jogador escolhe continuar (item Continuar ou tres dedos na direita)."""
        self.t += 1 / 60
        self.cursor.update(inp)
        if inp.back:
            return "next"
        if inp.confirm:
            key = ITEMS[self.cursor.idx][0]
            if key == "go":
                return "next"
            if self.run.buy(key):
                self.msg = "comprado!"
                sound.play("buy")
            else:
                self.msg = "moedas insuficientes" if self.run.coins < ITEMS[self.cursor.idx][2] else "ja tem"
                sound.play("hurt")
        return None

    def draw(self, screen):
        cx = WIDTH // 2
        self.bg_game.draw(screen)
        dim(screen, 170)
        panel = pygame.Rect(0, 0, 720, 460)
        panel.center = (cx, HEIGHT // 2 + 10)
        draw_panel(screen, panel)
        draw_text(screen, "LOJA", 64, YELLOW, (cx, panel.y + 40))
        screen.blit(assets.COIN[0], (cx - 70, panel.y + 66))
        draw_text(screen, f"{self.run.coins} moedas", 32, YELLOW, (cx + 20, panel.y + 84))
        for i in range(MAX_LIVES):
            screen.blit(assets.HEART["full" if i < self.run.lives else "empty"],
                        (panel.right - 60 - (MAX_LIVES - 1 - i) * 38, panel.y + 24))
        icons = {"heart": assets.HEART["full"], "shield": assets.GEM, "highjump": assets.PLAYER["jump"][0], "go": None}
        for i, (key, name, price, desc) in enumerate(ITEMS):
            y = panel.y + 130 + i * 72
            selected = i == self.cursor.idx
            row = pygame.Rect(panel.x + 30, y - 8, panel.w - 60, 62)
            if selected:
                pygame.draw.rect(screen, (50, 48, 70), row, border_radius=6)
                pygame.draw.rect(screen, YELLOW, row, 2, border_radius=6)
            icon = icons[key]
            if icon:
                screen.blit(icon, icon.get_rect(center=(row.x + 40, y + 22)))
            affordable = key == "go" or self.run.can_buy(key)
            color = WHITE if affordable else DIM
            draw_text(screen, name, 34, GREEN if key == "go" else color, (row.x + 80, y + 4), align="topleft")
            draw_text(screen, desc, 22, DIM, (row.x + 80, y + 34), align="topleft")
            if key != "go":
                have = (key == "shield" and self.run.shield_next) or (key == "highjump" and self.run.highjump_next)
                label = "ja tem" if have else f"{price}"
                draw_text(screen, label, 30, BLUE if have else (YELLOW if affordable else RED), (row.right - 30, y + 20),
                          align="midright")
        if self.msg:
            draw_text(screen, self.msg, 24, YELLOW, (cx, panel.bottom - 58))
        draw_text(screen, "esquerda escolhe   duas maos abertas: comprar   tres dedos direita: sair da loja", 20, DIM,
                  (cx, panel.bottom - 28))
