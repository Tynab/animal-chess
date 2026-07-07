"""Mã hóa bàn cờ sang tensor cho model CNN.

Tách khỏi ``manager.py``/``train.ipynb`` để chỉ còn MỘT nguồn sự thật cho phép
mã hóa. Định dạng phải giữ nguyên byte-for-byte vì ``models/best_model.h5`` đã
được huấn luyện theo đúng layout này.
"""
import numpy as np

# Bảng chữ ký hiệu quân (không phân biệt phe): tên lớp quân -> ký tự thường.
# Là nguồn sự thật duy nhất cho ký hiệu quân, dùng chung bởi log.map_piece_name.
PIECE_SYMBOLS = {
    "rat": "r", "cat": "c", "dog": "d", "wolf": "w",
    "leopard": "p", "tiger": "t", "lion": "l", "elephant": "e",
}

# Quân phe tối là số dương 1..8, phe sáng là số âm -1..-8, ô trống là 0.
PIECE_ENCODING = {
    "-": 0, "r": 1, "c": 2, "d": 3, "w": 4, "p": 5, "t": 6, "l": 7, "e": 8,
    "R": -1, "C": -2, "D": -3, "W": -4, "P": -5, "T": -6, "L": -7, "E": -8,
}


def encode_piece(piece_char: str) -> int:
    """Trả mã số của một ký tự quân; ký tự lạ coi như ô trống (0)."""
    return PIECE_ENCODING.get(piece_char, 0)


def encode_board(board_str: str) -> np.ndarray:
    """Chuỗi 63 ô -> tensor (9,7) đúng hướng tập dữ liệu/model cũ."""
    if len(board_str) != 63:
        raise ValueError(f"Bàn cờ phải có 63 ký tự, nhận {len(board_str)}.")
    # reversed -> reshape(7,9) -> transpose -> flip cả hai trục: phép xoay/lật
    # cố định để khớp hướng bàn của tập dữ liệu gốc. KHÔNG đổi.
    values = np.fromiter(
        (encode_piece(char) for char in reversed(board_str)),
        dtype=np.float32, count=63,
    )
    return np.flip(values.reshape(7, 9).T, axis=(0, 1)).copy()
