"""Mapa ASCII -> LevelData (colisão, spawns, blocos, tiles para desenhar)."""
import re
from dataclasses import dataclass, field

import pygame

from . import assets
from .config import HEART_EVERY, HEIGHT, TILE, VALID_CHARS, WIDTH


@dataclass
class QBlock:
    rect: pygame.Rect
    content: str          # "coin" | "heart"
    used: bool = False
    bump: float = 0.0     # s restantes do pulinho ao ser batido


@dataclass
class LevelData:
    solids: list = field(default_factory=list)
    tiles: list = field(default_factory=list)     # (surf, x, y) para desenhar
    deco: list = field(default_factory=list)      # (surf, x, y) atrás dos tiles
    enemies: list = field(default_factory=list)   # (x, y, kind)
    spikes: list = field(default_factory=list)
    coins: list = field(default_factory=list)
    qblocks: list = field(default_factory=list)
    checkpoint: pygame.Rect = None
    spawn: tuple = (0, 0)
    goal: pygame.Rect = None
    w: int = 0
    h: int = 0


KINDS = {"E": "walker", "H": "hopper", "C": "cannon", "B": "bee"}


def load_level(rows: list[str], theme: str = "grass") -> LevelData:
    assert len(rows) * TILE == HEIGHT, f"mapa precisa de {HEIGHT // TILE} linhas, tem {len(rows)}"
    assert len({len(r) for r in rows}) == 1, "todas as linhas do mapa precisam ter o mesmo comprimento"
    assert len(rows[0]) * TILE >= WIDTH, "fase mais estreita que a janela"
    lv = LevelData(w=len(rows[0]) * TILE, h=len(rows) * TILE)
    terrain = assets.TERRAIN.get(theme)  # None nos testes sem assets carregados
    spawns, goals = [], []
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch not in VALID_CHARS:
                raise ValueError(f"caractere {ch!r} inválido no mapa: linha {r}, coluna {c}")
            x, y = c * TILE, r * TILE
            if ch == "P":
                spawns.append((x, y))
            elif ch in KINDS:
                lv.enemies.append((x, y, KINDS[ch]))
            elif ch == "^":
                lv.spikes.append(pygame.Rect(x, y + TILE - 12, TILE, 12))
            elif ch == "o":
                lv.coins.append(pygame.Rect(x + 10, y + 10, 16, 16))
            elif ch == "G":
                goals.append(pygame.Rect(x, y, TILE, TILE))
            elif ch == "K":
                lv.checkpoint = pygame.Rect(x, y, TILE, TILE)
            elif ch == "?":
                rect = pygame.Rect(x, y, TILE, TILE)
                lv.solids.append(rect)
                lv.qblocks.append(QBlock(rect, "heart" if len(lv.qblocks) % HEART_EVERY == HEART_EVERY - 1 else "coin"))
            elif ch == "#" and terrain:
                top = r == 0 or rows[r - 1][c] != "#"
                lv.tiles.append((assets.pick(terrain["top" if top else "fill"], (r, c)), x, y))
                every = assets.THEMES[theme][6]
                if top and r > 0 and rows[r - 1][c] == "." and assets.pick(range(every), (c, r)) == 0:
                    lv.deco.append((assets.pick(terrain["deco"], (r, c, 1)), x, y - TILE))
        # funde '#' vizinhos numa linha: 1 Rect por sequência, não por tile (sem isso o player engancha)
        for m in re.finditer("#+", line):
            lv.solids.append(pygame.Rect(m.start() * TILE, r * TILE, len(m[0]) * TILE, TILE))
    if len(spawns) != 1:
        raise ValueError(f"mapa precisa de exatamente um 'P', tem {len(spawns)}")
    if not goals:
        raise ValueError("mapa precisa de pelo menos um 'G'")
    lv.spawn = spawns[0]
    lv.goal = goals[0].unionall(goals[1:])
    return lv
