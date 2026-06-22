"""Quân Voi: quân cấp 8, mạnh nhất nhưng bị Chuột khắc chế."""

from scripts.common import (
    CellPosition,
    PieceArtWork,
    PieceAtk,
    PieceAvatar,
    PieceDetail,
    PieceName,
    PlayerSide,
)
from scripts.piece import Piece


class Elephant(Piece):
    """Không bắt được Chuột, trừ khi Chuột đang mất sức mạnh trong bẫy."""

    def __init__(self, side: str, is_copy: bool = False) -> None:
        super().__init__(
            PieceName.elephant(side),
            PieceDetail.ELEPHANT,
            CellPosition.elephant(side),
            PieceAtk.ELEPHANT,
            side,
            None if is_copy else PieceAvatar.elephant(side),
            None if is_copy else PieceArtWork.elephant(side),
        )

    def copy(self):
        return Elephant(self.side, is_copy=True)

    def can_defeat(self, piece) -> bool:
        from scripts.pieces.rat import Rat

        return piece.atk == 0 if isinstance(piece, Rat) else self.atk >= piece.atk

    def weaker_pieces_positions(self, board) -> list[tuple[int, int]]:
        from scripts.pieces.rat import Rat

        opponents = board.pieces_of[PlayerSide.opponent_of(self.side)]
        targets = [
            piece.position
            for piece in opponents
            if (isinstance(piece, Rat) and piece.atk == 0)
            or (not isinstance(piece, Rat) and piece.atk < self.atk)
        ]
        return [PlayerSide.opponent_den_position(self.side), *targets]
