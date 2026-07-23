# tools/arena.py
"""Đấu model MỚI vs model CŨ để đo mạnh-yếu (headless). Chỉ khi model mới đạt
score >= 0.55 và có ý nghĩa nhị thức một phía (p<0.05) mới nên promote thủ công
best_model_outcome.h5 -> best_model.h5."""
import os
import random
import sys
from math import comb
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from scripts.board import Board
from scripts.common import BEST_MODEL_PATH, MODEL_DIR, PlayerSide
from scripts.manager import ModelEvaluator


def one_sided_binom_p(wins: int, decisive: int) -> float:
    """P(X >= wins) với X ~ Binomial(decisive, 0.5). decisive=0 -> 1.0."""
    if decisive <= 0:
        return 1.0
    tail = sum(comb(decisive, k) for k in range(wins, decisive + 1))
    return tail / (2 ** decisive)


def _winner_of(new_eval, old_eval, new_side, max_plies, opening_random_plies):
    """Chơi một ván; trả 'new'/'old'/'draw' theo phe mà model mới cầm."""
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
            ev = new_eval if side == new_side else old_eval
            move = ev.best_move(board, side)
            if move is None:
                break
        board.make_move(move)
        if board.is_game_over:
            break
        side = PlayerSide.opponent_of(side)
    winner = board.winner                            # PlayerSide hoặc None (hòa/cap)
    if winner is None:
        return "draw"
    return "new" if winner == new_side else "old"


def play_match(new_path, old_path, games, max_plies, opening_random_plies) -> dict:
    """Đấu `games` ván, đổi màu một nửa; trả thống kê + khuyến nghị promote."""
    new_eval = ModelEvaluator(new_path)
    old_eval = ModelEvaluator(old_path)
    new_wins = old_wins = draws = 0
    for i in range(games):
        new_side = PlayerSide.DARK if i % 2 == 0 else PlayerSide.LIGHT
        r = _winner_of(new_eval, old_eval, new_side, max_plies, opening_random_plies)
        if r == "new":
            new_wins += 1
        elif r == "old":
            old_wins += 1
        else:
            draws += 1
    score = (new_wins + 0.5 * draws) / games if games else 0.0
    decisive = new_wins + old_wins
    p = one_sided_binom_p(new_wins, decisive)
    return {
        "new_wins": new_wins, "old_wins": old_wins, "draws": draws,
        "score": score, "p_value": p,
        "promote": bool(score >= 0.55 and p < 0.05),
    }


def main() -> int:
    games = int(os.getenv("ARENA_GAMES", "400"))
    max_plies = int(os.getenv("MAX_PLIES", "300"))
    opening = int(os.getenv("OPENING_RANDOM_PLIES", "6"))
    seed = os.getenv("ARENA_SEED")
    if seed is not None:
        random.seed(int(seed))
    new_path = os.getenv("NEW_MODEL", str(MODEL_DIR / "best_model_outcome.h5"))
    old_path = os.getenv("OLD_MODEL", str(BEST_MODEL_PATH))
    res = play_match(new_path, old_path, games, max_plies, opening)
    print(f"new_wins={res['new_wins']} old_wins={res['old_wins']} draws={res['draws']}")
    print(f"score={res['score']:.4f} p={res['p_value']:.4g} promote={res['promote']}")
    print("ARENA_PROMOTE" if res["promote"] else "ARENA_NO_PROMOTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
