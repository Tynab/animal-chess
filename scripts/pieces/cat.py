"""Quân Mèo: quân cấp 2 dùng luật di chuyển cơ bản."""

from scripts.piece import Piece, build_piece_args


class Cat(Piece):
    """Không có luật riêng: dùng nguyên vẹn can_defeat/is_valid_cell của Piece."""

    KEY = "cat"  # Slug tra bảng metadata trong common.PIECES.

    def __init__(self, side: str, is_copy: bool = False) -> None:
        # Gom bảy tham số ctor từ bảng metadata thay vì gọi tay bốn lớp tra cứu.
        super().__init__(**build_piece_args(self.KEY, side, is_copy))

    def copy(self):
        # Bản sao dùng cho AI: is_copy=True bỏ qua ảnh để tiết kiệm RAM.
        return Cat(self.side, is_copy=True)
