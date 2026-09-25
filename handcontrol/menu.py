"""Menu inicial: título, instruções, status da câmera e personagens quicando."""
import random

import pygame

from . import assets
from .camview import draw_camera
from .config import DT, HEIGHT, TILE, WIDTH
from .physics import move_body
from .ui import DIM, GREEN, RED, WHITE, YELLOW, draw_text


class Bouncer:
    """Personagem decorativo; reaproveita move_body com um chão fake."""

    def __init__(self, frames):
        self.frames = frames
        self.rect = pygame.Rect(random.randint(40, WIDTH - 80), random.randint(100, 300), 36, 36)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.vx, self.vy = random.choice([-120, 120]), 0.0
        self.on_ground = self.hit_wall = False


class Menu:
    def __init__(self, background_game):
        self.bg_game = background_game   # um Game só para o fundo em parallax
        self.t = 0.0
        self.bouncers = [Bouncer(assets.PLAYER["walk"])] + [
            Bouncer(assets.ENEMY[k]) for k in ("walker", "hopper", "walker", "hopper")]
        self.floor = [pygame.Rect(0, HEIGHT - TILE, WIDTH, TILE),
                      pygame.Rect(-10, 0, 10, HEIGHT), pygame.Rect(WIDTH, 0, 10, HEIGHT)]

    def update(self):
        self.t += DT
        for b in self.bouncers:
            move_body(b, DT, self.floor)
            if b.hit_wall:
                b.vx = -b.vx
            if b.on_ground:
                b.vy = -random.randint(350, 700)

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
        band = pygame.Surface((WIDTH, 210), pygame.SRCALPHA)
        band.fill((0, 0, 0, 90))
        screen.blit(band, (0, 258))
        draw_text(screen, "HAND CONTROL", 120, WHITE, (cx, 140))
        draw_text(screen, "um platformer controlado pela sua mao", 36, DIM, (cx, 205))
        if int(self.t * 2) % 2 == 0:
            draw_text(screen, "ESPACO ou MAO ABERTA para jogar", 48, YELLOW, (cx, 290))
        draw_text(screen, "C  calibrar camera", 40, GREEN, (cx, 345))
        draw_text(screen, "1-5 escolhe a fase   A/D anda   ESPACO pula   V mostra/esconde camera   ESC sai",
                  26, DIM, (cx, 395))
        if tracker.error:
            status, color = f"camera: {tracker.error}", RED
        elif not tracker.ready:
            status, color = f"camera: {tracker.status}...", YELLOW
        else:
            status = f"camera ok   {tracker.fps:.0f} fps   {tracker.latency_ms:.0f} ms   gesto: {tracker.stable}"
            color = GREEN
        draw_text(screen, status, 26, color, (cx, 440))
        if show_cam and not tracker.error:
            draw_camera(screen, tracker, WIDTH - 220, HEIGHT - TILE - 170)
