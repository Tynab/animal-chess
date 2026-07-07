"""Quân Sư tử: quân cấp 7 có thể nhảy qua sông nếu không bị Chuột chặn."""

from scripts.piece import RiverJumper, build_piece_args


class Lion(RiverJumper):
    """Dùng chung thuật toán nhảy sông (available_cells) với Hổ qua RiverJumper."""

    KEY = "lion"  # Slug tra bảng metadata trong common.PIECES.

    def __init__(self, side: str, is_copy: bool = False) -> None:
        # Gom bảy tham số ctor từ bảng metadata thay vì gọi tay bốn lớp tra cứu.
        super().__init__(**build_piece_args(self.KEY, side, is_copy))

    def copy(self):
        # Bản sao dùng cho AI: is_copy=True bỏ qua ảnh để tiết kiệm RAM.
        return Lion(self.side, is_copy=True)
