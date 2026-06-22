"""Quân Báo: quân cấp 5 dùng luật di chuyển cơ bản."""

from scripts.common import (
    CellPosition,
    PieceArtWork,
    PieceAtk,
    PieceAvatar,
    PieceDetail,
    PieceName,
)
from scripts.piece import Piece


class Leopard(Piece):
    """Khởi tạo và sao chép quân Báo."""

    def __init__(self, side: str, is_copy: bool = False) -> None:
        super().__init__(
            PieceName.leopard(side),
            PieceDetail.LEOPARD,
            CellPosition.leopard(side),
            PieceAtk.LEOPARD,
            side,
            None if is_copy else PieceAvatar.leopard(side),
            None if is_copy else PieceArtWork.leopard(side),
        )

    def copy(self):
        return Leopard(self.side, is_copy=True)
