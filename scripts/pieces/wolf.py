"""Quân Sói: quân cấp 4 dùng luật di chuyển cơ bản."""

from scripts.common import (
    CellPosition,
    PieceArtWork,
    PieceAtk,
    PieceAvatar,
    PieceDetail,
    PieceName,
)
from scripts.piece import Piece


class Wolf(Piece):
    """Khởi tạo và sao chép quân Sói."""

    def __init__(self, side: str, is_copy: bool = False) -> None:
        super().__init__(
            PieceName.wolf(side),
            PieceDetail.WOLF,
            CellPosition.wolf(side),
            PieceAtk.WOLF,
            side,
            None if is_copy else PieceAvatar.wolf(side),
            None if is_copy else PieceArtWork.wolf(side),
        )

    def copy(self):
        return Wolf(self.side, is_copy=True)
