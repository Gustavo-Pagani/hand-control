"""Constantes de janela, física e regras. Um lugar só para ajustar a sensação do jogo."""
TILE = 36                    # 18 px do Kenney x 2
WIDTH, HEIGHT = 1080, 612    # 30 x 17 tiles
FPS = 60
DT = 1 / FPS                 # passo fixo; nunca usar o retorno de clock.tick() (thread da webcam disputa CPU)

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
ENEMY_SIZE = {"walker": (36, 28), "hopper": (36, 36), "cannon": (36, 36), "bee": (32, 24)}
STOMPABLE = {"walker", "hopper", "cannon"}

# campanha
LIVES = 3
MAX_LIVES = 5
COINS_PER_LIFE = 20
SHIELD_INVULN = 1.0   # s piscando depois de o escudo absorver um toque
HIGH_JUMP = 1.15      # multiplicador do pulo comprado na loja
SHOP = [("heart", "Coracao", 15, "+1 vida (max 5)"),
        ("shield", "Escudo", 20, "absorve um toque na proxima fase"),
        ("highjump", "Pulo alto", 25, "pulo 15% maior na proxima fase")]
STARS = (("done", "completa"), ("coins", "todas as moedas"), ("nodeath", "sem morrer"))

# inimigos novos
CANNON_RANGE = 10 * TILE
CANNON_INTERVAL = 2.0
ROCK_SPEED = 200
BEE_SPEED = 70
BEE_RANGE = 4 * TILE
BEE_AMPL = TILE
HEART_EVERY = 4   # a cada N blocos '?' de uma fase, um solta coracao

VALID_CHARS = "#P.EH^oGCB?K"
