# tools/test_search.py
"""Kiểm thử engine: zobrist, search_eval, tương đương Bot.minimax, ngân sách."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.board import Board
from scripts.bot import Bot
from scripts.common import PlayerSide
from scripts.log import Log
from scripts.pieces.rat import Rat
from scripts.search import SearchEngine, search_eval, zobrist_key


def _advance(board, side, plies):
    for _ in range(plies):
        moves = board.get_valid_moves(side)
        if not moves:
            break
        board.make_move(moves[0])
        side = PlayerSide.opponent_of(side)
    return side


def main() -> int:
    ok = True
    b = Board(is_copy=True)

    k1 = zobrist_key(b, PlayerSide.LIGHT)
    if zobrist_key(b, PlayerSide.LIGHT) != k1:
        ok = False
        print("[SAI] zobrist không ổn định")
    if zobrist_key(b, PlayerSide.DARK) == k1:
        ok = False
        print("[SAI] zobrist không phân biệt phe")
    mv = b.get_valid_moves(PlayerSide.LIGHT)[0]
    b.make_move(mv)
    b.undo_move(mv)
    if zobrist_key(b, PlayerSide.LIGHT) != k1:
        ok = False
        print("[SAI] zobrist đổi sau make+undo")

    if search_eval(b, PlayerSide.DARK, 0) != Bot.evaluate_position(b, PlayerSide.DARK):
        ok = False
        print("[SAI] search_eval(gradient=0) != evaluate_position")

    eng = SearchEngine(gradient_coef=0, quiescence=False)
    for plies in (0, 2, 4):
        pos = Board(is_copy=True)
        side = _advance(pos, PlayerSide.LIGHT, plies)
        for depth in (1, 2, 3):
            got = eng.value(pos, side, depth)
            want = Bot.minimax(pos, side, depth, True)[0]
            if got != want:
                ok = False
                print(f"[SAI] value!=minimax plies={plies} d{depth}: {got} vs {want}")

    eng2 = SearchEngine(time_budget_s=0.3)
    move, info = eng2.best_move(Board(is_copy=True), PlayerSide.LIGHT)
    if move not in Board(is_copy=True).get_valid_moves(PlayerSide.LIGHT):
        ok = False
        print("[SAI] best_move trả nước không hợp lệ")
    if info["depth"] < 1:
        ok = False
        print("[SAI] best_move không đạt nổi depth 1")
    eng3 = SearchEngine(time_budget_s=None, max_depth=2)
    _, info3 = eng3.best_move(Board(is_copy=True), PlayerSide.LIGHT)
    if info3["depth"] != 2:
        ok = False
        print(f"[SAI] max_depth không tôn trọng: {info3['depth']}")

    # Hồi quy: best_move phải khôi phục bàn ĐÃ tìm kiếm kể cả khi hết giờ giữa chừng.
    searched = Board(is_copy=True)
    before_search = Log.board_to_enum(searched)
    SearchEngine(time_budget_s=0.001).best_move(searched, PlayerSide.LIGHT)
    if searched.move_history or Log.board_to_enum(searched) != before_search:
        ok = False
        print("[SAI] best_move không khôi phục bàn sau timeout")

    # Rung 2 — số hạng phòng thủ hang.
    if search_eval(b, PlayerSide.DARK, 0, 0) != Bot.evaluate_position(b, PlayerSide.DARK):
        ok = False
        print("[SAI] search_eval(0,0) != evaluate_position")
    # Đặt một quân TỐI trong bán kính hang tối (3,0) -> defense dương cho DARK, âm cho LIGHT.
    guard = Board(with_pieces=False, is_copy=True)
    guard.get_cell((3, 2)).add_piece(Rat(PlayerSide.DARK, is_copy=True))
    guard.update_pieces()
    dark_contrib = search_eval(guard, PlayerSide.DARK, 0, 1) - search_eval(guard, PlayerSide.DARK, 0, 0)
    light_contrib = search_eval(guard, PlayerSide.LIGHT, 0, 1) - search_eval(guard, PlayerSide.LIGHT, 0, 0)
    if dark_contrib <= 0:
        ok = False
        print(f"[SAI] defense không dương khi có quân canh hang nhà: {dark_contrib}")
    if light_contrib >= 0:
        ok = False
        print(f"[SAI] defense không âm cho phe đối diện: {light_contrib}")

    print("SEARCH_OK" if ok else "SEARCH_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
