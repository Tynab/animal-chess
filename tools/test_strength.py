# tools/test_strength.py
"""Kiểm thử thống kê của strength arena (tái dùng one_sided_binom_p)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.strength import one_sided_binom_p


def main() -> int:
    ok = True
    if one_sided_binom_p(160, 200) >= 0.05:      # 80% -> có ý nghĩa một phía
        ok = False
        print("[SAI] 160/200 phải <0.05")
    if not (0.4 < one_sided_binom_p(100, 200) < 0.6):   # 50/50 -> ~0.5
        ok = False
        print("[SAI] 100/200 phải xấp xỉ 0.5")
    if one_sided_binom_p(0, 0) != 1.0:
        ok = False
        print("[SAI] decisive=0 phải trả 1.0")
    print("STRENGTH_STATS_OK" if ok else "STRENGTH_STATS_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
