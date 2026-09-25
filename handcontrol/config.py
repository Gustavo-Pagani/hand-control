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
ENEMY_SIZE = {"walker": (36, 28), "hopper": (36, 36)}
LIVES = 3

VALID_CHARS = "#P.EH^oG"
