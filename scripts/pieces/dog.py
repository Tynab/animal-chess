"""Quân Chó: quân cấp 3 có thể di chuyển trong sông theo luật của dự án."""

from scripts.common import CellLabel
from scripts.piece import Piece, build_piece_args


class Dog(Piece):
    """Mở rộng quân cơ sở bằng quyền đi vào ô sông."""

    KEY = "dog"  # Slug tra bảng metadata trong common.PIECES.

    def __init__(self, side: str, is_copy: bool = False) -> None:
        # Gom bảy tham số ctor từ bảng metadata thay vì gọi tay bốn lớp tra cứu.
        super().__init__(**build_piece_args(self.KEY, side, is_copy))

    def copy(self):
        # Bản sao dùng cho AI: is_copy=True bỏ qua ảnh để tiết kiệm RAM.
        return Dog(self.side, is_copy=True)

    def is_valid_cell(self, cell) -> bool:
        # Giống Piece.is_valid_cell nhưng BỎ điều kiện "not cell.is_river" -> Chó được phép vào sông.
        return (
            cell.is_in_board
            and not CellLabel.is_player_den(cell.label, self.side)
            and not cell.is_occupied_own(self.side)
            and (cell.piece is None or self.can_defeat(cell.piece))
        )
