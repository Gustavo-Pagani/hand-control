import random
import sys

import pygame

import assets
from game import HEIGHT, TILE, WIDTH, Game, Input, move_body
from levels import LEVELS

FPS = 60
DT = 1 / FPS  # passo fixo; nunca usar o retorno de clock.tick() (thread da webcam vai disputar CPU)
LIVES = 3
WHITE = (250, 250, 250)
DIM = (200, 200, 210)
YELLOW = (255, 215, 80)
RED = (235, 80, 80)
PANEL = (28, 26, 40)
SHADOW = (30, 30, 45)


def draw_text(surface, txt, size, color, center, shadow=True):
    f = assets.font(size)
    if shadow:
        img = f.render(txt, False, SHADOW)
        surface.blit(img, img.get_rect(center=(center[0] + 3, center[1] + 3)))
    img = f.render(txt, False, color)
    surface.blit(img, img.get_rect(center=center))


def fmt_time(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def read_keyboard(events) -> Input:
    keys = pygame.key.get_pressed()
    move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
    jump = any(e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_w) for e in events)
    return Input(move, jump)


class Bouncer:
    """Personagem decorativo do menu; reaproveita move_body com um chão fake."""

    def __init__(self, frames):
        self.frames = frames
        self.rect = pygame.Rect(random.randint(40, WIDTH - 80), random.randint(100, 300), 36, 36)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.vx, self.vy = random.choice([-120, 120]), 0.0
        self.on_ground = self.hit_wall = False


class App:
    def __init__(self, start_level=None):
        self.scene = "menu"
        self.level_idx = 0
        self.lives = LIVES
        self.game = None
        self.total_time = self.total_coins = self.total_coins_max = 0
        self.t = 0.0
        self.menu_game = Game(LEVELS[0][2], LEVELS[0][1])  # só para o fundo e o chão do menu
        self.bouncers = [Bouncer(assets.PLAYER["walk"])] + [
            Bouncer(assets.ENEMY[k]) for k in ("walker", "hopper", "walker", "hopper")]
        self.menu_floor = [pygame.Rect(0, HEIGHT - TILE, WIDTH, TILE),
                           pygame.Rect(-10, 0, 10, HEIGHT), pygame.Rect(WIDTH, 0, 10, HEIGHT)]
        if start_level is not None:
            self.start(start_level)

    def start(self, idx):
        self.level_idx, self.lives = idx, LIVES
        self.total_time = self.total_coins = self.total_coins_max = 0
        self.new_attempt()

    def new_attempt(self):
        name, theme, rows = LEVELS[self.level_idx]
        self.game = Game(rows, theme)
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
                    b.vy = -random.randint(350, 700)
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
            self.menu_game.draw_background(screen, self.t * 40)
            top = assets.TERRAIN["grass"]["top"]
            for i, x in enumerate(range(0, WIDTH, TILE)):
                screen.blit(assets.pick(top, i), (x, HEIGHT - TILE))
            for b in self.bouncers:
                img = assets.frame(b.frames, self.t, 4)
                if b.vx > 0:
                    img = assets.flip(img)
                screen.blit(img, img.get_rect(midbottom=b.rect.midbottom))
            draw_text(screen, "HAND CONTROL", 120, WHITE, (cx, 150))
            draw_text(screen, "um platformer de formas... com formas melhores", 36, DIM, (cx, 215))
            if blink:
                draw_text(screen, "ESPACO para jogar", 52, YELLOW, (cx, 320))
            draw_text(screen, "1-5 escolhe a fase   A/D anda   ESPACO pula   ESC sai", 30, DIM, (cx, 380))
            return

        self.game.draw(screen)
        name = LEVELS[self.level_idx][0]
        g = self.game
        if self.scene == "play":
            draw_text(screen, f"Fase {self.level_idx + 1}  {name}", 34, WHITE, (170, 24))
            for i in range(LIVES):
                screen.blit(assets.HEART["full" if i < self.lives else "empty"], (WIDTH - 50 - i * 40, 8))
            screen.blit(assets.COIN[0], (cx - 70, 6))
            draw_text(screen, f"{g.collected}/{g.coins_total}", 34, YELLOW, (cx + 10, 24))
            draw_text(screen, fmt_time(g.elapsed), 34, WHITE, (WIDTH - 260, 24))
            return

        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))
        panel = pygame.Rect(0, 0, 600, 320)
        panel.center = (cx, cy)
        pygame.draw.rect(screen, PANEL, panel, border_radius=8)
        pygame.draw.rect(screen, YELLOW, panel, 4, border_radius=8)
        if self.scene == "level_done":
            draw_text(screen, f"Fase {self.level_idx + 1} completa!", 64, YELLOW, (cx, cy - 100))
            draw_text(screen, name, 40, WHITE, (cx, cy - 50))
            draw_text(screen, f"tempo  {fmt_time(g.elapsed)}", 38, WHITE, (cx, cy + 5))
            screen.blit(assets.COIN[0], (cx - 80, cy + 27))
            draw_text(screen, f"{g.collected}/{g.coins_total}", 38, YELLOW, (cx + 10, cy + 45))
            hint = "ESPACO para continuar"
        elif self.scene == "game_over":
            draw_text(screen, "GAME OVER", 80, RED, (cx, cy - 80))
            draw_text(screen, f"Voce chegou ate a fase {self.level_idx + 1}", 38, WHITE, (cx, cy))
            hint = "ESPACO para o menu"
        else:
            draw_text(screen, "VOCE ZEROU!", 80, YELLOW, (cx, cy - 90))
            draw_text(screen, f"tempo total  {fmt_time(self.total_time)}", 38, WHITE, (cx, cy - 15))
            screen.blit(assets.COIN[0], (cx - 80, cy + 7))
            draw_text(screen, f"{self.total_coins}/{self.total_coins_max}", 38, YELLOW, (cx + 10, cy + 25))
            hint = "ESPACO para o menu"
        if blink:
            draw_text(screen, hint, 32, DIM, (cx, cy + 120))


def main():
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
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                return
        app.update(read_keyboard(events), events)
        app.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
