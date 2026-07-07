"""Quân Voi: quân cấp 8, mạnh nhất nhưng bị Chuột khắc chế."""

from scripts.common import PlayerSide
from scripts.piece import Piece, build_piece_args


class Elephant(Piece):
    """Không bắt được Chuột, trừ khi Chuột đang mất sức mạnh trong bẫy."""

    KEY = "elephant"  # Slug tra bảng metadata trong common.PIECES.

    def __init__(self, side: str, is_copy: bool = False) -> None:
        # Gom bảy tham số ctor từ bảng metadata thay vì gọi tay bốn lớp tra cứu.
        super().__init__(**build_piece_args(self.KEY, side, is_copy))

    def copy(self):
        # Bản sao dùng cho AI: is_copy=True bỏ qua ảnh để tiết kiệm RAM.
        return Elephant(self.side, is_copy=True)

    def can_defeat(self, piece) -> bool:
        # Import cục bộ phá vòng phụ thuộc Elephant <-> Rat.
        from scripts.pieces.rat import Rat

        # Ngoại lệ bát thú: Voi (cấp cao nhất) KHÔNG hạ được Chuột (cấp thấp
        # nhất), TRỪ KHI Chuột đang mất sức (atk == 0, tức đứng trên bẫy đối
        # phương); với mọi quân khác vẫn theo luật thường atk mình >= atk đối phương.
        return piece.atk == 0 if isinstance(piece, Rat) else self.atk >= piece.atk

    def weaker_pieces_positions(self, board) -> list[tuple[int, int]]:
        # Import cục bộ phá vòng phụ thuộc Elephant <-> Rat.
        from scripts.pieces.rat import Rat

        opponents = board.pieces_of[PlayerSide.opponent_of(self.side)]
        targets = [
            piece.position
            for piece in opponents
            # Mục tiêu hợp lệ: Chuột chỉ khi đang mất sức (atk == 0, khớp
            # can_defeat ở trên), hoặc quân khác Chuột yếu hơn theo luật thường.
            if (isinstance(piece, Rat) and piece.atk == 0)
            or (not isinstance(piece, Rat) and piece.atk < self.atk)
        ]
        return [PlayerSide.opponent_den_position(self.side), *targets]
