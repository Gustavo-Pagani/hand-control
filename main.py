import pygame

from game import HEIGHT, WIDTH, Game, Input

FPS = 60
DT = 1 / FPS  # passo fixo; nunca usar o retorno de clock.tick() (thread da webcam vai disputar CPU)


def read_keyboard(events) -> Input:
    keys = pygame.key.get_pressed()
    move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
    jump = any(e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE for e in events)
    return Input(move, jump)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hand Control")
    clock = pygame.time.Clock()
    game = Game()
    while True:
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                return
        game.update(read_keyboard(events), DT)
        game.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
