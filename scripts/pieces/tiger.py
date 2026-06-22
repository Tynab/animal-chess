"""Quân Hổ: quân cấp 6 có thể nhảy qua sông nếu không bị Chuột chặn."""

from scripts.common import (
    CellPosition,
    PieceArtWork,
    PieceAtk,
    PieceAvatar,
    PieceDetail,
    PieceName,
)
from scripts.piece import RiverJumper


class Tiger(RiverJumper):
    """Dùng chung thuật toán nhảy sông với Sư tử."""

    def __init__(self, side: str, is_copy: bool = False) -> None:
        super().__init__(
            PieceName.tiger(side),
            PieceDetail.TIGER,
            CellPosition.tiger(side),
            PieceAtk.TIGER,
            side,
            None if is_copy else PieceAvatar.tiger(side),
            None if is_copy else PieceArtWork.tiger(side),
        )

    def copy(self):
        return Tiger(self.side, is_copy=True)
