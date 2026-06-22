"""Quân Chó: quân cấp 3 có thể di chuyển trong sông theo luật của dự án."""

from scripts.common import (
    CellLabel,
    CellPosition,
    PieceArtWork,
    PieceAtk,
    PieceAvatar,
    PieceDetail,
    PieceName,
)
from scripts.piece import Piece


class Dog(Piece):
    """Mở rộng quân cơ sở bằng quyền đi vào ô sông."""

    def __init__(self, side: str, is_copy: bool = False) -> None:
        super().__init__(
            PieceName.dog(side),
            PieceDetail.DOG,
            CellPosition.dog(side),
            PieceAtk.DOG,
            side,
            None if is_copy else PieceAvatar.dog(side),
            None if is_copy else PieceArtWork.dog(side),
        )

    def copy(self):
        return Dog(self.side, is_copy=True)

    def is_valid_cell(self, cell) -> bool:
        return (
            cell.is_in_board
            and not CellLabel.is_player_den(cell.label, self.side)
            and not cell.is_occupied_own(self.side)
            and (cell.piece is None or self.can_defeat(cell.piece))
        )
