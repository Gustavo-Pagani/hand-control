"""Cenas (menu, calibrar, jogar, fim de fase, game over, vitória), vidas, HUD e o loop principal."""
import sys

import pygame

from . import assets
from .calibration import Calibration
from .camview import draw_camera
from .config import DT, FPS, HEIGHT, LIVES, WIDTH
from .game import Game
from .inputs import GestureInput, Input, merge, read_keyboard
from .levels import LEVELS
from .menu import Menu
from .ui import DIM, RED, WHITE, YELLOW, dim, draw_panel, draw_text, fmt_time
from .vision import HandTracker


class App:
    def __init__(self, start_level=None, tracker=None):
        self.scene = "menu"
        self.level_idx = 0
        self.lives = LIVES
        self.game = None
        self.total_time = self.total_coins = self.total_coins_max = 0
        self.t = 0.0
        self.show_cam = True
        self.tracker = tracker or HandTracker()
        if not self.tracker.is_alive() and not self.tracker.error:
            self.tracker.start()
        self.gestures = GestureInput()
        bg_game = Game(LEVELS[0][2], LEVELS[0][1])   # só para o fundo em parallax do menu e da calibração
        self.menu = Menu(bg_game)
        self.calibration = Calibration(self.tracker, bg_game)
        if start_level is not None:
            self.start(start_level)

    # ---------------- fluxo ----------------
    def start(self, idx):
        self.level_idx, self.lives = idx, LIVES
        self.total_time = self.total_coins = self.total_coins_max = 0
        self.new_attempt()

    def new_attempt(self):
        name, theme, rows = LEVELS[self.level_idx]
        self.game = Game(rows, theme)
        self.scene = "play"

    def read_input(self, events) -> Input:
        tr = self.tracker
        stable = tr.stable if tr.ready and not tr.error else {}
        return merge(read_keyboard(events), self.gestures.read(stable))

    def update(self, inp, events):
        self.t += DT
        keys = [e.key for e in events if e.type == pygame.KEYDOWN]
        self.tracker.want_big = self.scene == "calibrate"
        if pygame.K_v in keys:
            self.show_cam = not self.show_cam
        if self.scene == "menu":
            self.menu.update()
            if pygame.K_c in keys:
                self.calibration.reset()
                self.scene = "calibrate"
            elif inp.jump:
                self.start(0)
            for k in keys:
                if pygame.K_1 <= k <= pygame.K_5:
                    self.start(k - pygame.K_1)
        elif self.scene == "calibrate":
            if self.calibration.update(keys) == "menu":
                self.scene = "menu"
        elif self.scene == "play":
            g = self.game
            if pygame.K_r in keys:
                self.new_attempt()
                return
            g.update(inp, DT)
            if g.state == "dead_done":
                self.lives -= 1
                if self.lives > 0:
                    self.new_attempt()
                else:
                    self.scene = "game_over"
            elif g.state == "won":
                self.total_time += g.elapsed
                self.total_coins += g.collected
                self.total_coins_max += g.coins_total
                self.scene = "level_done"
        elif self.scene == "level_done":
            if inp.jump:
                if self.level_idx + 1 < len(LEVELS):
                    self.level_idx += 1
                    self.lives = LIVES
                    self.new_attempt()
                else:
                    self.scene = "victory"
        elif inp.jump:  # game_over / victory
            self.scene = "menu"

    # ---------------- desenho ----------------
    def draw(self, screen):
        if self.scene == "menu":
            self.menu.draw(screen, self.tracker, self.show_cam)
        elif self.scene == "calibrate":
            self.calibration.draw(screen)
        else:
            self.game.draw(screen)
            if self.scene == "play":
                self.draw_hud(screen)
            else:
                self.draw_end_panel(screen)

    def draw_hud(self, screen):
        g, cx = self.game, WIDTH // 2
        draw_text(screen, f"Fase {self.level_idx + 1}  {LEVELS[self.level_idx][0]}", 34, WHITE, (170, 24))
        for i in range(LIVES):
            screen.blit(assets.HEART["full" if i < self.lives else "empty"], (WIDTH - 50 - i * 40, 8))
        screen.blit(assets.COIN[0], (cx - 70, 6))
        draw_text(screen, f"{g.collected}/{g.coins_total}", 34, YELLOW, (cx + 10, 24))
        draw_text(screen, fmt_time(g.elapsed), 34, WHITE, (WIDTH - 260, 24))
        if self.show_cam and not self.tracker.error:
            draw_camera(screen, self.tracker, WIDTH - 210, 48)

    def draw_end_panel(self, screen):
        g, cx, cy = self.game, WIDTH // 2, HEIGHT // 2
        name = LEVELS[self.level_idx][0]
        dim(screen)
        panel = pygame.Rect(0, 0, 600, 320)
        panel.center = (cx, cy)
        draw_panel(screen, panel)
        if self.scene == "level_done":
            draw_text(screen, f"Fase {self.level_idx + 1} completa!", 64, YELLOW, (cx, cy - 100))
            draw_text(screen, name, 40, WHITE, (cx, cy - 50))
            draw_text(screen, f"tempo  {fmt_time(g.elapsed)}", 38, WHITE, (cx, cy + 5))
            screen.blit(assets.COIN[0], (cx - 80, cy + 27))
            draw_text(screen, f"{g.collected}/{g.coins_total}", 38, YELLOW, (cx + 10, cy + 45))
            hint = "ESPACO ou INDICADOR DIREITO para continuar"
        elif self.scene == "game_over":
            draw_text(screen, "GAME OVER", 80, RED, (cx, cy - 80))
            draw_text(screen, f"Voce chegou ate a fase {self.level_idx + 1}", 38, WHITE, (cx, cy))
            hint = "ESPACO ou INDICADOR DIREITO para o menu"
        else:
            draw_text(screen, "VOCE ZEROU!", 80, YELLOW, (cx, cy - 90))
            draw_text(screen, f"tempo total  {fmt_time(self.total_time)}", 38, WHITE, (cx, cy - 15))
            screen.blit(assets.COIN[0], (cx - 80, cy + 7))
            draw_text(screen, f"{self.total_coins}/{self.total_coins_max}", 38, YELLOW, (cx + 10, cy + 25))
            hint = "ESPACO ou INDICADOR DIREITO para o menu"
        if int(self.t * 2) % 2 == 0:
            draw_text(screen, hint, 32, DIM, (cx, cy + 120))


def run():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hand Control")
    assets.load()
    clock = pygame.time.Clock()
    start = int(sys.argv[1]) - 1 if len(sys.argv) > 1 else None
    app = App(start)
    while True:
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE
                                          and app.scene == "menu"):
                app.tracker.stop()
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                app.scene = "menu"
        app.update(app.read_input(events), events)
        app.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
