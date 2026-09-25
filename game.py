import math
import re
from dataclasses import dataclass, field

import pygame

import assets

TILE = 36                    # 18 px do Kenney x 2
WIDTH, HEIGHT = 1080, 612    # 30 x 17 tiles
# física em px/s escalada por 36/32 para manter altura de pulo (3,6 tiles) e alcance (6,7 tiles)
SPEED = 338
GRAVITY = 2025
JUMP_SPEED = 731
MAX_FALL = 1012
COYOTE_TIME = 0.10   # s: ainda pode pular depois de sair da beirada
JUMP_BUFFER = 0.12   # s: pulo comandado antes de tocar o chão executa ao tocar
ENEMY_SPEED = 90
HOP_INTERVAL = 1.4
HOP_SPEED = 506
STOMP_BOUNCE = 0.6
DEATH_TIME = 1.0
PLAYER_W, PLAYER_H = 36, 44
ENEMY_SIZE = {"walker": (36, 28), "hopper": (36, 36)}
VALID = "#P.EH^oG"


@dataclass
class Input:
    move: int   # -1 esquerda, 0 parado, +1 direita
    jump: bool  # True só no frame em que o pulo foi comandado (borda de subida)


@dataclass
class LevelData:
    solids: list = field(default_factory=list)
    tiles: list = field(default_factory=list)     # (surf, x, y) para desenhar
    deco: list = field(default_factory=list)      # (surf, x, y) atrás dos tiles
    enemies: list = field(default_factory=list)   # (x, y, kind)
    spikes: list = field(default_factory=list)
    coins: list = field(default_factory=list)
    spawn: tuple = (0, 0)
    goal: pygame.Rect = None
    w: int = 0
    h: int = 0


def load_level(rows: list[str], theme: str = "grass") -> LevelData:
    assert len(rows) * TILE == HEIGHT, f"mapa precisa de {HEIGHT // TILE} linhas, tem {len(rows)}"
    assert len({len(r) for r in rows}) == 1, "todas as linhas do mapa precisam ter o mesmo comprimento"
    assert len(rows[0]) * TILE >= WIDTH, "fase mais estreita que a janela"
    lv = LevelData(w=len(rows[0]) * TILE, h=len(rows) * TILE)
    terrain = assets.TERRAIN.get(theme)  # None nos testes sem assets carregados
    spawns, goals = [], []
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch not in VALID:
                raise ValueError(f"caractere {ch!r} inválido no mapa: linha {r}, coluna {c}")
            x, y = c * TILE, r * TILE
            if ch == "P":
                spawns.append((x, y))
            elif ch in "EH":
                lv.enemies.append((x, y, "walker" if ch == "E" else "hopper"))
            elif ch == "^":
                lv.spikes.append(pygame.Rect(x, y + TILE - 12, TILE, 12))
            elif ch == "o":
                lv.coins.append(pygame.Rect(x + 10, y + 10, 16, 16))
            elif ch == "G":
                goals.append(pygame.Rect(x, y, TILE, TILE))
            elif ch == "#" and terrain:
                top = r == 0 or rows[r - 1][c] != "#"
                lv.tiles.append((assets.pick(terrain["top" if top else "fill"], (r, c)), x, y))
                every = assets.THEMES[theme][6]
                if top and r > 0 and rows[r - 1][c] == "." and assets.pick(range(every), (c, r)) == 0:
                    lv.deco.append((assets.pick(terrain["deco"], (r, c, 1)), x, y - TILE))
        # funde '#' vizinhos numa linha: 1 Rect por sequência, não por tile
        for m in re.finditer("#+", line):
            lv.solids.append(pygame.Rect(m.start() * TILE, r * TILE, len(m[0]) * TILE, TILE))
    if len(spawns) != 1:
        raise ValueError(f"mapa precisa de exatamente um 'P', tem {len(spawns)}")
    if not goals:
        raise ValueError("mapa precisa de pelo menos um 'G'")
    lv.spawn = spawns[0]
    lv.goal = goals[0].unionall(goals[1:])
    return lv


def move_body(body, dt: float, solids: list[pygame.Rect]):
    """Gravidade, move X e resolve, move Y e resolve. Seta on_ground e hit_wall."""
    body.vy = min(body.vy + GRAVITY * dt, MAX_FALL)

    body.x += body.vx * dt
    body.rect.x = round(body.x)
    body.hit_wall = False
    for s in solids:
        if body.rect.colliderect(s):
            if body.vx > 0:
                body.rect.right = s.left
            elif body.vx < 0:
                body.rect.left = s.right
            body.x = body.rect.x
            body.hit_wall = True

    body.y += body.vy * dt
    # ponytail: arredonda na direção do movimento; com round/int os 0,5 px/frame
    # de gravidade parado no chão não encostam e on_ground piscaria frame sim, frame não
    body.rect.y = math.ceil(body.y) if body.vy > 0 else math.floor(body.y)
    body.on_ground = False
    for s in solids:
        if body.rect.colliderect(s):
            if body.vy > 0:
                body.rect.bottom = s.top
                body.on_ground = True
            else:
                body.rect.top = s.bottom
            body.vy = 0
            body.y = body.rect.y


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y + TILE - PLAYER_H, PLAYER_W, PLAYER_H)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.vx = self.vy = 0.0
        self.on_ground = self.hit_wall = False
        self.prev_bottom = self.rect.bottom
        self.coyote = self.jump_buf = 0.0
        self.facing = 1

    def update(self, inp: Input, dt: float, solids: list[pygame.Rect]):
        self.prev_bottom = self.rect.bottom
        self.vx = inp.move * SPEED
        if inp.move:
            self.facing = inp.move
        self.coyote = COYOTE_TIME if self.on_ground else self.coyote - dt
        self.jump_buf = JUMP_BUFFER if inp.jump else self.jump_buf - dt
        if self.jump_buf > 0 and self.coyote > 0:
            self.vy = -JUMP_SPEED
            self.coyote = self.jump_buf = 0.0
        move_body(self, dt, solids)


class Enemy:
    def __init__(self, x, y, kind):
        self.kind = kind
        w, h = ENEMY_SIZE[kind]
        self.rect = pygame.Rect(x + (TILE - w) // 2, y + TILE - h, w, h)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.vx, self.vy = -ENEMY_SPEED, 0.0
        self.on_ground = self.hit_wall = False
        self.timer = HOP_INTERVAL

    def update(self, dt: float, solids: list[pygame.Rect]):
        move_body(self, dt, solids)
        if self.hit_wall:
            self.vx = -self.vx
        if self.on_ground:
            foot_x = self.rect.left if self.vx < 0 else self.rect.right - 2
            probe = pygame.Rect(foot_x, self.rect.bottom + 1, 2, 2)
            if probe.collidelist(solids) == -1:
                self.vx = -self.vx
            if self.kind == "hopper":
                self.timer -= dt
                if self.timer <= 0:
                    self.vy = -HOP_SPEED
                    self.timer = HOP_INTERVAL


class Game:
    """Uma tentativa em uma fase. state: playing -> dead -> dead_done, ou playing -> won."""

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
                if p.vy > 0 and p.prev_bottom <= e.rect.top:
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
