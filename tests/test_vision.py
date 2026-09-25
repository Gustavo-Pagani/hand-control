"""Checagem da visão sem abrir câmera: python -m tests.test_vision"""
from handcontrol.inputs import GestureInput, Hold, Input
from handcontrol.vision import Debouncer, classify


def _hand(open_fingers, thumb_open):
    """Mão sintética: pulso na origem, dedos apontando para cima; aberto = ponta longe, fechado = ponta dobrada."""
    lm = [(0.0, 0.0)] * 21
    lm[9] = (0.0, -1.0)     # MCP do médio: tamanho da palma = 1
    lm[17] = (0.4, -0.9)    # MCP do mínimo
    for i, (pip, tip) in enumerate(zip((6, 10, 14, 18), (8, 12, 16, 20))):
        x = -0.3 + i * 0.25
        lm[pip] = (x, -1.4)
        lm[tip] = (x, -2.2) if open_fingers[i] else (x, -1.2)
    lm[3] = (0.5, -0.5)
    lm[4] = (1.6, -0.4) if thumb_open else (0.5, -0.7)
    return lm


def test_classify():
    assert classify(_hand([1, 1, 1, 1], True))[0] == "FIVE"
    assert classify(_hand([1, 1, 1, 1], False))[0] == "OPEN"
    assert classify(_hand([1, 0, 0, 0], False))[0] == "INDEX"
    assert classify(_hand([1, 0, 0, 0], True))[0] == "INDEX", "polegar nao atrapalha o indicador"
    assert classify(_hand([0, 0, 0, 0], True))[0] == "THUMB"
    assert classify(_hand([0, 0, 0, 0], False))[0] == "FIST"
    assert classify(_hand([1, 1, 0, 0], False))[0] == "TWO"
    assert classify(_hand([1, 1, 1, 0], True))[0] == "THREE", "polegar nao atrapalha o tres"
    assert classify(_hand([1, 0, 1, 1], False))[0] == "NONE", "combinacao sem sentido"


def test_debounce():
    d = Debouncer(hold=0.2)
    d.update("OPEN", 0.0); d.update("OPEN", 0.25)
    assert d.stable == "OPEN"
    d.update("FIST", 0.30); d.update("INDEX", 0.40); d.update("FIST", 0.45); d.update("FIST", 0.60)
    assert d.stable == "OPEN", "trocas curtas nao podem virar comando"
    d.update("FIST", 0.66)
    assert d.stable == "FIST"


def test_gesture_two_hands():
    gi = GestureInput()
    seq = [("FIST", "FIST"), ("INDEX", "INDEX"), ("INDEX", "INDEX"), ("THUMB", "FIST"), ("NONE", "INDEX"),
           ("FIST", "NONE"), ("INDEX", "INDEX")]
    out = [gi.read({"L": l, "R": r}) for l, r in seq]
    one = {"select": 1}   # indicador direito tambem conta como "item 1" nos menus
    assert out == [Input(0, False), Input(1, True, **one), Input(1, False, **one), Input(-1, False),
                   Input(0, True, **one), Input(0, False), Input(1, True, **one)]
    assert gi.read({}) == Input(0, False), "sem tracker: nada"


def test_hold_confirm_and_back():
    gi = GestureInput(confirm_seconds=0.5, back_seconds=0.5)
    both = {"L": "FIST", "R": "FIST"}
    fired = [gi.read(both, 0.1).confirm for _ in range(8)]
    assert fired == [False] * 4 + [True] + [False] * 3, "confirma uma vez ao completar 0,5 s e nao repete"
    assert gi.read({"L": "FIST", "R": "OPEN"}, 0.1).confirm is False
    assert gi.confirm.progress == 0, "soltar zera"
    back = [gi.read({"L": "THREE"}, 0.1).back for _ in range(6)]
    assert back == [False] * 4 + [True, False]


def test_select_by_fingers():
    from handcontrol.shop import Cursor
    gi = GestureInput()
    assert [gi.read({"R": g}).select for g in ("INDEX", "TWO", "THREE", "OPEN", "FIVE", "FIST", "NONE")] == [1, 2, 3, 4, 5, 0, 0]
    c = Cursor(4)
    c.update(Input(select=3)); assert c.idx == 2
    c.update(Input(select=0)); assert c.idx == 2, "sem gesto mantem"
    c.update(Input(select=5)); assert c.idx == 3, "5 dedos num menu de 4 cai no ultimo"
    h = Hold(1.0)
    assert not h.update(True, 0.6) and 0.5 < h.progress < 0.7
    assert h.update(True, 0.5) and h.progress == 0


if __name__ == "__main__":
    from tests.test_game import run_all
    run_all(globals())
    print("todos passaram")
