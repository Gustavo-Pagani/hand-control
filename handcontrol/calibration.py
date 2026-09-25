"""Tela de calibração: pede cada comando de cada mão, mede as métricas e ajusta os limiares."""
import statistics

import pygame

from .camview import draw_camera
from .config import DT
from .inputs import Hold
from .ui import DIM, GREEN, RED, SHADOW, WHITE, YELLOW, dim, draw_panel, draw_text
from .vision import FINGER_NAMES, save_calibration

# (lado, gesto, nome curto, instrução)
STEPS = [("L", "INDEX", "FRENTE", "mao esquerda, so o indicador levantado"),
         ("L", "THUMB", "TRAS", "mao esquerda, so o polegar, joinha"),
         ("R", "INDEX", "PULO", "mao direita, so um dedo levantado (o indicador para calibrar)"),
         ("A", "OK", "OK", "polegar e indicador em circulo, outros dedos abertos (qualquer mao)")]
HOLD = 1.0  # s segurando o gesto certo para o passo contar
SIDE_NAME = {"L": "esquerda", "R": "direita", "A": "qualquer mao"}


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
        self.skip = Hold(1.5)   # dois punhos segurados pulam o passo

    def _hand_for(self, side, target):
        """Lado que está fazendo o gesto pedido, ou None. 'A' aceita qualquer mão."""
        st, lm = self.tracker.stable, self.tracker.landmarks
        for s in (("L", "R") if side == "A" else (side,)):
            if st[s] == target and s in lm:
                return s
        return None

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
        hand = self._hand_for(side, target)
        if self.skip.update(tr.stable["L"] == "FIST" and tr.stable["R"] == "FIST", DT):
            self.results[(side, target)] = False
            self._advance()
        elif hand:
            self.hold += DT
            self.samples[target].append(tr.metrics[hand])
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
        if s["INDEX"]:
            index_open = statistics.median(m[1] for m in s["INDEX"])           # indicador levantado
            rest_closed = statistics.median(max(m[2:]) for m in s["INDEX"])    # medio/anelar/minimo dobrados
            if index_open > rest_closed:
                thresh["fingers"] = round((index_open + rest_closed) / 2, 3)
            else:
                msgs.append("dedos: indicador e os outros parecidos demais, limiar mantido")
        if s["THUMB"] and s["INDEX"]:
            thumb_open = statistics.median(m[0] for m in s["THUMB"])
            thumb_closed = statistics.median(m[0] for m in s["INDEX"])
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
            draw_text(screen, f"{mark}  {i + 1}. {name}", 30, color, (px + 24, py + 20 + i * 40), align="topleft")
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
            draw_text(screen, "sinal de OK: voltar ao menu", 26, DIM, (px + 240, py + 430))
            return
        side, target, name, hint = STEPS[self.step]
        hand = self._hand_for(side, target)
        draw_text(screen, f"Mostre: {name}", 36, YELLOW, (px + 240, py + 240))
        draw_text(screen, hint, 22, WHITE, (px + 240, py + 272))
        bar = pygame.Rect(px + 60, py + 294, 360, 22)
        pygame.draw.rect(screen, SHADOW, bar)
        pygame.draw.rect(screen, GREEN, (bar.x, bar.y, int(bar.w * min(self.hold / HOLD, 1)), bar.h))
        pygame.draw.rect(screen, DIM, bar, 2)
        draw_text(screen, f"segure o gesto: {SIDE_NAME[side]}", 20, DIM, (px + 240, py + 330))
        fside = hand or ("R" if side == "A" else side)
        for i, (fname, ext, m) in enumerate(zip(FINGER_NAMES, tr.fingers[fside], tr.metrics[fside])):
            cx = px + 60 + i * 90
            pygame.draw.circle(screen, GREEN if ext else (70, 70, 85), (cx, py + 372), 14)
            pygame.draw.circle(screen, DIM, (cx, py + 372), 14, 2)
            draw_text(screen, fname, 18, DIM, (cx, py + 398))
            draw_text(screen, f"{m:.2f}", 18, DIM, (cx, py + 416))
        draw_text(screen, "dois punhos (segure): pula o passo   tres dedos esquerda: volta", 20, DIM,
                  (px + 240, py + 440))
