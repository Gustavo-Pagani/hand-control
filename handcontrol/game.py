"""Uma tentativa em uma fase: regras, colisões entre entidades, câmera e desenho do mundo."""
import pygame

from . import assets
from .config import DEATH_TIME, GRAVITY, HEIGHT, JUMP_SPEED, PLAYER_W, STOMP_BOUNCE, TILE, WIDTH
from .entities import Enemy, Player
from .inputs import Input
from .level import load_level


class Game:
    """state: playing -> dead -> dead_done, ou playing -> won."""

    def __init__(self, rows: list[str], theme: str = "grass"):
        self.level = load_level(rows, theme)
        self.theme = theme
        self.player = Player(*self.level.spawn)
        self.enemies = [Enemy(*e) for e in self.level.enemies]
        self.coins = list(self.level.coins)
        self.coins_total = len(self.coins)
        self.collected = 0
        self.elapsed = 0.0
        self.t = 0.0
        self.state = "playing"
        self.timer = 0.0
        self.camera_x = 0

    def die(self):
        self.state = "dead"
        self.timer = DEATH_TIME
        self.player.vy = -450.0

    def update(self, inp: Input, dt: float):
        p, lv = self.player, self.level
        self.t += dt
        if self.state == "dead":
            p.vy += GRAVITY * dt
            p.y += p.vy * dt
            p.rect.y = round(p.y)
            self.timer -= dt
            if self.timer <= 0:
                self.state = "dead_done"
            return
        if self.state != "playing":
            return

        self.elapsed += dt
        p.update(inp, dt, lv.solids)
        p.x = pygame.math.clamp(p.x, 0, lv.w - PLAYER_W)
        p.rect.x = round(p.x)
        for e in self.enemies:
            e.update(dt, lv.solids)
        self.enemies = [e for e in self.enemies if e.rect.top <= lv.h]

        for e in self.enemies:
            if p.rect.colliderect(e.rect):
                if p.vy > 0 and p.prev_bottom <= e.rect.top:   # veio de cima: pisão
                    self.enemies.remove(e)
                    p.rect.bottom = e.rect.top
                    p.y = p.rect.y
                    p.vy = -JUMP_SPEED * STOMP_BOUNCE
                    break
                self.die()
                return
        if p.rect.collidelist(lv.spikes) != -1 or p.rect.top > lv.h:
            self.die()
            return
        for c in p.rect.collidelistall(self.coins)[::-1]:
            del self.coins[c]
            self.collected += 1
        if p.rect.colliderect(lv.goal):
            self.state = "won"
        self.camera_x = pygame.math.clamp(p.rect.centerx - WIDTH // 2, 0, lv.w - WIDTH)

    def draw_background(self, surface, cx):
        bg = assets.BG[self.theme]
        surface.fill(bg["sky"])
        for factor, y, hills, fill in ((0.2, HEIGHT - 300, bg["far"], bg["far_fill"]),
                                        (0.5, HEIGHT - 190, bg["hills"], bg["fill"])):
            off = int(cx * factor) % 48
            for x in range(-off, WIDTH, 48):
                surface.blit(hills, (x, y))
                for yy in range(y + 48, HEIGHT, 48):
                    surface.blit(fill, (x, yy))

    def draw(self, surface):
        cx, lv, t = self.camera_x, self.level, self.t
        self.draw_background(surface, cx)
        visible = pygame.Rect(cx - TILE, 0, WIDTH + 2 * TILE, HEIGHT)
        for surf, x, y in lv.deco + lv.tiles:
            if visible.left <= x <= visible.right:
                surface.blit(surf, (x - cx, y))
        for s in lv.spikes:
            if s.colliderect(visible):
                surface.blit(assets.SPIKE, (s.x - cx, s.bottom - TILE))
        coin = assets.frame(assets.COIN, t, 4)
        for c in self.coins:
            if c.colliderect(visible):
                surface.blit(coin, (c.centerx - TILE // 2 - cx, c.centery - TILE // 2))
        g = lv.goal
        for y in range(g.top + TILE, g.bottom, TILE):
            surface.blit(assets.POLE, (g.x - cx, y))
        surface.blit(assets.frame(assets.FLAG, t, 3), (g.x - cx, g.top))
        for e in self.enemies:
            if e.rect.colliderect(visible):
                frames = assets.ENEMY[e.kind]
                img = frames[1] if e.kind == "hopper" and not e.on_ground else assets.frame(frames, t, 3)
                if e.vx > 0:
                    img = assets.flip(img)
                surface.blit(img, img.get_rect(midbottom=(e.rect.centerx - cx, e.rect.bottom)))
        p = self.player
        if self.state != "playing":
            img = pygame.transform.flip(assets.PLAYER["idle"][0], p.facing < 0, True)
        elif not p.on_ground:
            img = assets.PLAYER["jump"][0]
        elif p.vx:
            img = assets.frame(assets.PLAYER["walk"], t, 8)
        else:
            img = assets.PLAYER["idle"][0]
        if p.facing < 0 and self.state == "playing":
            img = assets.flip(img)
        surface.blit(img, img.get_rect(midbottom=(p.rect.centerx - cx, p.rect.bottom + 2)))
