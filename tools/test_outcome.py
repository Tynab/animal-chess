# tools/test_outcome.py
"""Kiểm thử attach_outcome_labels: gán z outcome cho mọi vị trí của ván."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from tools.outcome import attach_outcome_labels


def main() -> int:
    # 3 ván: dark thắng (+1), light thắng (-1), cap-draw (0). winner chỉ khác 0 ở dòng cuối.
    df = pd.DataFrame({
        "id":     ["g1","g1","g1", "g2","g2", "g3","g3","g3"],
        "winner": [0,   0,   1,    0,   -1,   0,   0,   0],
        "board":  ["-"] * 8,
    })
    out = attach_outcome_labels(df)
    ok = True
    z1 = out.loc[out.id == "g1", "z"].tolist()
    z2 = out.loc[out.id == "g2", "z"].tolist()
    z3 = out.loc[out.id == "g3", "z"].tolist()
    if z1 != [1.0, 1.0, 1.0]:
        ok = False
        print("[SAI] g1", z1)
    if z2 != [-1.0, -1.0]:
        ok = False
        print("[SAI] g2", z2)
    if z3 != [0.0, 0.0, 0.0]:
        ok = False
        print("[SAI] g3", z3)
    # Ván dị thường (|sum|>1) phải bị loại.
    bad = pd.DataFrame({"id": ["b","b"], "winner": [1, 1], "board": ["-","-"]})
    if len(attach_outcome_labels(bad)) != 0:
        ok = False
        print("[SAI] không loại ván |sum|>1")
    print("OUTCOME_OK" if ok else "OUTCOME_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
