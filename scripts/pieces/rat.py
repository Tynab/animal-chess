"""Quân Chuột: quân cấp 1 có thể vào sông và khắc chế Voi."""

from scripts.common import CellLabel, PlayerSide
from scripts.piece import Piece, build_piece_args


class Rat(Piece):
    """Cài luật bắt Voi và khả năng đi trong sông."""

    KEY = "rat"  # Slug tra bảng metadata trong common.PIECES.

    def __init__(self, side: str, is_copy: bool = False) -> None:
        # Gom bảy tham số ctor từ bảng metadata thay vì gọi tay bốn lớp tra cứu.
        super().__init__(**build_piece_args(self.KEY, side, is_copy))

    def copy(self):
        # Bản sao dùng cho AI: is_copy=True bỏ qua ảnh để tiết kiệm RAM.
        return Rat(self.side, is_copy=True)

    def can_defeat(self, piece) -> bool:
        # Import cục bộ phá vòng phụ thuộc Rat <-> Elephant.
        from scripts.pieces.elephant import Elephant

        # Ngoại lệ bát thú: Chuột (cấp thấp nhất) hạ được Voi (cấp cao nhất)
        # khi chưa bị vô hiệu hóa (atk != 0, tức Chuột không đứng trên bẫy
        # đối phương - atk chỉ bị triệt tiêu về 0 trên bẫy, không phải cứ ở
        # dưới sông là mất sức, xem Cell.add_piece); ngoài ngoại lệ đó vẫn
        # theo luật thường: atk mình >= atk đối phương.
        return (isinstance(piece, Elephant) and self.atk != 0) or self.atk >= piece.atk

    def is_valid_cell(self, cell) -> bool:
        # Giống Piece.is_valid_cell nhưng BỎ điều kiện "not cell.is_river" -> Chuột được phép vào sông.
        return (
            cell.is_in_board
            and not CellLabel.is_player_den(cell.label, self.side)
            and not cell.is_occupied_own(self.side)
            and (cell.piece is None or self.can_defeat(cell.piece))
        )

    def weaker_pieces_positions(self, board) -> list[tuple[int, int]]:
        # Import cục bộ phá vòng phụ thuộc Rat <-> Elephant.
        from scripts.pieces.elephant import Elephant

        opponents = board.pieces_of[PlayerSide.opponent_of(self.side)]
        targets = [
            piece.position
            for piece in opponents
            # Mục tiêu hợp lệ: quân yếu hơn theo luật thường, HOẶC là Voi mà
            # Chuột chưa bị vô hiệu hóa (atk != 0, tức Chuột không đứng trên
            # bẫy đối phương) - khớp với can_defeat ở trên.
            if piece.atk < self.atk or (isinstance(piece, Elephant) and self.atk != 0)
        ]
        return [PlayerSide.opponent_den_position(self.side), *targets]
