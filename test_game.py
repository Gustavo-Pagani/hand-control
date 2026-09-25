"""Checagem mínima da lógica: python test_game.py"""
import pygame

from game import TILE, Game, Input, load_level
from levels import LEVELS

DT = 1 / 60


def mk(cells, ground=True):
    """Mapa 17x30: chão na linha 16, bandeira na coluna 27, parede na 29. cells = {(linha, col): char}."""
    g = [["."] * 30 for _ in range(17)]
    if ground:
        g[16] = ["#"] * 30
    for r in (12, 13, 14, 15):
        g[r][29] = "#"
    for r in (13, 14, 15):
        g[r][27] = "G"
    for (r, c), ch in cells.items():
        g[r][c] = ch
    return ["".join(r) for r in g]


def run(game, frames, move=0, jump_frames=()):
    for i in range(frames):
        game.update(Input(move, i in jump_frames), DT)
        yield i


def test_stomp():
    g = Game(mk({(8, 5): "P", (15, 6): "E"}))
    for _ in run(g, 90):
        if not g.enemies:
            break
    assert not g.enemies and g.player.vy < 0 and g.state == "playing", "pisão deve remover inimigo e quicar"


def test_side_contact_kills():
    g = Game(mk({(15, 3): "P", (15, 6): "E"}))
    for _ in run(g, 120):
        if g.state != "playing":
            break
    assert g.state == "dead" and len(g.enemies) == 1, "contato lateral deve matar sem remover inimigo"


def test_head_bump():
    g = Game(mk({(15, 5): "P", (12, 4): "#", (12, 5): "#", (12, 6): "#"}))
    list(run(g, 3))
    bumped = False
    for _ in run(g, 30, jump_frames={0}):
        if g.player.rect.top <= 13 * TILE:
            bumped = g.player.rect.top == 13 * TILE and g.player.vy == 0
            break
    assert bumped, "bater a cabeça deve zerar vy sem atravessar"


def _coyote(delay):
    cells = {(15, 3): "P"}
    g = Game(mk(cells, ground=False))
    g.level.solids.append(pygame.Rect(0, 16 * TILE, 6 * TILE, TILE))
    list(run(g, 3))
    left = None
    for i in run(g, 200, move=1):
        if left is None and not g.player.on_ground:
            left = i
        if left is not None and i == left + delay:
            g.update(Input(1, True), DT)
            return g.player.vy < 0
    raise AssertionError("player nunca saiu da beirada")


def test_coyote():
    assert _coyote(4), "pular 4 frames após sair da beirada deve funcionar"
    assert not _coyote(10), "pular 10 frames após sair da beirada não deve funcionar"


def test_jump_buffer():
    g = Game(mk({(6, 5): "P"}))
    ground_top = 16 * TILE
    pressed = None
    for i in run(g, 120):
        if pressed is None and g.player.rect.bottom >= ground_top - 50:
            g.update(Input(0, True), DT)
            pressed = i
        elif pressed is not None and g.player.vy < 0 and g.player.rect.bottom < ground_top:
            return
    raise AssertionError("jump buffer: pulo comandado antes de tocar o chão deve executar ao tocar")


def test_walker_ledge():
    g = Game(mk({(15, 3): "P", (13, 10): "#", (13, 11): "#", (13, 12): "#", (13, 13): "#", (12, 11): "E"}))
    flips, last = 0, g.enemies[0].vx
    for _ in run(g, 600):
        e = g.enemies[0]
        assert 10 * TILE - 4 <= e.rect.left and e.rect.right <= 14 * TILE + 4, "andante passou da beirada"
        assert e.rect.bottom == 13 * TILE, "andante saiu da altura da plataforma"
        if e.vx != last:
            flips, last = flips + 1, e.vx
    assert flips >= 2, "andante deve inverter nas duas beiradas"


def test_walker_wall():
    g = Game(mk({(15, 25): "P", (15, 10): "E", (13, 5): "#", (14, 5): "#", (15, 5): "#"}))
    for _ in run(g, 300):
        if g.enemies[0].vx > 0:
            break
    assert g.enemies[0].vx > 0 and g.enemies[0].rect.left >= 6 * TILE, "andante deve inverter na parede"


def test_spike_coin_goal():
    g = Game(mk({(15, 3): "P", (15, 6): "^"}))
    for _ in run(g, 120, move=1):
        if g.state != "playing":
            break
    assert g.state == "dead", "espinho deve matar"

    g = Game(mk({(15, 3): "P", (15, 6): "o", (13, 8): "o"}))
    list(run(g, 90, move=1))
    assert g.collected == 1 and len(g.coins) == 1 and g.coins_total == 2, "moeda no caminho deve ser coletada"

    g = Game(mk({(15, 3): "P"}))
    for _ in run(g, 400, move=1):
        if g.state == "won":
            break
    assert g.state == "won", "bandeira deve vencer"


def test_death_flow():
    g = Game(mk({(15, 3): "P", (15, 5): "E"}))
    for _ in run(g, 200):
        if g.state == "dead_done":
            break
    assert g.state == "dead_done", "morte deve terminar em dead_done após DEATH_TIME"


def test_levels_static():
    for name, bg, rows in LEVELS:
        assert len(rows) == 17, name
        assert len({len(r) for r in rows}) == 1 and len(rows[0]) >= 30, name
        assert sum(r.count("P") for r in rows) == 1, name
        assert any("G" in r for r in rows), name
        assert len(bg) == 3, name
        load_level(rows)  # valida caracteres
        gap = 0
        for ch in rows[16]:
            gap = gap + 1 if ch != "#" else 0
            assert gap <= 4, f"{name}: buraco maior que 4 na última linha"


if __name__ == "__main__":
    pygame.init()
    for k, fn in list(globals().items()):
        if k.startswith("test_"):
            fn()
            print("ok", k)
    print("todos passaram")
