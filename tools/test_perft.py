# tools/test_perft.py
"""Kiểm thử perft: số node lá cố định + make/undo đối xứng (chuỗi bàn không đổi)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.board import Board
from scripts.common import PlayerSide
from scripts.log import Log
from tools.perft import perft


def main() -> int:
    b = Board(is_copy=True)
    before = Log.board_to_enum(b)
    ok = True
    for depth, want in ((1, 24), (2, 576), (3, 12264)):
        got = perft(b, PlayerSide.LIGHT, depth)
        if got != want:
            ok = False
            print(f"[SAI] perft d{depth}: want {want} got {got}")
    if Log.board_to_enum(b) != before:
        ok = False
        print("[SAI] make/undo không khôi phục bàn (chuỗi bàn đổi sau perft)")
    print("PERFT_OK" if ok else "PERFT_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
