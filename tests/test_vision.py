"""Checagem da visão sem abrir câmera: python -m tests.test_vision"""
from handcontrol.inputs import GestureInput, Input
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
    assert classify(_hand([1, 1, 1, 1], True))[0] == "OPEN"
    assert classify(_hand([1, 1, 1, 1], False))[0] == "OPEN"
    assert classify(_hand([1, 0, 0, 0], False))[0] == "INDEX"
    assert classify(_hand([0, 0, 0, 0], True))[0] == "THUMB"
    assert classify(_hand([0, 0, 0, 0], False))[0] == "FIST"
    assert classify(_hand([1, 1, 0, 0], False))[0] == "NONE", "dois dedos nao e gesto"
    assert classify(_hand([1, 0, 0, 0], True))[0] == "L", "indicador + polegar = L (pulo)"
    assert classify(_hand([1, 1, 0, 0], True))[0] == "NONE"


def test_debounce():
    d = Debouncer(hold=0.2)
    d.update("OPEN", 0.0); d.update("OPEN", 0.25)
    assert d.stable == "OPEN"
    d.update("FIST", 0.30); d.update("INDEX", 0.40); d.update("FIST", 0.45); d.update("FIST", 0.60)
    assert d.stable == "OPEN", "trocas curtas nao podem virar comando"
    d.update("FIST", 0.66)
    assert d.stable == "FIST"


def test_gesture_edge():
    gi = GestureInput()
    jumps = [gi.read(s).jump for s in ("FIST", "L", "L", "FIST", "L", "NONE", "L", "OPEN")]
    assert jumps == [False, True, False, False, True, False, True, False]
    assert gi.read("INDEX").move == 1 and gi.read("THUMB").move == -1 and gi.read("OPEN").move == 0
    gi.read("INDEX")
    assert gi.read("L") == Input(1, True), "L vindo do indicador mantem a direcao e pula"
    assert gi.read("L") == Input(1, False), "segurar o L nao pula de novo"
    assert gi.read("FIST") == Input(0, False)
    assert gi.read("L") == Input(0, True), "L vindo do punho pula parado"




if __name__ == "__main__":
    from tests.test_game import run_all
    run_all(globals())
    print("todos passaram")
