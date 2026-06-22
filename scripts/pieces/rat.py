"""Quân Chuột: quân cấp 1 có thể vào sông và khắc chế Voi."""

from scripts.common import (
    CellLabel,
    CellPosition,
    PieceArtWork,
    PieceAtk,
    PieceAvatar,
    PieceDetail,
    PieceName,
    PlayerSide,
)
from scripts.piece import Piece


class Rat(Piece):
    """Cài luật bắt Voi và khả năng đi trong sông."""

    def __init__(self, side: str, is_copy: bool = False) -> None:
        super().__init__(
            PieceName.rat(side),
            PieceDetail.RAT,
            CellPosition.rat(side),
            PieceAtk.RAT,
            side,
            None if is_copy else PieceAvatar.rat(side),
            None if is_copy else PieceArtWork.rat(side),
        )

    def copy(self):
        return Rat(self.side, is_copy=True)

    def can_defeat(self, piece) -> bool:
        # Import cục bộ phá vòng phụ thuộc Rat <-> Elephant.
        from scripts.pieces.elephant import Elephant

        return (isinstance(piece, Elephant) and self.atk != 0) or self.atk >= piece.atk

    def is_valid_cell(self, cell) -> bool:
        return (
            cell.is_in_board
            and not CellLabel.is_player_den(cell.label, self.side)
            and not cell.is_occupied_own(self.side)
            and (cell.piece is None or self.can_defeat(cell.piece))
        )

    def weaker_pieces_positions(self, board) -> list[tuple[int, int]]:
        from scripts.pieces.elephant import Elephant

        opponents = board.pieces_of[PlayerSide.opponent_of(self.side)]
        targets = [
            piece.position
            for piece in opponents
            if piece.atk < self.atk or (isinstance(piece, Elephant) and self.atk != 0)
        ]
        return [PlayerSide.opponent_den_position(self.side), *targets]
