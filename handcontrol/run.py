"""Estado de uma campanha (vidas, moedas, itens, checkpoint) e o progresso salvo entre sessões."""
import json
import os

from .config import COINS_PER_LIFE, LIVES, MAX_LIVES, SHOP, STARS

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "progress.json")
PRICES = {key: price for key, _, price, _ in SHOP}


class Run:
    def __init__(self, level_idx=0):
        self.level_idx = level_idx
        self.lives = LIVES
        self.coins = 0          # saldo gastável na loja
        self.coins_total = 0    # coletadas na campanha; a cada 20 uma vida
        self.shield_next = False    # comprados na loja, valem para a próxima fase
        self.highjump_next = False
        self.shield = False         # ativos na fase atual
        self.highjump = False
        self.checkpoint = None      # Rect do checkpoint alcançado na fase atual
        self.deaths = 0             # mortes na fase atual (estrela "sem morrer")
        self.total_time = 0.0

    def add_coins(self, n) -> int:
        """-> quantas vidas extras ganhou agora."""
        before = self.coins_total // COINS_PER_LIFE
        self.coins += n
        self.coins_total += n
        gained = self.coins_total // COINS_PER_LIFE - before
        gained = min(gained, MAX_LIVES - self.lives)
        self.lives += max(0, gained)
        return max(0, gained)

    def add_life(self) -> bool:
        if self.lives >= MAX_LIVES:
            return False
        self.lives += 1
        return True

    def can_buy(self, key) -> bool:
        if self.coins < PRICES[key]:
            return False
        return {"heart": self.lives < MAX_LIVES, "shield": not self.shield_next,
                "highjump": not self.highjump_next}[key]

    def buy(self, key) -> bool:
        if not self.can_buy(key):
            return False
        self.coins -= PRICES[key]
        if key == "heart":
            self.lives += 1
        elif key == "shield":
            self.shield_next = True
        else:
            self.highjump_next = True
        return True

    def start_level(self, idx):
        """Ativa os itens comprados e zera o que é por fase."""
        self.level_idx = idx
        self.shield, self.highjump = self.shield_next, self.highjump_next
        self.shield_next = self.highjump_next = False
        self.checkpoint = None
        self.deaths = 0


def stars_for(collected, coins_total, deaths) -> set:
    s = {"done"}
    if collected >= coins_total:
        s.add("coins")
    if deaths == 0:
        s.add("nodeath")
    return s


def load_progress() -> dict:
    try:
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return {"unlocked": int(d.get("unlocked", 1)), "stars": {int(k): set(v) for k, v in d.get("stars", {}).items()}}
    except (OSError, ValueError):
        return {"unlocked": 1, "stars": {}}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"unlocked": progress["unlocked"],
                   "stars": {str(k): sorted(v) for k, v in progress["stars"].items()}}, f, indent=2)


def record_level(progress: dict, level_idx: int, stars: set, n_levels: int):
    progress["stars"][level_idx] = progress["stars"].get(level_idx, set()) | stars
    progress["unlocked"] = max(progress["unlocked"], min(level_idx + 2, n_levels))
    save_progress(progress)


STAR_NAMES = dict(STARS)
