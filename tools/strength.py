# tools/strength.py
"""Đấu ENGINE (alpha-beta sâu) vs bot CNN hiện tại để đo Rung 1 có mạnh hơn không.

Thành công = engine đạt score >= 0.80 và nhị thức một phía p<0.05. Tái dùng
one_sided_binom_p của arena. Headless, có random khai cuộc + ply-cap."""
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
from scripts.common import BEST_MODEL_PATH, PlayerSide
from scripts.manager import ModelEvaluator
from scripts.search import SearchEngine
from tools.arena import one_sided_binom_p


def _play_game(engine, evaluator, engine_side, max_plies, opening_random_plies):
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
        elif side == engine_side:
            move, _ = engine.best_move(board, side)
        else:
            move = evaluator.best_move(board, side)
        if move is None:
            break
        board.make_move(move)
        if board.is_game_over:
            break
        side = PlayerSide.opponent_of(side)
    winner = board.winner
    if winner is None:
        return "draw"
    return "engine" if winner == engine_side else "baseline"


def play_strength(search_time, max_depth, games, max_plies, opening_random_plies, model_path):
    evaluator = ModelEvaluator(model_path)
    engine = SearchEngine(time_budget_s=search_time, max_depth=max_depth)
    ew = bw = draws = 0
    for i in range(games):
        engine_side = PlayerSide.DARK if i % 2 == 0 else PlayerSide.LIGHT
        r = _play_game(engine, evaluator, engine_side, max_plies, opening_random_plies)
        if r == "engine":
            ew += 1
        elif r == "baseline":
            bw += 1
        else:
            draws += 1
    score = (ew + 0.5 * draws) / games if games else 0.0
    decisive = ew + bw
    p = one_sided_binom_p(ew, decisive)
    return {"engine_wins": ew, "baseline_wins": bw, "draws": draws,
            "score": score, "p_value": p, "pass": bool(score >= 0.80 and p < 0.05)}


def main() -> int:
    games = int(os.getenv("STRENGTH_GAMES", "200"))
    max_plies = int(os.getenv("MAX_PLIES", "300"))
    opening = int(os.getenv("OPENING_RANDOM_PLIES", "6"))
    search_time = os.getenv("STRENGTH_SEARCH_TIME")
    search_time = float(search_time) if search_time else None
    max_depth = int(os.getenv("STRENGTH_MAX_DEPTH", "4")) if search_time is None else None
    seed = os.getenv("STRENGTH_SEED")
    if seed is not None:
        random.seed(int(seed))
    res = play_strength(search_time, max_depth, games, max_plies, opening,
                        os.getenv("BASELINE_MODEL", str(BEST_MODEL_PATH)))
    print(f"engine_wins={res['engine_wins']} baseline_wins={res['baseline_wins']} draws={res['draws']}")
    print(f"score={res['score']:.4f} p={res['p_value']:.4g} pass={res['pass']}")
    print("STRENGTH_PROMOTE" if res["pass"] else "STRENGTH_NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
