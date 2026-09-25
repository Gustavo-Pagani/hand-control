"""Carrega os spritesheets Kenney (CC0) uma vez e expõe dicionários de Surfaces já escaladas 2x."""
import os
import zlib

import pygame

DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
SCALE = 2

# tema -> (sheet, linhas de topo, linhas de preenchimento, colunas, decorações [(r,c)], colunas do fundo,
#          1 decoração a cada N tiles de topo, tinta multiplicativa do fundo)
THEMES = {
    "grass": ("tiles", [0, 1], [6, 7], range(4), [(6, 4), (6, 5), (6, 6)], (6, 7), 5, None),
    "sand": ("tiles", [2, 3], [6, 7], range(4), [(6, 7), (6, 8)], (4, 5), 5, None),
    "snow": ("tiles", [4, 5], [6, 7], range(4), [(7, 5), (6, 6)], (0, 1), 5, None),
    "stone": ("industrial", [0], [2, 3], range(4), [(2, 10), (4, 9)], (2, 3), 10, (175, 180, 195)),
    "lava": ("industrial", [1], [3], range(4), [(2, 10), (4, 0)], (4, 5), 10, (160, 95, 100)),
}

TERRAIN = {}   # tema -> {"top": [surf...], "fill": [surf...], "deco": [surf...]}
BG = {}        # tema -> {"sky": color, "hills": [surf, surf], "fill": surf}
COIN, FLAG, SPIKE = [], [], None
QBLOCK, CHECKPOINT = [], []   # [cheio, usado], [inativo, ativo]
ROCK = GEM = POLE = None
HEART = {}
PLAYER = {}    # "idle" | "walk" | "jump" -> [surf...]
ENEMY = {}     # kind -> [surf...]
_fonts = {}
_flips = {}


def _sheet(name):
    return pygame.image.load(os.path.join(DIR, name + ".png")).convert_alpha()


def _cut(sheet, r, c, ts):
    return pygame.transform.scale(sheet.subsurface((c * ts, r * ts, ts, ts)), (ts * SCALE, ts * SCALE))


def load():
    tiles, ind, chars, bgs = _sheet("tiles"), _sheet("industrial"), _sheet("characters"), _sheet("backgrounds")
    sheets = {"tiles": tiles, "industrial": ind}
    for name, (sh, tops, fills, cols, deco, bgc, _, tint) in THEMES.items():
        s = sheets[sh]
        TERRAIN[name] = {
            "top": [_cut(s, r, c, 18) for r in tops for c in cols],
            "fill": [_cut(s, r, c, 18) for r in fills for c in cols],
            "deco": [_cut(s, r, c, 18) for r, c in deco],
        }
        sky = bgs.get_at((bgc[0] * 24 + 2, 2))
        hills, fill = _cut(bgs, 1, bgc[1], 24), _cut(bgs, 2, bgc[0], 24)
        hills.set_colorkey(sky)
        far, far_fill = _cut(bgs, 1, bgc[0], 24), fill.copy()
        far.set_colorkey(sky)
        far.set_alpha(110)      # camada distante mais clara: profundidade barata
        far_fill.set_alpha(110)
        if tint:
            sky = pygame.Color(*(a * b // 255 for a, b in zip(sky[:3], tint)))
            for surf in (hills, fill, far, far_fill):
                surf.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
            hills.set_colorkey(sky)
            far.set_colorkey(sky)
        BG[name] = {"sky": sky, "hills": hills, "fill": fill, "far": far, "far_fill": far_fill}
    COIN[:] = [_cut(tiles, 7, 11, 18), _cut(tiles, 7, 12, 18)]
    FLAG[:] = [_cut(tiles, 5, 11, 18), _cut(tiles, 5, 12, 18)]
    global SPIKE, POLE
    SPIKE = _cut(tiles, 3, 8, 18)
    POLE = _cut(tiles, 6, 11, 18)
    HEART.update(full=_cut(tiles, 2, 4, 18), empty=_cut(tiles, 2, 6, 18))
    PLAYER.update(idle=[_cut(chars, 0, 0, 24)], walk=[_cut(chars, 0, 0, 24), _cut(chars, 0, 1, 24)],
                  jump=[_cut(chars, 0, 1, 24)])
    ENEMY.update(walker=[_cut(chars, 2, 0, 24), _cut(chars, 2, 1, 24)],
                 hopper=[_cut(chars, 1, 2, 24), _cut(chars, 1, 3, 24)],
                 cannon=[_cut(chars, 1, 6, 24), _cut(chars, 1, 7, 24)],
                 bee=[_cut(chars, 2, 6, 24), _cut(chars, 2, 7, 24)])
    global ROCK, GEM
    ROCK = _cut(tiles, 0, 8, 18)
    GEM = _cut(tiles, 3, 7, 18)
    QBLOCK[:] = [_cut(tiles, 0, 10, 18), _cut(tiles, 1, 10, 18)]
    gray = FLAG[0].copy()
    gray.fill((120, 120, 130), special_flags=pygame.BLEND_RGB_MULT)
    CHECKPOINT[:] = [gray, FLAG[0]]


def font(size, ui=False):
    key = (size, ui)
    if key not in _fonts:
        _fonts[key] = pygame.font.Font(os.path.join(DIR, "font_ui.ttf" if ui else "font.ttf"), size)
    return _fonts[key]


def frame(frames, t, fps=6):
    return frames[int(t * fps) % len(frames)]


def flip(surf):
    if id(surf) not in _flips:
        _flips[id(surf)] = pygame.transform.flip(surf, True, False)
    return _flips[id(surf)]


def pick(seq, seed):
    """Escolha determinística por posição (variação de tile sem cintilar entre frames)."""
    return seq[zlib.crc32(repr(seed).encode()) % len(seq)]
