# tools/outcome.py
"""Gán nhãn kết quả ván (outcome) cho từng vị trí, thay cho nhãn heuristic cũ.

z theo góc nhìn phe TỐI: +1 dark thắng, -1 light thắng, 0 hòa/ván bị cắt theo
ply-cap. Vì cột ``winner`` chỉ khác 0 ở đúng dòng kết thúc ván, tổng ``winner``
theo từng ``id`` chính là z (bất biến với thứ tự dòng)."""
import pandas as pd


def attach_outcome_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Trả về bản sao df có thêm cột ``z`` = kết quả ván (broadcast mọi dòng).

    Loại các ván dị thường (|tổng winner| > 1, tức có nhiều hơn một dòng kết
    thúc) để nhãn luôn nằm trong {-1, 0, 1}."""
    outcome = df.groupby("id")["winner"].transform("sum")
    kept = df[outcome.abs() <= 1].copy()
    kept["z"] = kept.groupby("id")["winner"].transform("sum").astype("float32")
    return kept
