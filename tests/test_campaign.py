"""Checagem das mecânicas de campanha: escudo, blocos, canhão, abelha, checkpoint, moedas, loja, estrelas."""
import pygame

from handcontrol.config import MAX_LIVES, TILE
from handcontrol.game import Game
from handcontrol.inputs import Input
from handcontrol.run import Run, stars_for
from tests.test_game import mk, run


def test_shield_two_stage():
    r = Run(); r.shield_next = True; r.start_level(0)
    g = Game(mk({(15, 3): "P", (15, 6): "E"}), run=r)
    assert g.player.shield
    for _ in run(g, 120):
        if not g.player.shield:
            break
    assert not g.player.shield and g.state == "playing" and g.player.invuln > 0, "escudo absorve o 1o toque"
    for _ in run(g, 240):
        if g.state != "playing":
            break
    assert g.state == "dead", "2o toque (depois da invencibilidade) mata"


def test_qblock():
    g = Game(mk({(15, 5): "P", (12, 5): "?"}))
    block = g.level.qblocks[0]
    assert block.content == "coin" and block.rect in g.level.solids
    list(run(g, 3))
    for _ in run(g, 60, jump_frames={0}):
        if block.used:
            break
    assert block.used and g.run.coins == 1 and g.collected == 1 and g.coins_total == 1, "cabecada abre o bloco e da moeda"
    before = g.run.coins
    list(run(g, 60, jump_frames={0}))
    assert g.run.coins == before, "bloco usado nao da de novo"


def test_qblock_heart_every_fourth():
    cells = {(15, 3): "P"}
    for c in (6, 8, 10, 12):
        cells[(12, c)] = "?"
    g = Game(mk(cells))
    assert [b.content for b in g.level.qblocks] == ["coin", "coin", "coin", "heart"]


def test_cannon_rock():
    g = Game(mk({(15, 3): "P", (15, 12): "C"}))
    for _ in run(g, 360):
        if g.state != "playing":
            break
    assert g.state == "dead" and g.enemies, "pedra do canhao mata, canhao continua"
    # parede entre os dois: a pedra some na parede
    g = Game(mk({(15, 3): "P", (15, 12): "C", (13, 8): "#", (14, 8): "#", (15, 8): "#"}))
    list(run(g, 300))
    assert g.state == "playing" and not g.rocks, "parede bloqueia a pedra"


def test_cannon_stompable():
    g = Game(mk({(8, 12): "P", (15, 12): "C"}))
    for _ in run(g, 90):
        if not g.enemies:
            break
    assert not g.enemies and g.state == "playing", "canhao morre pisado"


def test_bee_not_stompable():
    g = Game(mk({(8, 5): "P", (13, 5): "B"}))
    bee = g.enemies[0]
    bee.vx = 0
    for _ in run(g, 90):
        if g.state != "playing":
            break
    assert g.state == "dead" and g.enemies, "cair na abelha mata"


def test_checkpoint():
    r = Run(); r.start_level(0)
    g = Game(mk({(15, 3): "P", (15, 10): "K"}), run=r)
    for _ in run(g, 200, move=1):
        if g.checkpoint_active:
            break
    assert g.checkpoint_active and r.checkpoint is not None
    g2 = Game(mk({(15, 3): "P", (15, 10): "K"}), run=r)
    assert g2.player.rect.x == 10 * TILE, "renasce no checkpoint"
    assert g2.checkpoint_active


def test_run_coins_and_lives():
    r = Run()
    assert r.add_coins(19) == 0 and r.lives == 3
    assert r.add_coins(1) == 1 and r.lives == 4, "20 moedas = vida"
    r.add_coins(20); assert r.lives == 5
    assert r.add_coins(20) == 0 and r.lives == MAX_LIVES, "respeita o maximo"
    assert r.coins == 60 and r.coins_total == 60


def test_shop():
    r = Run(); r.add_coins(10)
    assert not r.buy("highjump") and r.coins == 10, "sem saldo nao compra"
    r = Run(); r.add_coins(35)
    assert r.buy("shield") and r.coins == 15 and r.shield_next
    assert not r.buy("shield"), "ja tem"
    assert r.buy("heart") and r.lives == 5 and r.coins == 0   # 35 moedas ja deram 1 vida
    assert not r.buy("heart"), "sem saldo"
    r.start_level(1)
    assert r.shield and not r.shield_next and r.deaths == 0


def test_stars():
    assert stars_for(10, 10, 0) == {"done", "coins", "nodeath"}
    assert stars_for(9, 10, 0) == {"done", "nodeath"}
    assert stars_for(10, 10, 2) == {"done", "coins"}


if __name__ == "__main__":
    from tests.test_game import run_all
    pygame.init()
    run_all(globals())
    print("todos passaram")
