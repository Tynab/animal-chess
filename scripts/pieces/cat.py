"""Quân Mèo: quân cấp 2 dùng luật di chuyển cơ bản."""

from scripts.common import (
    CellPosition,
    PieceArtWork,
    PieceAtk,
    PieceAvatar,
    PieceDetail,
    PieceName,
)
from scripts.piece import Piece


class Cat(Piece):
    """Khởi tạo và sao chép quân Mèo."""

    def __init__(self, side: str, is_copy: bool = False) -> None:
        super().__init__(
            PieceName.cat(side),
            PieceDetail.CAT,
            CellPosition.cat(side),
            PieceAtk.CAT,
            side,
            None if is_copy else PieceAvatar.cat(side),
            None if is_copy else PieceArtWork.cat(side),
        )

    def copy(self):
        return Cat(self.side, is_copy=True)
