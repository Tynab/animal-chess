"""Quân Sư tử: quân cấp 7 có thể nhảy qua sông nếu không bị Chuột chặn."""

from scripts.common import (
    CellPosition,
    PieceArtWork,
    PieceAtk,
    PieceAvatar,
    PieceDetail,
    PieceName,
)
from scripts.piece import RiverJumper


class Lion(RiverJumper):
    """Dùng chung thuật toán nhảy sông với Hổ."""

    def __init__(self, side: str, is_copy: bool = False) -> None:
        super().__init__(
            PieceName.lion(side),
            PieceDetail.LION,
            CellPosition.lion(side),
            PieceAtk.LION,
            side,
            None if is_copy else PieceAvatar.lion(side),
            None if is_copy else PieceArtWork.lion(side),
        )

    def copy(self):
        return Lion(self.side, is_copy=True)
