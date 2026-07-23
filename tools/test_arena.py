# tools/test_arena.py
"""Kiểm thử thống kê nhị thức một phía của arena."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.arena import one_sided_binom_p


def main() -> int:
    ok = True
    if abs(one_sided_binom_p(5, 10) - 0.6230) > 1e-3:
        ok = False
        print("[SAI] 5/10")
    if one_sided_binom_p(10, 10) >= 0.01:
        ok = False
        print("[SAI] 10/10 phải rất nhỏ")
    if abs(one_sided_binom_p(0, 0) - 1.0) > 1e-9:
        ok = False
        print("[SAI] 0/0")
    if one_sided_binom_p(220, 400) >= 0.05:
        ok = False
        print("[SAI] 220/400 phải <0.05")
    print("ARENA_STATS_OK" if ok else "ARENA_STATS_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
