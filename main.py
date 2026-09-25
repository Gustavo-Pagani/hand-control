import random
import statistics
import sys

import pygame

import assets
import vision
from game import HEIGHT, TILE, WIDTH, Game, Input, move_body
from levels import LEVELS

FPS = 60
DT = 1 / FPS  # passo fixo; nunca usar o retorno de clock.tick() (thread da webcam disputa CPU)
LIVES = 3
WHITE = (250, 250, 250)
DIM = (200, 200, 210)
YELLOW = (255, 215, 80)
RED = (235, 80, 80)
GREEN = (110, 220, 120)
BLUE = (110, 170, 255)
PANEL = (28, 26, 40)
SHADOW = (30, 30, 45)
GESTURE_COLOR = {"OPEN": DIM, "INDEX": GREEN, "THUMB": BLUE, "FIST": YELLOW, "NONE": RED}
GESTURE_LABEL = {"OPEN": "MAO ABERTA = parado", "INDEX": "INDICADOR = frente", "THUMB": "POLEGAR = tras",
                 "FIST": "PUNHO = pulo", "NONE": "sem mao"}
CAL_STEPS = [("OPEN", "MAO ABERTA", "abra a mao, dedos separados"),
             ("FIST", "PUNHO", "feche a mao"),
             ("INDEX", "INDICADOR", "so o indicador levantado"),
             ("THUMB", "POLEGAR", "so o polegar levantado (joinha)")]
CAL_HOLD = 1.0  # s segurando o gesto certo para o passo contar


def draw_text(surface, txt, size, color, center, shadow=True, align="center"):
    f = assets.font(size)
    img = f.render(txt, False, color)
    rect = img.get_rect(**{align: center})
    if shadow:
        sh = f.render(txt, False, SHADOW)
        surface.blit(sh, rect.move(3, 3))
    surface.blit(img, rect)


def fmt_time(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def read_keyboard(events) -> Input:
    keys = pygame.key.get_pressed()
    move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
    jump = any(e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_w) for e in events)
    return Input(move, jump)


class GestureInput:
    """Gesto estável -> Input. Pulo só na borda de subida do punho: um pulo por punho fechado."""

    def __init__(self):
        self.prev = "NONE"

    def read(self, stable: str) -> Input:
        jump = stable == "FIST" and self.prev != "FIST"
        self.prev = stable
        return Input({"INDEX": 1, "THUMB": -1}.get(stable, 0), jump)


class Bouncer:
    """Personagem decorativo do menu; reaproveita move_body com um chão fake."""

    def __init__(self, frames):
        self.frames = frames
        self.rect = pygame.Rect(random.randint(40, WIDTH - 80), random.randint(100, 300), 36, 36)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.vx, self.vy = random.choice([-120, 120]), 0.0
        self.on_ground = self.hit_wall = False


