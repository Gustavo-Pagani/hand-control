"""Menu inicial: título, lista de opções navegada por gesto, status da câmera e personagens quicando."""
import random

import pygame

from . import assets
from .camview import draw_camera
from .config import DT, HEIGHT, TILE, WIDTH
from .physics import move_body
from .shop import Cursor
from .ui import DIM, GREEN, RED, WHITE, YELLOW, draw_fingers, draw_text

ITEMS = [("play", "Jogar"), ("levels", "Fases e estrelas"), ("calibrate", "Calibrar camera"), ("quit", "Sair")]


class Bouncer:
    """Personagem decorativo; reaproveita move_body com um chão fake."""

    def __init__(self, frames):
        self.frames = frames
        self.rect = pygame.Rect(random.randint(40, WIDTH - 80), random.randint(100, 300), 36, 36)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.vx, self.vy = random.choice([-120, 120]), 0.0
        self.on_ground = self.hit_wall = False
        self.hit_ceiling = None


class Menu:
    def __init__(self, background_game):
        self.bg_game = background_game   # um Game só para o fundo em parallax
        self.t = 0.0
        self.cursor = Cursor(len(ITEMS))
        self.bouncers = [Bouncer(assets.PLAYER["walk"])] + [
            Bouncer(assets.ENEMY[k]) for k in ("walker", "hopper", "walker", "bee")]
        self.floor = [pygame.Rect(0, HEIGHT - TILE, WIDTH, TILE),
                      pygame.Rect(-10, 0, 10, HEIGHT), pygame.Rect(WIDTH, 0, 10, HEIGHT)]

    def update(self, inp):
        """-> ação escolhida ('play', 'levels', 'calibrate', 'quit') ou None."""
        self.t += DT
        for b in self.bouncers:
            move_body(b, DT, self.floor)
            if b.hit_wall:
                b.vx = -b.vx
            if b.on_ground:
                b.vy = -random.randint(350, 700)
        self.cursor.update(inp)
        if inp.confirm:
            return ITEMS[self.cursor.idx][0]
        return None

    def draw(self, screen, tracker, show_cam):
        cx = WIDTH // 2
        self.bg_game.draw_background(screen, self.t * 40)
        top = assets.TERRAIN["grass"]["top"]
        for i, x in enumerate(range(0, WIDTH, TILE)):
            screen.blit(assets.pick(top, i), (x, HEIGHT - TILE))
        for b in self.bouncers:
            img = assets.frame(b.frames, self.t, 4)
            if b.vx > 0:
                img = assets.flip(img)
            screen.blit(img, img.get_rect(midbottom=b.rect.midbottom))
        band = pygame.Surface((WIDTH, 250), pygame.SRCALPHA)
        band.fill((0, 0, 0, 100))
        screen.blit(band, (0, 240))
        draw_text(screen, "HAND CONTROL", 120, WHITE, (cx, 130))
        draw_text(screen, "um platformer controlado pelas suas maos", 36, DIM, (cx, 195))
        for i, (_, label) in enumerate(ITEMS):
            selected = i == self.cursor.idx
            y = 275 + i * 46
            if selected:
                pygame.draw.rect(screen, (50, 48, 70), (cx - 220, y - 20, 440, 40), border_radius=6)
                pygame.draw.rect(screen, YELLOW, (cx - 220, y - 20, 440, 40), 2, border_radius=6)
            draw_fingers(screen, (cx - 205, y - 17), i + 1, YELLOW if selected else DIM)
            draw_text(screen, label, 40, YELLOW if selected else WHITE, (cx + 20, y))
        draw_text(screen, "dedos da mao direita escolhem   dois punhos fechados: confirma", 22, DIM, (cx, 462))
        if tracker.error:
            status, color = f"camera: {tracker.error}", RED
        elif not tracker.ready:
            status, color = f"camera: {tracker.status}...", YELLOW
        else:
            status = f"camera ok   {tracker.fps:.0f} fps   {tracker.latency_ms:.0f} ms"
            color = GREEN
        draw_text(screen, status, 24, color, (cx, 490))
        if show_cam and not tracker.error:
            draw_camera(screen, tracker, WIDTH - 220, HEIGHT - TILE - 170)
