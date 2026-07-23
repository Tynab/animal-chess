"""Quân Hổ: quân cấp 6 có thể nhảy qua sông nếu không bị Chuột chặn."""

from scripts.piece import RiverJumper, build_piece_args


class Tiger(RiverJumper):
    """Dùng chung thuật toán nhảy sông (available_cells) với Sư tử qua RiverJumper."""

    KEY = "tiger"  # Slug tra bảng metadata trong common.PIECES.

    def __init__(self, side: str, is_copy: bool = False) -> None:
        # Gom bảy tham số ctor từ bảng metadata thay vì gọi tay bốn lớp tra cứu.
        super().__init__(**build_piece_args(self.KEY, side, is_copy))

    def copy(self):
        # Bản sao dùng cho AI: is_copy=True bỏ qua ảnh để tiết kiệm RAM.
        return Tiger(self.side, is_copy=True)
