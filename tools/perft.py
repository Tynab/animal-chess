# tools/perft.py
"""Perft: đếm số node lá ở độ sâu N qua make_move/undo_move + get_valid_moves.

Dùng để tin cậy tính đúng của bộ sinh nước + tính đối xứng make/undo mà engine
alpha-beta phụ thuộc. Không nằm trên đường chơi."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ruff: noqa: E402
from scripts.common import PlayerSide


def perft(board, side, depth: int) -> int:
    """Số chuỗi nước hợp lệ độ dài `depth` từ thế cờ hiện tại (khôi phục bàn khi xong)."""
    if depth == 0:
        return 1
    total = 0
    opponent = PlayerSide.opponent_of(side)
    for move in board.get_valid_moves(side):
        board.make_move(move)
        total += perft(board, opponent, depth - 1)
        board.undo_move(move)
    return total


if __name__ == "__main__":
    from scripts.board import Board
    b = Board(is_copy=True)
    for d in (1, 2, 3):
        print(f"perft(initial, LIGHT, {d}) = {perft(b, PlayerSide.LIGHT, d)}")
