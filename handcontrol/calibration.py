"""Tela de calibração: pede os 4 gestos, mede as métricas e ajusta os limiares do classificador."""
import statistics

import pygame

from .camview import draw_camera
from .config import DT
from .ui import DIM, GREEN, RED, SHADOW, WHITE, YELLOW, dim, draw_panel, draw_text
from .vision import FINGER_NAMES, save_calibration

STEPS = [("FIST", "PUNHO", "feche a mao (parado)"),
         ("OPEN", "MAO ABERTA", "abra a mao, dedos separados (parado)"),
         ("INDEX", "INDICADOR", "so o indicador levantado (frente)"),
         ("THUMB", "POLEGAR", "so o polegar levantado, joinha (tras)"),
         ("L", "POLEGAR + INDICADOR", "os dois levantados, mao em L (pulo)")]
HOLD = 1.0  # s segurando o gesto certo para o passo contar


class Calibration:
    def __init__(self, tracker, background_game):
        self.tracker = tracker
        self.bg_game = background_game
        self.reset()

    def reset(self):
        self.step = 0
        self.hold = 0.0
        self.samples = {g: [] for g, *_ in STEPS}
        self.results = {}
        self.done = False
        self.msg = ""
        self.thresh = None
        self.t = 0.0

    @property
    def finished(self):
        return self.done

    def update(self, keys):
        """keys: teclas KEYDOWN deste frame. Retorna 'menu' quando o usuário quer sair."""
        self.t += DT
        tr = self.tracker
        if pygame.K_r in keys:
            self.reset()
            return None
        if self.done:
            return "menu" if pygame.K_SPACE in keys else None
        if tr.error or not tr.ready:
            return None
        target = STEPS[self.step][0]
        if pygame.K_SPACE in keys:  # pula o passo
            self.results[target] = False
            self.samples[target] = []
            self._advance()
        elif tr.stable == target and tr.landmarks:
            self.hold += DT
            self.samples[target].append(tr.metrics)
            if self.hold >= HOLD:
                self.results[target] = True
                self._advance()
        else:
            self.hold = max(0.0, self.hold - 2 * DT)
        return None

    def _advance(self):
        self.step += 1
        self.hold = 0.0
        if self.step < len(STEPS):
            return
        self.done = True
        self.thresh = self._compute_thresholds()
        save_calibration(self.thresh)
        self.tracker.thresh = self.thresh   # o próximo frame já classifica com os limiares novos

    def _compute_thresholds(self):
        """Limiar = meio do caminho entre o gesto que abre o dedo e o que fecha. Sem amostras: mantém."""
        thresh = dict(self.tracker.thresh)
        msgs = []
        s = self.samples
        if s["OPEN"] and s["FIST"]:
            open_low = statistics.median(min(m[1:]) for m in s["OPEN"])   # dedo menos aberto na mão aberta
            fist_high = statistics.median(max(m[1:]) for m in s["FIST"])  # dedo mais aberto no punho
            if open_low > fist_high:
                thresh["fingers"] = round((open_low + fist_high) / 2, 3)
            else:
                msgs.append("dedos: mao aberta e punho parecidos demais, limiar mantido")
        closed = s["FIST"] + s["INDEX"]
        if s["THUMB"] and closed:
            thumb_open = statistics.median(m[0] for m in s["THUMB"])
            thumb_closed = statistics.median(m[0] for m in closed)
            if thumb_open > thumb_closed:
                thresh["thumb"] = round((thumb_open + thumb_closed) / 2, 3)
            else:
                msgs.append("polegar: joinha e punho parecidos demais, limiar mantido")
        self.msg = "  ".join(msgs)
        return thresh

    def draw(self, screen):
        tr = self.tracker
        self.bg_game.draw_background(screen, self.t * 20)
        dim(screen, 120)
        draw_text(screen, "CALIBRAR CAMERA", 56, WHITE, (40, 30), align="topleft")
        draw_camera(screen, tr, 40, 90, big=True)
        draw_text(screen, f"{tr.fps:.0f} fps   {tr.latency_ms:.0f} ms de atraso   gesto cru: {tr.gesture}",
                  22, DIM, (40, 462), align="topleft")
        px, py = 560, 90
        draw_panel(screen, pygame.Rect(px, py, 480, 470))
        for i, (g, name, _) in enumerate(STEPS):
            if g in self.results:
                mark, color = ("OK", GREEN) if self.results[g] else ("X", RED)
            elif i == self.step and not self.done:
                mark, color = ">", YELLOW
            else:
                mark, color = "-", DIM
            draw_text(screen, f"{mark}  {i + 1}. {name}", 30, color, (px + 24, py + 20 + i * 36), align="topleft")
        if self.done:
            ok = sum(self.results.values())
            n = len(STEPS)
            draw_text(screen, "Calibrado!" if ok == n else "Concluido", 44, GREEN if ok == n else YELLOW,
                      (px + 240, py + 200))
            draw_text(screen, f"{ok}/{n} gestos reconhecidos", 30, WHITE, (px + 240, py + 240))
            th = self.thresh or tr.thresh
            draw_text(screen, f"limiar dedos {th['fingers']:.2f}   polegar {th['thumb']:.2f}", 24, DIM,
                      (px + 240, py + 275))
            if self.msg:
                draw_text(screen, self.msg, 18, YELLOW, (px + 240, py + 305))
            draw_text(screen, "ESPACO volta ao menu   R refaz", 26, DIM, (px + 240, py + 430))
            return
        _, name, hint = STEPS[self.step]
        draw_text(screen, f"Mostre: {name}", 40, YELLOW, (px + 240, py + 200))
        draw_text(screen, hint, 24, WHITE, (px + 240, py + 236))
        bar = pygame.Rect(px + 60, py + 262, 360, 22)
        pygame.draw.rect(screen, SHADOW, bar)
        pygame.draw.rect(screen, GREEN, (bar.x, bar.y, int(bar.w * min(self.hold / HOLD, 1)), bar.h))
        pygame.draw.rect(screen, DIM, bar, 2)
        draw_text(screen, "segure o gesto", 20, DIM, (px + 240, py + 300))
        for i, (fname, ext, m) in enumerate(zip(FINGER_NAMES, tr.fingers, tr.metrics)):
            cx = px + 60 + i * 90
            pygame.draw.circle(screen, GREEN if ext else (70, 70, 85), (cx, py + 350), 14)
            pygame.draw.circle(screen, DIM, (cx, py + 350), 14, 2)
            draw_text(screen, fname, 18, DIM, (cx, py + 378))
            draw_text(screen, f"{m:.2f}", 18, DIM, (cx, py + 396))
        draw_text(screen, "ESPACO pula o passo   ESC volta   R refaz", 22, DIM, (px + 240, py + 440))
