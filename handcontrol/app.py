"""Cenas (menu, fases, calibrar, jogar, fim de fase, loja, game over, vitória), HUD e o loop principal.

Tudo é controlado por gesto. O teclado continua funcionando em silêncio (A/D, espaço, ENTER, BACKSPACE, ESC)
só para testes; nenhuma tela anuncia teclas.
"""
import sys

import pygame

from . import assets, sound
from .calibration import Calibration
from .camview import draw_camera
from .config import COINS_PER_LIFE, DT, FPS, HEIGHT, MAX_LIVES, STARS, WIDTH
from .game import Game
from .inputs import GestureInput, Input, merge, read_keyboard
from .levels import LEVELS
from .levelselect import LevelSelect
from .menu import Menu
from .run import Run, load_progress, record_level, stars_for
from .shop import Shop
from .ui import BLUE, DIM, GREEN, RED, WHITE, YELLOW, dim, draw_panel, draw_star, draw_text, fmt_time
from .vision import HandTracker


class App:
    def __init__(self, start_level=None, tracker=None):
        self.scene = "menu"
        self.run = Run()
        self.game = None
        self.stars = set()
        self.t = 0.0
        self.show_cam = True
        self.quit = False
        self.progress = load_progress()
        self.tracker = tracker or HandTracker()
        if not self.tracker.is_alive() and not self.tracker.error:
            self.tracker.start()
        self.gestures = GestureInput()
        self.bg_game = Game(LEVELS[0][2], LEVELS[0][1])   # só para o fundo em parallax do menu e das telas
        self.menu = Menu(self.bg_game)
        self.calibration = Calibration(self.tracker, self.bg_game)
        self.levelselect = LevelSelect(self.progress, self.bg_game)
        self.shop = None
        if start_level is not None:
            self.start(start_level)

    # ---------------- fluxo ----------------
    def start(self, idx):
        self.run = Run()
        self.begin_level(idx)

    def begin_level(self, idx):
        self.run.start_level(idx)
        self.new_attempt()

    def new_attempt(self):
        name, theme, rows = LEVELS[self.run.level_idx]
        self.game = Game(rows, theme, self.run)
        self.scene = "play"

    def read_input(self, events) -> Input:
        tr = self.tracker
        stable = tr.stable if tr.ready and not tr.error else {}
        return merge(read_keyboard(events), self.gestures.read(stable, DT))

    def update(self, inp, events):
        self.t += DT
        keys = [e.key for e in events if e.type == pygame.KEYDOWN]
        self.tracker.want_big = self.scene == "calibrate"
        if pygame.K_v in keys:
            self.show_cam = not self.show_cam
        if pygame.K_m in keys:
            sound.toggle_mute()
        if self.scene == "menu":
            action = self.menu.update(inp)
            if action == "play":
                self.start(0)
            elif action == "levels":
                self.scene = "levels"
            elif action == "calibrate":
                self.calibration.reset()
                self.scene = "calibrate"
            elif action == "quit":
                self.quit = True
        elif self.scene == "levels":
            r = self.levelselect.update(inp)
            if r == "menu":
                self.scene = "menu"
            elif r is not None:
                self.start(r)
        elif self.scene == "calibrate":
            if self.calibration.update(inp) == "menu":
                self.scene = "menu"
        elif self.scene == "play":
            self.update_play(inp)
        elif self.scene == "level_done":
            if inp.confirm:
                if self.run.level_idx + 1 < len(LEVELS):
                    self.shop = Shop(self.run, self.game)
                    self.scene = "shop"
                else:
                    self.scene = "victory"
        elif self.scene == "shop":
            if self.shop.update(inp) == "next":
                self.begin_level(self.run.level_idx + 1)
        elif inp.confirm or inp.back:  # game_over / victory
            self.scene = "menu"

    def update_play(self, inp):
        g, run = self.game, self.run
        if inp.back:   # tres dedos na esquerda, segurado: abandona a fase
            self.scene = "menu"
            return
        g.update(inp, DT)
        if g.state == "dead_done":
            run.lives -= 1
            run.deaths += 1
            if run.lives > 0:
                self.new_attempt()
            else:
                self.scene = "game_over"
        elif g.state == "won":
            run.total_time += g.elapsed
            self.stars = stars_for(g.collected, g.coins_total, run.deaths)
            record_level(self.progress, run.level_idx, self.stars, len(LEVELS))
            self.scene = "level_done"

    # ---------------- desenho ----------------
    def draw(self, screen):
        if self.scene == "menu":
            self.menu.draw(screen, self.tracker, self.show_cam)
        elif self.scene == "levels":
            self.levelselect.draw(screen)
        elif self.scene == "calibrate":
            self.calibration.draw(screen)
        elif self.scene == "shop":
            self.shop.draw(screen)
        else:
            self.game.draw(screen)
            if self.scene == "play":
                self.draw_hud(screen)
            else:
                self.draw_end_panel(screen)
        self.draw_holds(screen)

    def draw_holds(self, screen):
        """Barrinha de progresso enquanto um gesto de confirmar/voltar está sendo segurado."""
        g = self.gestures
        for hold, label, color in ((g.confirm, "confirmando (dois punhos)", YELLOW),
                                   (g.back, "voltando (tres dedos esquerda)", BLUE)):
            if hold.progress > 0:
                bar = pygame.Rect(0, 0, 300, 14)
                bar.center = (WIDTH // 2, HEIGHT - 40)
                pygame.draw.rect(screen, (20, 20, 30), bar.inflate(8, 8), border_radius=6)
                pygame.draw.rect(screen, color, (bar.x, bar.y, int(bar.w * hold.progress), bar.h), border_radius=4)
                draw_text(screen, label, 20, color, (WIDTH // 2, HEIGHT - 62))

    def draw_hud(self, screen):
        g, run, cx = self.game, self.run, WIDTH // 2
        draw_text(screen, f"Fase {run.level_idx + 1}  {LEVELS[run.level_idx][0]}", 34, WHITE, (170, 24))
        for i in range(MAX_LIVES):
            screen.blit(assets.HEART["full" if i < run.lives else "empty"], (WIDTH - 50 - (MAX_LIVES - 1 - i) * 38, 8))
        if g.player.shield:
            screen.blit(assets.GEM, (WIDTH - 50 - MAX_LIVES * 38, 8))
        size = 34 + int(14 * g.coin_pop / 0.2)
        screen.blit(assets.COIN[0], (cx - 70, 6))
        draw_text(screen, f"{run.coins}", size, YELLOW, (cx + 10, 24))
        bar = pygame.Rect(cx - 70, 44, 120, 6)   # próxima vida extra
        pygame.draw.rect(screen, (40, 40, 55), bar)
        pygame.draw.rect(screen, GREEN, (bar.x, bar.y, bar.w * (run.coins_total % COINS_PER_LIFE) // COINS_PER_LIFE, bar.h))
        draw_text(screen, f"{g.collected}/{g.coins_total} na fase", 18, DIM, (cx + 10, 60))
        draw_text(screen, fmt_time(g.elapsed), 34, WHITE, (WIDTH - 300, 24))
        if g.life_flash > 0:
            draw_text(screen, "VIDA EXTRA!", 40, GREEN, (cx, 110))
        if self.show_cam and not self.tracker.error:
            draw_camera(screen, self.tracker, WIDTH - 210, 48)

    def draw_end_panel(self, screen):
        g, run, cx, cy = self.game, self.run, WIDTH // 2, HEIGHT // 2
        name = LEVELS[run.level_idx][0]
        dim(screen)
        panel = pygame.Rect(0, 0, 640, 360)
        panel.center = (cx, cy)
        draw_panel(screen, panel)
        if self.scene == "level_done":
            draw_text(screen, f"Fase {run.level_idx + 1} completa!", 60, YELLOW, (cx, cy - 130))
            draw_text(screen, name, 36, WHITE, (cx, cy - 85))
            for j, (key, label) in enumerate(STARS):
                x = cx - 200 + j * 200
                draw_star(screen, (x, cy - 30), 22, key in self.stars)
                draw_text(screen, label, 20, YELLOW if key in self.stars else DIM, (x, cy + 5))
            draw_text(screen, f"tempo  {fmt_time(g.elapsed)}", 32, WHITE, (cx, cy + 50))
            screen.blit(assets.COIN[0], (cx - 90, cy + 72))
            draw_text(screen, f"{g.collected}/{g.coins_total}   saldo {run.coins}", 30, YELLOW, (cx + 20, cy + 90))
            hint = "dois punhos: loja" if run.level_idx + 1 < len(LEVELS) else "dois punhos: continuar"
        elif self.scene == "game_over":
            draw_text(screen, "GAME OVER", 80, RED, (cx, cy - 80))
            draw_text(screen, f"Voce chegou ate a fase {run.level_idx + 1}", 36, WHITE, (cx, cy))
            draw_text(screen, "o progresso das fases vencidas fica salvo", 22, DIM, (cx, cy + 40))
            hint = "dois punhos: menu"
        else:
            draw_text(screen, "VOCE ZEROU!", 80, YELLOW, (cx, cy - 100))
            draw_text(screen, f"tempo total  {fmt_time(run.total_time)}", 34, WHITE, (cx, cy - 30))
            draw_text(screen, f"moedas coletadas  {run.coins_total}", 34, YELLOW, (cx, cy + 10))
            total = sum(len(s) for s in self.progress["stars"].values())
            draw_text(screen, f"estrelas  {total}/{3 * len(LEVELS)}", 34, BLUE, (cx, cy + 50))
            hint = "dois punhos: menu"
        if int(self.t * 2) % 2 == 0:
            draw_text(screen, hint, 28, DIM, (cx, cy + 140))


def run():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hand Control")
    assets.load()
    sound.init()
    clock = pygame.time.Clock()
    start = int(sys.argv[1]) - 1 if len(sys.argv) > 1 else None
    app = App(start)
    while not app.quit:
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE
                                          and app.scene == "menu"):
                app.quit = True
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                app.scene = "menu"
        app.update(app.read_input(events), events)
        app.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
    app.tracker.stop()
    pygame.quit()
