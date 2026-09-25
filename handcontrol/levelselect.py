"""Tela de seleção de fases com as estrelas ganhas e cadeado nas fases não liberadas."""
import pygame

from . import assets, sound
from .config import HEIGHT, STARS, WIDTH
from .levels import LEVELS
from .shop import Cursor
from .ui import DIM, GREEN, WHITE, YELLOW, dim, draw_panel, draw_star, draw_text


class LevelSelect:
    def __init__(self, progress, background_game):
        self.progress = progress
        self.bg_game = background_game
        self.cursor = Cursor(len(LEVELS))

    def update(self, inp):
        """-> índice da fase escolhida, 'menu' para voltar, ou None."""
        self.cursor.update(inp)
        if inp.back:
            return "menu"
        if inp.confirm:
            if self.cursor.idx < self.progress["unlocked"]:
                return self.cursor.idx
            sound.play("hurt")
        return None

    def draw(self, screen):
        cx = WIDTH // 2
        self.bg_game.draw_background(screen, 0)
        dim(screen, 150)
        panel = pygame.Rect(0, 0, 760, 500)
        panel.center = (cx, HEIGHT // 2)
        draw_panel(screen, panel)
        draw_text(screen, "FASES", 60, YELLOW, (cx, panel.y + 40))
        total = sum(len(s) for s in self.progress["stars"].values())
        draw_text(screen, f"estrelas: {total}/{3 * len(LEVELS)}", 26, DIM, (cx, panel.y + 78))
        for i, (name, theme, _) in enumerate(LEVELS):
            y = panel.y + 110 + i * 66
            row = pygame.Rect(panel.x + 30, y - 6, panel.w - 60, 58)
            unlocked = i < self.progress["unlocked"]
            if i == self.cursor.idx:
                pygame.draw.rect(screen, (50, 48, 70), row, border_radius=6)
                pygame.draw.rect(screen, YELLOW, row, 2, border_radius=6)
            pygame.draw.rect(screen, assets.BG[theme]["sky"], (row.x + 12, y + 6, 34, 34), border_radius=4)
            draw_text(screen, f"{i + 1}. {name}", 34, WHITE if unlocked else DIM, (row.x + 62, y + 22), align="midleft")
            got = self.progress["stars"].get(i, set())
            for j, (key, label) in enumerate(STARS):
                draw_star(screen, (row.right - 150 + j * 44, y + 23), 15, key in got)
            if not unlocked:
                draw_text(screen, "bloqueada", 22, DIM, (row.right - 240, y + 22), align="midright")
        draw_text(screen, "esquerda escolhe   duas maos abertas: jogar   tres dedos direita: voltar",
                  20, DIM, (cx, panel.bottom - 24))
        draw_text(screen, "estrelas: completa · todas as moedas · sem morrer", 20, GREEN, (cx, panel.bottom - 48))
