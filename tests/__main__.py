"""python -m tests: roda todas as checagens."""
from tests import test_game, test_vision

test_game.run_all(vars(test_game))
test_game.run_all(vars(test_vision))
print("todos passaram")
