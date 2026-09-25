"""Sons sintetizados em código (sem arquivos de áudio). Sem dispositivo de som vira no-op."""
import numpy as np
import pygame

RATE = 22050
_sounds = {}
muted = False
_ok = False


def _wave(freq, dur, kind="square", volume=0.25, slide=0.0):
    n = int(RATE * dur)
    t = np.arange(n) / RATE
    f = freq + slide * t / dur
    phase = 2 * np.pi * np.cumsum(f) / RATE
    if kind == "square":
        w = np.sign(np.sin(phase))
    elif kind == "noise":
        w = np.random.uniform(-1, 1, n)
    else:
        w = np.sin(phase)
    env = np.minimum(1.0, np.linspace(0, 1, n) * 40) * np.linspace(1, 0, n)   # ataque curto, decaimento linear
    return (w * env * volume * 32767).astype(np.int16)


def _build():
    return {
        "coin": np.concatenate([_wave(988, 0.07), _wave(1319, 0.12)]),
        "jump": _wave(300, 0.15, slide=400),
        "stomp": _wave(200, 0.12, slide=-150),
        "hurt": _wave(0, 0.25, kind="noise", volume=0.3),
        "block": _wave(440, 0.08, slide=200),
        "heart": np.concatenate([_wave(660, 0.08), _wave(880, 0.08), _wave(1100, 0.15)]),
        "shield": _wave(500, 0.2, kind="sine", slide=-300, volume=0.35),
        "buy": np.concatenate([_wave(700, 0.06), _wave(1000, 0.1)]),
        "star": np.concatenate([_wave(784, 0.1), _wave(988, 0.1), _wave(1175, 0.1), _wave(1568, 0.25)]),
        "checkpoint": np.concatenate([_wave(600, 0.08, kind="sine"), _wave(900, 0.15, kind="sine")]),
        "die": _wave(400, 0.5, slide=-350, volume=0.3),
    }


def init():
    global _ok
    try:
        pygame.mixer.pre_init(RATE, -16, 1, 512)
        pygame.mixer.init()
        for name, data in _build().items():
            _sounds[name] = pygame.sndarray.make_sound(data)
        _ok = True
    except Exception:  # noqa: BLE001 - sem áudio o jogo segue mudo
        _ok = False


def play(name):
    if _ok and not muted and name in _sounds:
        _sounds[name].play()


def toggle_mute():
    global muted
    muted = not muted
    return muted
