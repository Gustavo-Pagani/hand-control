"""Partículas e tremor de tela. Puro estado; o Game chama burst/shake e desenha."""
import random

import pygame

from .config import GRAVITY


class Effects:
    def __init__(self):
        self.particles = []   # [x, y, vx, vy, vida restante, cor, tamanho]
        self.shake = 0.0

    def burst(self, pos, color, n=8, speed=220):
        for _ in range(n):
            vx = random.uniform(-speed, speed)
            vy = random.uniform(-speed * 1.4, -speed * 0.2)
            self.particles.append([pos[0], pos[1], vx, vy, random.uniform(0.3, 0.6), color, random.randint(3, 6)])

    def shake_screen(self, amount):
        self.shake = max(self.shake, amount)

    def update(self, dt):
        self.shake = max(0.0, self.shake - dt * 30)
        alive = []
        for p in self.particles:
            p[4] -= dt
            if p[4] > 0:
                p[3] += GRAVITY * 0.5 * dt
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                alive.append(p)
        self.particles = alive

    def offset(self):
        if self.shake <= 0:
            return 0, 0
        return random.randint(-int(self.shake), int(self.shake)), random.randint(-int(self.shake), int(self.shake))

    def draw(self, surface, cx):
        for x, y, _, _, life, color, size in self.particles:
            s = max(1, int(size * min(1.0, life * 3)))
            pygame.draw.rect(surface, color, (int(x - cx), int(y), s, s))
