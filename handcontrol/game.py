"""Uma tentativa em uma fase: regras, colisões entre entidades, câmera e desenho do mundo."""
import pygame

from . import assets, sound
from .config import (DEATH_TIME, GRAVITY, HEIGHT, HIGH_JUMP, JUMP_SPEED, PLAYER_W, STOMPABLE, STOMP_BOUNCE, TILE,
                     WIDTH)
from .effects import Effects
from .entities import Enemy, Player
from .inputs import Input
from .level import load_level
from .run import Run
from .ui import BLUE, RED, WHITE, YELLOW

ENEMY_COLOR = {"walker": (80, 160, 230), "hopper": (240, 190, 60), "cannon": (230, 110, 60), "bee": (200, 120, 60)}


class Game:
    """state: playing -> dead -> dead_done, ou playing -> won."""

    def __init__(self, rows: list[str], theme: str = "grass", run: Run = None):
        self.run = run or Run()
        self.level = load_level(rows, theme)
        self.theme = theme
        lv = self.level
        spawn = self.run.checkpoint.topleft if self.run.checkpoint else lv.spawn
        self.player = Player(*spawn, shield=self.run.shield, jump_mult=HIGH_JUMP if self.run.highjump else 1.0)
        self.enemies = [Enemy(*e) for e in lv.enemies]
        self.rocks = []
        self.coins = list(lv.coins)
        self.coins_total = len(self.coins)
        self.collected = 0
        self.checkpoint_active = self.run.checkpoint is not None
        self.fx = Effects()
        self.coin_pop = 0.0      # s restantes do "pulo" do contador no HUD
        self.life_flash = 0.0    # s restantes do aviso de vida extra
        self.elapsed = 0.0
        self.t = 0.0
        self.state = "playing"
        self.timer = 0.0
        self.camera_x = 0

    # ---------------- regras ----------------
    def die(self):
        self.state = "dead"
        self.timer = DEATH_TIME
        self.player.vy = -450.0
        self.fx.burst(self.player.rect.center, RED, 14, 300)
        self.fx.shake_screen(8)
        sound.play("die")

    def hurt(self):
        """Toque letal no player: escudo absorve uma vez, senão morre."""
        result = self.player.hit()
        if result == "dead":
            self.die()
        elif result == "shield":
            self.run.shield = False
            self.fx.burst(self.player.rect.center, BLUE, 12, 260)
            self.fx.shake_screen(4)
            sound.play("shield")

    def collect_coin(self, pos):
        self.collected += 1
        self.coin_pop = 0.2
        self.fx.burst(pos, YELLOW, 6, 160)
        sound.play("coin")
        if self.run.add_coins(1):
            self.life_flash = 1.5
            sound.play("heart")

    def open_block(self, block):
        block.used, block.bump = True, 0.2
        self.fx.burst(block.rect.midtop, WHITE, 6, 150)
        sound.play("block")
        if block.content == "heart" and self.run.add_life():
            self.life_flash = 1.5
            sound.play("heart")
        else:
            self.coins_total += 1
            self.collect_coin(block.rect.midtop)

    def update(self, inp: Input, dt: float):
        p, lv = self.player, self.level
        self.t += dt
        self.fx.update(dt)
        self.coin_pop = max(0.0, self.coin_pop - dt)
        self.life_flash = max(0.0, self.life_flash - dt)
        for b in lv.qblocks:
            b.bump = max(0.0, b.bump - dt)
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
        was_grounded = p.on_ground
        p.update(inp, dt, lv.solids)
        if was_grounded and not p.on_ground and p.vy < 0:
            sound.play("jump")
        p.x = pygame.math.clamp(p.x, 0, lv.w - PLAYER_W)
        p.rect.x = round(p.x)
        if p.hit_ceiling is not None:
            for b in lv.qblocks:
                if not b.used and b.rect is p.hit_ceiling:
                    self.open_block(b)

        for e in self.enemies:
            rock = e.update(dt, lv.solids, p.rect)
            if rock:
                self.rocks.append(rock)
        self.enemies = [e for e in self.enemies if e.rect.top <= lv.h]
        for r in self.rocks:
            r.update(dt, lv.solids)
        self.rocks = [r for r in self.rocks if r.alive and 0 <= r.rect.x <= lv.w]

        for e in self.enemies:
            if p.rect.colliderect(e.rect):
                if e.kind in STOMPABLE and p.vy > 0 and p.prev_bottom <= e.rect.top:   # veio de cima: pisão
                    self.enemies.remove(e)
                    p.rect.bottom = e.rect.top
                    p.y = p.rect.y
                    p.vy = -JUMP_SPEED * STOMP_BOUNCE
                    self.fx.burst(e.rect.center, ENEMY_COLOR[e.kind], 10, 220)
                    self.fx.shake_screen(2)
                    sound.play("stomp")
                    break
                self.hurt()
                if self.state != "playing":
                    return
        for r in self.rocks:
            if p.rect.colliderect(r.rect):
                r.alive = False
                self.hurt()
                if self.state != "playing":
                    return
        if p.rect.collidelist(lv.spikes) != -1:
            self.hurt()
            if self.state != "playing":
                return
        if p.rect.top > lv.h:
            self.die()
            return
        for c in p.rect.collidelistall(self.coins)[::-1]:
            pos = self.coins[c].center
            del self.coins[c]
            self.collect_coin(pos)
        if lv.checkpoint and not self.checkpoint_active and p.rect.colliderect(lv.checkpoint):
            self.checkpoint_active = True
            self.run.checkpoint = lv.checkpoint
            self.fx.burst(lv.checkpoint.center, YELLOW, 10, 200)
            sound.play("checkpoint")
        if p.rect.colliderect(lv.goal):
            self.state = "won"
            sound.play("star")
        self.camera_x = pygame.math.clamp(p.rect.centerx - WIDTH // 2, 0, lv.w - WIDTH)

    # ---------------- desenho ----------------
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
        lv, t = self.level, self.t
        sx, sy = self.fx.offset()
        cx = self.camera_x + sx
        self.draw_background(surface, cx)
        visible = pygame.Rect(cx - TILE, 0, WIDTH + 2 * TILE, HEIGHT)
        for surf, x, y in lv.deco + lv.tiles:
            if visible.left <= x <= visible.right:
                surface.blit(surf, (x - cx, y + sy))
        for b in lv.qblocks:
            if b.rect.colliderect(visible):
                lift = int(6 * b.bump / 0.2)
                surface.blit(assets.QBLOCK[1 if b.used else 0], (b.rect.x - cx, b.rect.y + sy - lift))
        for s in lv.spikes:
            if s.colliderect(visible):
                surface.blit(assets.SPIKE, (s.x - cx, s.bottom - TILE + sy))
        coin = assets.frame(assets.COIN, t, 4)
        for c in self.coins:
            if c.colliderect(visible):
                surface.blit(coin, (c.centerx - TILE // 2 - cx, c.centery - TILE // 2 + sy))
        if lv.checkpoint:
            k = lv.checkpoint
            surface.blit(assets.POLE, (k.x - cx, k.y + sy))
            surface.blit(assets.CHECKPOINT[1 if self.checkpoint_active else 0], (k.x - cx, k.y - TILE + sy))
        g = lv.goal
        for y in range(g.top + TILE, g.bottom, TILE):
            surface.blit(assets.POLE, (g.x - cx, y + sy))
        surface.blit(assets.frame(assets.FLAG, t, 3), (g.x - cx, g.top + sy))
        for e in self.enemies:
            if not e.rect.colliderect(visible):
                continue
            frames = assets.ENEMY[e.kind]
            if e.kind == "hopper":
                img = frames[1] if not e.on_ground else assets.frame(frames, t, 3)
            elif e.kind == "cannon":
                img = frames[1] if e.recoil > 0 else frames[0]
            else:
                img = assets.frame(frames, t, 6 if e.kind == "bee" else 3)
            if e.facing > 0:
                img = assets.flip(img)
            surface.blit(img, img.get_rect(midbottom=(e.rect.centerx - cx, e.rect.bottom + sy)))
        for r in self.rocks:
            surface.blit(assets.ROCK, assets.ROCK.get_rect(center=(r.rect.centerx - cx, r.rect.centery + sy)))
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
        center = (p.rect.centerx - cx, p.rect.centery + sy)
        if p.shield:
            halo = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.circle(halo, (110, 170, 255, 70), (32, 32), 30)
            pygame.draw.circle(halo, (110, 170, 255, 180), (32, 32), 30, 2)
            surface.blit(halo, halo.get_rect(center=center))
        if not (p.invuln > 0 and int(t * 20) % 2):   # pisca enquanto invencível
            surface.blit(img, img.get_rect(midbottom=(center[0], p.rect.bottom + 2 + sy)))
        self.fx.draw(surface, cx)
