# tools/evalarena.py
"""A/B eval: đấu HAI cấu hình SearchEngine (khác hệ số eval, cùng độ sâu) để
quyết định giữ hay bỏ một số hạng. Tái dùng one_sided_binom_p của arena.
Giữ số hạng nếu cấu hình A thắng score >= 0.55 và p<0.05."""
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from scripts.board import Board
from scripts.common import PlayerSide
from scripts.search import SearchEngine
from tools.arena import one_sided_binom_p


def _play_game(engine_a, engine_b, a_side, max_plies, opening_random_plies):
    board = Board(is_copy=True)
    side = PlayerSide.LIGHT
    for ply in range(max_plies):
        if board.is_game_over:
            break
        if ply < opening_random_plies:
            moves = board.get_valid_moves(side)
            if not moves:
                break
            move = random.choice(moves)
        else:
            engine = engine_a if side == a_side else engine_b
            move, _ = engine.best_move(board, side)
        if move is None:
            break
        board.make_move(move)
        if board.is_game_over:
            break
        side = PlayerSide.opponent_of(side)
    winner = board.winner
    if winner is None:
        return "draw"
    return "a" if winner == a_side else "b"


def play_ab(a_kwargs, b_kwargs, games, max_plies, opening_random_plies):
    engine_a = SearchEngine(**a_kwargs)
    engine_b = SearchEngine(**b_kwargs)
    aw = bw = draws = 0
    for i in range(games):
        a_side = PlayerSide.DARK if i % 2 == 0 else PlayerSide.LIGHT
        r = _play_game(engine_a, engine_b, a_side, max_plies, opening_random_plies)
        if r == "a":
            aw += 1
        elif r == "b":
            bw += 1
        else:
            draws += 1
    score = (aw + 0.5 * draws) / games if games else 0.0
    decisive = aw + bw
    p = one_sided_binom_p(aw, decisive)
    return {"a_wins": aw, "b_wins": bw, "draws": draws, "score": score,
            "p_value": p, "keep": bool(score >= 0.55 and p < 0.05)}


def main() -> int:
    games = int(os.getenv("EVALARENA_GAMES", "200"))
    max_plies = int(os.getenv("MAX_PLIES", "200"))
    opening = int(os.getenv("OPENING_RANDOM_PLIES", "6"))
    depth = int(os.getenv("EVAL_MAX_DEPTH", "3"))
    a = {"time_budget_s": None, "max_depth": depth,
         "gradient_coef": int(os.getenv("A_GRADIENT_COEF", "1")),
         "defense_coef": int(os.getenv("A_DEFENSE_COEF", "5"))}
    b = {"time_budget_s": None, "max_depth": depth,
         "gradient_coef": int(os.getenv("B_GRADIENT_COEF", "1")),
         "defense_coef": int(os.getenv("B_DEFENSE_COEF", "0"))}
    seed = os.getenv("EVALARENA_SEED")
    if seed is not None:
        random.seed(int(seed))
    res = play_ab(a, b, games, max_plies, opening)
    print(f"A(defense={a['defense_coef']}) vs B(defense={b['defense_coef']}): "
          f"a_wins={res['a_wins']} b_wins={res['b_wins']} draws={res['draws']}")
    print(f"score={res['score']:.4f} p={res['p_value']:.4g} keep={res['keep']}")
    print("EVAL_KEEP" if res["keep"] else "EVAL_NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
