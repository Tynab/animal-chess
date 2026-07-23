# tools/test_evalarena.py
"""Kiểm thử tiện ích evalarena: re-export thống kê nhị thức chạy được."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.evalarena import one_sided_binom_p


def main() -> int:
    ok = True
    if one_sided_binom_p(120, 200) >= 0.05:      # 60% -> có ý nghĩa
        ok = False
        print("[SAI] 120/200 phải <0.05")
    if one_sided_binom_p(0, 0) != 1.0:
        ok = False
        print("[SAI] decisive=0 phải 1.0")
    print("EVALARENA_STATS_OK" if ok else "EVALARENA_STATS_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