class App:
    def __init__(self, start_level=None, tracker=None):
        self.scene = "menu"
        self.level_idx = 0
        self.lives = LIVES
        self.game = None
        self.total_time = self.total_coins = self.total_coins_max = 0
        self.t = 0.0
        self.show_cam = True
        self.tracker = tracker or vision.HandTracker()
        if not self.tracker.is_alive() and not self.tracker.error:
            self.tracker.start()
        self.gestures = GestureInput()
        self.cal = None
        self.menu_game = Game(LEVELS[0][2], LEVELS[0][1])  # só para o fundo e o chão do menu
        self.bouncers = [Bouncer(assets.PLAYER["walk"])] + [
            Bouncer(assets.ENEMY[k]) for k in ("walker", "hopper", "walker", "hopper")]
        self.menu_floor = [pygame.Rect(0, HEIGHT - TILE, WIDTH, TILE),
                           pygame.Rect(-10, 0, 10, HEIGHT), pygame.Rect(WIDTH, 0, 10, HEIGHT)]
        if start_level is not None:
            self.start(start_level)

    def start(self, idx):
        self.level_idx, self.lives = idx, LIVES
        self.total_time = self.total_coins = self.total_coins_max = 0
        self.new_attempt()

    def new_attempt(self):
        name, theme, rows = LEVELS[self.level_idx]
        self.game = Game(rows, theme)
        self.scene = "play"

    def read_input(self, events) -> Input:
        kb = read_keyboard(events)
        tr = self.tracker
        g = self.gestures.read(tr.stable if tr.ready and not tr.error else "NONE")
        return Input(kb.move or g.move, kb.jump or g.jump)

    def update(self, inp, events):
        self.t += DT
        keys = [e.key for e in events if e.type == pygame.KEYDOWN]
        if pygame.K_v in keys:
            self.show_cam = not self.show_cam
        if self.scene == "menu":
            for b in self.bouncers:
                move_body(b, DT, self.menu_floor)
                if b.hit_wall:
                    b.vx = -b.vx
                if b.on_ground:
                    b.vy = -random.randint(350, 700)
            if pygame.K_c in keys:
                self.start_calibration()
            elif inp.jump:
                self.start(0)
            for k in keys:
                if pygame.K_1 <= k <= pygame.K_5:
                    self.start(k - pygame.K_1)
        elif self.scene == "calibrate":
            self.update_calibration(keys)
        elif self.scene == "play":
            g = self.game
            if pygame.K_r in keys:
                self.new_attempt()
                return
            g.update(inp, DT)
            if g.state == "dead_done":
                self.lives -= 1
                if self.lives > 0:
                    self.new_attempt()
                else:
                    self.scene = "game_over"
            elif g.state == "won":
                self.total_time += g.elapsed
                self.total_coins += g.collected
                self.total_coins_max += g.coins_total
                self.scene = "level_done"
        elif self.scene == "level_done":
            if inp.jump:
                if self.level_idx + 1 < len(LEVELS):
                    self.level_idx += 1
                    self.lives = LIVES
                    self.new_attempt()
                else:
                    self.scene = "victory"
        elif inp.jump:  # game_over / victory
            self.scene = "menu"

    # ---------------- calibração ----------------
    def start_calibration(self):
        self.cal = {"step": 0, "hold": 0.0, "samples": {g for g, *_ in CAL_STEPS} and {g: [] for g, *_ in CAL_STEPS},
                    "results": {}, "done": False, "msg": "", "thresh": None}
        self.scene = "calibrate"

    def update_calibration(self, keys):
        cal, tr = self.cal, self.tracker
        if pygame.K_r in keys:
            self.start_calibration()
            return
        if cal["done"]:
            if pygame.K_SPACE in keys:
                self.scene = "menu"
            return
        if tr.error or not tr.ready:
            return
        target = CAL_STEPS[cal["step"]][0]
        if pygame.K_SPACE in keys:  # pula o passo
            cal["results"][target] = False
            cal["samples"][target] = []
            self.advance_calibration()
            return
        if tr.stable == target and tr.landmarks:
            cal["hold"] += DT
            cal["samples"][target].append(tr.metrics)
            if cal["hold"] >= CAL_HOLD:
                cal["results"][target] = True
                self.advance_calibration()
        else:
            cal["hold"] = max(0.0, cal["hold"] - 2 * DT)

    def advance_calibration(self):
        cal = self.cal
        cal["step"] += 1
        cal["hold"] = 0.0
        if cal["step"] < len(CAL_STEPS):
            return
        cal["done"] = True
        cal["thresh"] = self.compute_thresholds(cal["samples"])
        if cal["thresh"]:
            vision.save_calibration(cal["thresh"])
            self.tracker.thresh = cal["thresh"]
            # recalibrar não muda gestos já estáveis, mas o próximo frame já usa os limiares novos

    def compute_thresholds(self, samples):
        """Limiar = meio do caminho entre o gesto que abre o dedo e o que fecha. Sem amostras: mantém."""
        thresh = dict(self.tracker.thresh)
        msgs = []
        s_open, s_fist, s_index, s_thumb = (samples[g] for g in ("OPEN", "FIST", "INDEX", "THUMB"))
        if s_open and s_fist:
            open_low = statistics.median(min(m[1:]) for m in s_open)   # dedo menos aberto na mão aberta
            fist_high = statistics.median(max(m[1:]) for m in s_fist)  # dedo mais aberto no punho
            if open_low > fist_high:
                thresh["fingers"] = round((open_low + fist_high) / 2, 3)
            else:
                msgs.append("dedos: mao aberta e punho parecidos demais, limiar mantido")
        closed = s_fist + s_index
        if s_thumb and closed:
            thumb_open = statistics.median(m[0] for m in s_thumb)
            thumb_closed = statistics.median(m[0] for m in closed)
            if thumb_open > thumb_closed:
                thresh["thumb"] = round((thumb_open + thumb_closed) / 2, 3)
            else:
                msgs.append("polegar: joinha e punho parecidos demais, limiar mantido")
        self.cal["msg"] = "  ".join(msgs)
        return thresh

    # ---------------- desenho ----------------
    def draw_camera(self, screen, x, y, big=False):
        tr = self.tracker
        data = tr.preview_big if big else tr.preview
        if tr.error or not data:
            w, h = (480, 360) if big else (200, 150)
            pygame.draw.rect(screen, PANEL, (x, y, w, h))
            pygame.draw.rect(screen, RED if tr.error else DIM, (x, y, w, h), 3)
            draw_text(screen, tr.error or f"camera: {tr.status}...", 22 if big else 18,
                      RED if tr.error else DIM, (x + w // 2, y + h // 2))
            return
        raw, (w, h) = data
        screen.blit(pygame.image.frombuffer(raw, (w, h), "RGB"), (x, y))
        if tr.landmarks:
            pts = [(x + int(px * w), y + int(py * h)) for px, py in tr.landmarks]
            for a, b in vision.CONNECTIONS:
                pygame.draw.line(screen, WHITE, pts[a], pts[b], 2)
            for p in pts:
                pygame.draw.circle(screen, GREEN, p, 4 if big else 3)
        color = GESTURE_COLOR[tr.stable]
        pygame.draw.rect(screen, color, (x, y, w, h), 3)
        label = GESTURE_LABEL[tr.stable] if big else tr.stable
        draw_text(screen, label, 30 if big else 24, color, (x + w // 2, y + h - (22 if big else 14)))
        if tr.hands > 1:
            draw_text(screen, "2 MAOS!", 26, RED, (x + w // 2, y + 20))

    def draw_calibration(self, screen):
        cal, tr = self.cal, self.tracker
        self.menu_game.draw_background(screen, self.t * 20)
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        screen.blit(dim, (0, 0))
        draw_text(screen, "CALIBRAR CAMERA", 56, WHITE, (40, 30), align="topleft")
        self.draw_camera(screen, 40, 90, big=True)
        draw_text(screen, f"{tr.fps:.0f} fps   gesto cru: {tr.gesture}", 22, DIM, (40, 462), align="topleft")
        px, py = 560, 90
        pygame.draw.rect(screen, PANEL, (px, py, 480, 470), border_radius=8)
        pygame.draw.rect(screen, YELLOW, (px, py, 480, 470), 3, border_radius=8)
        for i, (g, name, _) in enumerate(CAL_STEPS):
            if g in cal["results"]:
                mark, color = ("OK", GREEN) if cal["results"][g] else ("X", RED)
            elif i == cal["step"] and not cal["done"]:
                mark, color = ">", YELLOW
            else:
                mark, color = "-", DIM
            draw_text(screen, f"{mark}  {i + 1}. {name}", 30, color, (px + 24, py + 20 + i * 36), align="topleft")
        if cal["done"]:
            ok = sum(cal["results"].values())
            draw_text(screen, "Calibrado!" if ok == 4 else "Concluido", 44, GREEN if ok == 4 else YELLOW,
                      (px + 240, py + 200))
            draw_text(screen, f"{ok}/4 gestos reconhecidos", 30, WHITE, (px + 240, py + 240))
            th = cal["thresh"] or tr.thresh
            draw_text(screen, f"limiar dedos {th['fingers']:.2f}   polegar {th['thumb']:.2f}", 24, DIM, (px + 240, py + 275))
            if cal["msg"]:
                draw_text(screen, cal["msg"], 18, YELLOW, (px + 240, py + 305))
            draw_text(screen, "ESPACO volta ao menu   R refaz", 26, DIM, (px + 240, py + 430))
            return
        g, name, hint = CAL_STEPS[cal["step"]]
        draw_text(screen, f"Mostre: {name}", 40, YELLOW, (px + 240, py + 200))
        draw_text(screen, hint, 24, WHITE, (px + 240, py + 236))
        bar = pygame.Rect(px + 60, py + 262, 360, 22)
        pygame.draw.rect(screen, SHADOW, bar)
        pygame.draw.rect(screen, GREEN, (bar.x, bar.y, int(bar.w * min(cal["hold"] / CAL_HOLD, 1)), bar.h))
        pygame.draw.rect(screen, DIM, bar, 2)
        draw_text(screen, "segure o gesto", 20, DIM, (px + 240, py + 300))
        for i, (fname, ext, m) in enumerate(zip(vision.FINGER_NAMES, tr.fingers, tr.metrics)):
            cx = px + 60 + i * 90
            pygame.draw.circle(screen, GREEN if ext else (70, 70, 85), (cx, py + 350), 14)
            pygame.draw.circle(screen, DIM, (cx, py + 350), 14, 2)
            draw_text(screen, fname, 18, DIM, (cx, py + 378))
            draw_text(screen, f"{m:.2f}", 18, DIM, (cx, py + 396))
        draw_text(screen, "ESPACO pula o passo   ESC volta   R refaz", 22, DIM, (px + 240, py + 440))

    def draw(self, screen):
        cx, cy = WIDTH // 2, HEIGHT // 2
        blink = int(self.t * 2) % 2 == 0
        tr = self.tracker
        if self.scene == "calibrate":
            self.draw_calibration(screen)
            return
        if self.scene == "menu":
            self.menu_game.draw_background(screen, self.t * 40)
            top = assets.TERRAIN["grass"]["top"]
            for i, x in enumerate(range(0, WIDTH, TILE)):
                screen.blit(assets.pick(top, i), (x, HEIGHT - TILE))
            for b in self.bouncers:
                img = assets.frame(b.frames, self.t, 4)
                if b.vx > 0:
                    img = assets.flip(img)
                screen.blit(img, img.get_rect(midbottom=b.rect.midbottom))
            band = pygame.Surface((WIDTH, 210), pygame.SRCALPHA)
            band.fill((0, 0, 0, 90))
            screen.blit(band, (0, 258))
            draw_text(screen, "HAND CONTROL", 120, WHITE, (cx, 140))
            draw_text(screen, "um platformer controlado pela sua mao", 36, DIM, (cx, 205))
            if blink:
                draw_text(screen, "ESPACO ou PUNHO para jogar", 48, YELLOW, (cx, 290))
            draw_text(screen, "C  calibrar camera", 40, GREEN, (cx, 345))
            draw_text(screen, "1-5 escolhe a fase   A/D anda   ESPACO pula   V mostra/esconde camera   ESC sai",
                      26, DIM, (cx, 395))
            if tr.error:
                status, color = f"camera: {tr.error}", RED
            elif not tr.ready:
                status, color = f"camera: {tr.status}...", YELLOW
            else:
                status, color = f"camera ok  {tr.fps:.0f} fps   gesto: {tr.stable}", GREEN
            draw_text(screen, status, 26, color, (cx, 440))
            if self.show_cam and not tr.error:
                self.draw_camera(screen, WIDTH - 220, HEIGHT - TILE - 170)
            return

        self.game.draw(screen)
        name = LEVELS[self.level_idx][0]
        g = self.game
        if self.scene == "play":
            draw_text(screen, f"Fase {self.level_idx + 1}  {name}", 34, WHITE, (170, 24))
            for i in range(LIVES):
                screen.blit(assets.HEART["full" if i < self.lives else "empty"], (WIDTH - 50 - i * 40, 8))
            screen.blit(assets.COIN[0], (cx - 70, 6))
            draw_text(screen, f"{g.collected}/{g.coins_total}", 34, YELLOW, (cx + 10, 24))
            draw_text(screen, fmt_time(g.elapsed), 34, WHITE, (WIDTH - 260, 24))
            if self.show_cam and not tr.error:
                self.draw_camera(screen, WIDTH - 210, 48)
            return

        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))
        panel = pygame.Rect(0, 0, 600, 320)
        panel.center = (cx, cy)
        pygame.draw.rect(screen, PANEL, panel, border_radius=8)
        pygame.draw.rect(screen, YELLOW, panel, 4, border_radius=8)
        if self.scene == "level_done":
            draw_text(screen, f"Fase {self.level_idx + 1} completa!", 64, YELLOW, (cx, cy - 100))
            draw_text(screen, name, 40, WHITE, (cx, cy - 50))
            draw_text(screen, f"tempo  {fmt_time(g.elapsed)}", 38, WHITE, (cx, cy + 5))
            screen.blit(assets.COIN[0], (cx - 80, cy + 27))
            draw_text(screen, f"{g.collected}/{g.coins_total}", 38, YELLOW, (cx + 10, cy + 45))
            hint = "ESPACO ou PUNHO para continuar"
        elif self.scene == "game_over":
            draw_text(screen, "GAME OVER", 80, RED, (cx, cy - 80))
            draw_text(screen, f"Voce chegou ate a fase {self.level_idx + 1}", 38, WHITE, (cx, cy))
            hint = "ESPACO ou PUNHO para o menu"
        else:
            draw_text(screen, "VOCE ZEROU!", 80, YELLOW, (cx, cy - 90))
            draw_text(screen, f"tempo total  {fmt_time(self.total_time)}", 38, WHITE, (cx, cy - 15))
            screen.blit(assets.COIN[0], (cx - 80, cy + 7))
            draw_text(screen, f"{self.total_coins}/{self.total_coins_max}", 38, YELLOW, (cx + 10, cy + 25))
            hint = "ESPACO ou PUNHO para o menu"
        if blink:
            draw_text(screen, hint, 32, DIM, (cx, cy + 120))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hand Control")
    assets.load()
    clock = pygame.time.Clock()
    start = int(sys.argv[1]) - 1 if len(sys.argv) > 1 else None
    app = App(start)
    while True:
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE
                                          and app.scene == "menu"):
                app.tracker.stop()
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                app.scene = "menu"
        app.update(app.read_input(events), events)
        app.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
