# tools/smoke_test.py
"""Bộ smoke/golden test cho Animal Chess.

Chạy headless hoàn toàn: dùng ``Board(is_copy=True)`` để dựng bàn logic không
nạp ảnh, nên không cần display, asset hay Git LFS. Dùng làm lưới chống hồi quy
cho đợt refactor: giá trị vàng được chốt từ code GỐC rồi kiểm lại sau mỗi bước.
"""
# Import scripts.* buộc phải nằm sau khi chèn ROOT vào sys.path -> tắt E402 cho file này.
# ruff: noqa: E402
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.board import Board
from scripts.bot import Bot
from scripts.common import PlayerSide
from scripts.log import Log

# encode_board chuyển sang scripts.encoding ở Task 2; import mềm để test không vỡ.
try:
    from scripts.encoding import encode_board
except ImportError:
    from scripts.manager import GameManager
    encode_board = GameManager.encode_board

GOLDEN_PATH = Path(__file__).resolve().parent / "golden.json"


def collect() -> dict:
    """Thu thập các bất biến format/luật/bot từ bàn khởi đầu."""
    board = Board(is_copy=True)                     # bàn đầu ván, không ảnh
    initial = Log.board_to_enum(board)
    tensor = encode_board(initial)

    dark_moves = len(board.get_valid_moves(PlayerSide.DARK))
    light_moves = len(board.get_valid_moves(PlayerSide.LIGHT))

    first = board.get_valid_moves(PlayerSide.LIGHT)[0]   # nước hợp lệ đầu tiên
    board.make_move(first)
    after = Log.board_to_enum(board)
    board.undo_move(first)
    restored = Log.board_to_enum(board)

    fresh = Board(is_copy=True)
    score, best = Bot.minimax(fresh, PlayerSide.LIGHT, 2, True)

    return {
        "initial_board": initial,
        "tensor_shape": list(tensor.shape),
        "tensor_flat": [float(v) for v in tensor.reshape(-1)],
        "dark_moves": dark_moves,
        "light_moves": light_moves,
        "after_first_move": after,
        "restored_after_undo": restored,
        "minimax_score": score,
        "minimax_best_count": len(best),
    }


def main() -> int:
    data = collect()
    if "--capture" in sys.argv:
        GOLDEN_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Đã ghi golden: {GOLDEN_PATH}")
        return 0
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    ok = True
    for key, want in golden.items():
        if data[key] != want:
            ok = False
            print(f"[SAI] {key}: want {want!r} got {data[key]!r}")
    if data["restored_after_undo"] != data["initial_board"]:
        ok = False
        print("[SAI] undo không khôi phục bàn ban đầu")
    print("SMOKE_OK" if ok else "SMOKE_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
