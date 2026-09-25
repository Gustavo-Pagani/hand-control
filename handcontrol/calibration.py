"""Tela de calibração: pede cada comando de cada mão, mede as métricas e ajusta os limiares."""
import statistics

import pygame

from .camview import draw_camera
from .config import DT
from .inputs import Hold
from .ui import DIM, GREEN, RED, SHADOW, WHITE, YELLOW, dim, draw_panel, draw_text
from .vision import FINGER_NAMES, save_calibration

# (lado, gesto, nome curto, instrução)
STEPS = [("L", "FIST", "ESQUERDA: PUNHO", "mao esquerda fechada (parado)"),
         ("L", "INDEX", "ESQUERDA: INDICADOR", "mao esquerda, so o indicador (frente / proximo)"),
         ("L", "THUMB", "ESQUERDA: POLEGAR", "mao esquerda, so o polegar, joinha (tras / anterior)"),
         ("L", "THREE", "ESQUERDA: TRES DEDOS", "indicador, medio e anelar (pular passo)"),
         ("R", "FIST", "DIREITA: PUNHO", "mao direita fechada (parado)"),
         ("R", "INDEX", "DIREITA: INDICADOR", "mao direita, so o indicador (pulo)"),
         ("R", "THREE", "DIREITA: TRES DEDOS", "indicador, medio e anelar (voltar / sair)"),
         ("B", "OPEN", "DUAS MAOS ABERTAS", "as duas maos abertas (confirmar)")]
HOLD = 1.0  # s segurando o gesto certo para o passo contar
SIDE_NAME = {"L": "esquerda", "R": "direita", "B": "duas maos"}


class Calibration:
    def __init__(self, tracker, background_game):
        self.tracker = tracker
        self.bg_game = background_game
        self.reset()

    def reset(self):
        self.step = 0
        self.hold = 0.0
        self.samples = {g: [] for _, g, *_ in STEPS}   # por gesto, as duas mãos juntas
        self.results = {}                               # (lado, gesto) -> bool
        self.done = False
        self.msg = ""
        self.thresh = None
        self.t = 0.0
        self.skip = Hold(1.5)   # tres dedos na esquerda seguradas pulam o passo

    def _matches(self, side, target):
        st, lm = self.tracker.stable, self.tracker.landmarks
        if side == "B":
            return st["L"] == target and st["R"] == target and "L" in lm and "R" in lm
        return st[side] == target and side in lm

    def update(self, inp):
        """Retorna 'menu' quando o usuário quer sair (confirmar na tela final, ou voltar)."""
        self.t += DT
        tr = self.tracker
        if self.done:
            return "menu" if inp.confirm or inp.back else None
        if inp.back:
            return "menu"
        if tr.error or not tr.ready:
            return None
        side, target, *_ = STEPS[self.step]
        if self.skip.update(tr.stable["L"] == "THREE" and target != "THREE", DT):
            self.results[(side, target)] = False
            self._advance()
        elif self._matches(side, target):
            self.hold += DT
            if side != "B":
                self.samples[target].append(tr.metrics[side])
            if self.hold >= HOLD:
                self.results[(side, target)] = True
                self._advance()
        else:
            self.hold = max(0.0, self.hold - 2 * DT)
        return None

    def _advance(self):
        self.step += 1
        self.hold = 0.0
        self.skip.reset()
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
        if s["INDEX"] and s["FIST"]:
            index_open = statistics.median(m[1] for m in s["INDEX"])       # indicador levantado
            fist_high = statistics.median(max(m[1:]) for m in s["FIST"])   # dedo mais aberto no punho
            if index_open > fist_high:
                thresh["fingers"] = round((index_open + fist_high) / 2, 3)
            else:
                msgs.append("dedos: indicador e punho parecidos demais, limiar mantido")
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
        draw_text(screen, f"{tr.fps:.0f} fps   {tr.latency_ms:.0f} ms de atraso   "
                  f"cru E: {tr.gesture['L']}  D: {tr.gesture['R']}", 22, DIM, (40, 462), align="topleft")
        px, py = 560, 90
        draw_panel(screen, pygame.Rect(px, py, 480, 470))
        for i, (side, g, name, _) in enumerate(STEPS):
            if (side, g) in self.results:
                mark, color = ("OK", GREEN) if self.results[(side, g)] else ("X", RED)
            elif i == self.step and not self.done:
                mark, color = ">", YELLOW
            else:
                mark, color = "-", DIM
            draw_text(screen, f"{mark}  {i + 1}. {name}", 22, color, (px + 24, py + 12 + i * 24), align="topleft")
        if self.done:
            ok, n = sum(self.results.values()), len(STEPS)
            draw_text(screen, "Calibrado!" if ok == n else "Concluido", 44, GREEN if ok == n else YELLOW,
                      (px + 240, py + 215))
            draw_text(screen, f"{ok}/{n} comandos reconhecidos", 30, WHITE, (px + 240, py + 255))
            th = self.thresh or tr.thresh
            draw_text(screen, f"limiar dedos {th['fingers']:.2f}   polegar {th['thumb']:.2f}", 24, DIM,
                      (px + 240, py + 290))
            if self.msg:
                draw_text(screen, self.msg, 18, YELLOW, (px + 240, py + 320))
            draw_text(screen, "duas maos abertas: voltar ao menu", 26, DIM, (px + 240, py + 430))
            return
        side, _, name, hint = STEPS[self.step]
        draw_text(screen, f"Mostre: {name}", 36, YELLOW, (px + 240, py + 205))
        draw_text(screen, hint, 22, WHITE, (px + 240, py + 240))
        bar = pygame.Rect(px + 60, py + 264, 360, 22)
        pygame.draw.rect(screen, SHADOW, bar)
        pygame.draw.rect(screen, GREEN, (bar.x, bar.y, int(bar.w * min(self.hold / HOLD, 1)), bar.h))
        pygame.draw.rect(screen, DIM, bar, 2)
        draw_text(screen, f"segure o gesto: {SIDE_NAME[side]}", 20, DIM, (px + 240, py + 302))
        fside = "R" if side == "B" else side
        for i, (fname, ext, m) in enumerate(zip(FINGER_NAMES, tr.fingers[fside], tr.metrics[fside])):
            cx = px + 60 + i * 90
            pygame.draw.circle(screen, GREEN if ext else (70, 70, 85), (cx, py + 350), 14)
            pygame.draw.circle(screen, DIM, (cx, py + 350), 14, 2)
            draw_text(screen, fname, 18, DIM, (cx, py + 378))
            draw_text(screen, f"{m:.2f}", 18, DIM, (cx, py + 396))
        draw_text(screen, "tres dedos esquerda (segure): pula o passo   tres dedos direita: volta", 20, DIM,
                  (px + 240, py + 440))
