"""python -m tests: roda todas as checagens."""
from tests import test_campaign, test_game, test_vision

for mod in (test_game, test_vision, test_campaign):
    test_game.run_all(vars(mod))
print("todos passaram")
