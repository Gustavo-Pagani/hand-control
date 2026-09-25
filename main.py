import random
import sys

import pygame

from game import BLUE, GREEN, HEIGHT, RED, ORANGE, YELLOW, WIDTH, Game, Input, move_body
from levels import LEVELS

FPS = 60
DT = 1 / FPS  # passo fixo; nunca usar o retorno de clock.tick() (thread da webcam vai disputar CPU)
LIVES = 3
WHITE = (240, 240, 245)
DIM = (180, 180, 190)
PANEL = (20, 20, 30)
MENU_BG = (25, 30, 50)

_fonts = {}


def draw_text(surface, txt, size, color, center):
    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont(None, size)
    img = _fonts[size].render(txt, True, color)
    surface.blit(img, img.get_rect(center=center))


def fmt_time(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def read_keyboard(events) -> Input:
    keys = pygame.key.get_pressed()
    move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
    jump = any(e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_w) for e in events)
    return Input(move, jump)


class Bouncer:
    """Quadradinho decorativo do menu; reaproveita move_body com um chão fake."""

    def __init__(self):
        self.x, self.y = float(random.randint(40, WIDTH - 80)), float(random.randint(100, 300))
        self.rect = pygame.Rect(self.x, self.y, 24, 24)
        self.vx, self.vy = random.choice([-120, 120]), 0.0
        self.on_ground = self.hit_wall = False
        self.color = random.choice([BLUE, RED, ORANGE, YELLOW, GREEN])


class App:
    def __init__(self, start_level=None):
        self.scene = "menu"
        self.level_idx = 0
        self.lives = LIVES
        self.game = None
        self.total_time = self.total_coins = self.total_coins_max = 0
        self.t = 0.0
        self.bouncers = [Bouncer() for _ in range(6)]
        self.menu_floor = [pygame.Rect(0, HEIGHT - 60, WIDTH, 60),
                           pygame.Rect(-10, 0, 10, HEIGHT), pygame.Rect(WIDTH, 0, 10, HEIGHT)]
        if start_level is not None:
            self.start(start_level)

    def start(self, idx):
        self.level_idx, self.lives = idx, LIVES
        self.total_time = self.total_coins = self.total_coins_max = 0
        self.new_attempt()

    def new_attempt(self):
        name, bg, rows = LEVELS[self.level_idx]
        self.game = Game(rows, bg)
        self.scene = "play"

    def update(self, inp, events):
        self.t += DT
        keys = [e.key for e in events if e.type == pygame.KEYDOWN]
        if self.scene == "menu":
            for b in self.bouncers:
                move_body(b, DT, self.menu_floor)
                if b.hit_wall:
                    b.vx = -b.vx
                if b.on_ground:
                    b.vy = -random.randint(300, 600)
            if inp.jump:
                self.start(0)
            for k in keys:
                if pygame.K_1 <= k <= pygame.K_5:
                    self.start(k - pygame.K_1)
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

    def draw(self, screen):
        cx, cy = WIDTH // 2, HEIGHT // 2
        blink = int(self.t * 2) % 2 == 0
        if self.scene == "menu":
            screen.fill(MENU_BG)
            pygame.draw.rect(screen, GREEN, self.menu_floor[0])
            for b in self.bouncers:
                pygame.draw.rect(screen, b.color, b.rect)
            draw_text(screen, "HAND CONTROL", 96, PANEL, (cx + 4, 154))
            draw_text(screen, "HAND CONTROL", 96, WHITE, (cx, 150))
            draw_text(screen, "um platformer de formas", 32, DIM, (cx, 205))
            if blink:
                draw_text(screen, "ESPAÇO para jogar", 40, YELLOW, (cx, 300))
            draw_text(screen, "1-5 escolhe a fase   ·   A/D anda   ·   ESPAÇO pula   ·   ESC sai", 24, DIM, (cx, 350))
            return

        self.game.draw(screen)
        name = LEVELS[self.level_idx][0]
        g = self.game
        if self.scene == "play":
            draw_text(screen, f"Fase {self.level_idx + 1} · {name}", 28, WHITE, (140, 20))
            for i in range(self.lives):
                pygame.draw.rect(screen, BLUE, (WIDTH - 40 - i * 28, 10, 20, 20))
            draw_text(screen, f"moedas {g.collected}/{g.coins_total}", 28, YELLOW, (cx, 20))
            draw_text(screen, fmt_time(g.elapsed), 28, WHITE, (WIDTH - 200, 20))
            return

        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        screen.blit(dim, (0, 0))
        panel = pygame.Rect(0, 0, 560, 300)
        panel.center = (cx, cy)
        pygame.draw.rect(screen, PANEL, panel, border_radius=12)
        pygame.draw.rect(screen, YELLOW, panel, 3, border_radius=12)
        if self.scene == "level_done":
            draw_text(screen, f"Fase {self.level_idx + 1} completa!", 56, YELLOW, (cx, cy - 90))
            draw_text(screen, name, 36, WHITE, (cx, cy - 40))
            draw_text(screen, f"tempo  {fmt_time(g.elapsed)}", 32, WHITE, (cx, cy + 10))
            draw_text(screen, f"moedas  {g.collected}/{g.coins_total}", 32, YELLOW, (cx, cy + 45))
            hint = "ESPAÇO para continuar"
        elif self.scene == "game_over":
            draw_text(screen, "GAME OVER", 64, RED, (cx, cy - 70))
            draw_text(screen, f"Você chegou até a fase {self.level_idx + 1}", 32, WHITE, (cx, cy))
            hint = "ESPAÇO para o menu"
        else:
            draw_text(screen, "VOCÊ ZEROU!", 64, YELLOW, (cx, cy - 80))
            draw_text(screen, f"tempo total  {fmt_time(self.total_time)}", 32, WHITE, (cx, cy - 10))
            draw_text(screen, f"moedas  {self.total_coins}/{self.total_coins_max}", 32, YELLOW, (cx, cy + 30))
            hint = "ESPAÇO para o menu"
        if blink:
            draw_text(screen, hint, 28, DIM, (cx, cy + 110))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hand Control")
    clock = pygame.time.Clock()
    start = int(sys.argv[1]) - 1 if len(sys.argv) > 1 else None
    app = App(start)
    while True:
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                return
        app.update(read_keyboard(events), events)
        app.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
