"""Lớp quân cờ cơ sở và luật di chuyển dùng chung.

Mỗi quân cụ thể chỉ cần cung cấp metadata và ghi đè phần luật đặc biệt. Module
không phụ thuộc các lớp quân con nên tránh được vòng import với ``Cell``.
"""

import pygame

from scripts import common
from scripts.common import CellLabel, PlayerSide, Size


def build_piece_args(key: str, side: str, is_copy: bool) -> dict:
    """Gom tham số khởi tạo cho một quân từ bảng metadata trong common.

    Mỗi lớp quân con (Rat, Cat, Dog, ...) trước đây phải tự liệt kê lại bảy
    tham số của ``Piece.__init__`` (tên, mô tả, vị trí, atk, phe, ảnh, ảnh
    minh họa) bằng cách gọi trực tiếp bốn lớp tra cứu trong common. Hàm này
    tra cứu hộ, để __init__ của mỗi quân chỉ còn một dòng gọi super().

    `key` là slug viết thường của quân (rat, cat, dog, ...) - trùng tên
    staticmethod trong CellPosition/PieceName/PieceAvatar/PieceArtWork và
    trùng tên thuộc tính viết hoa trong PieceAtk/PieceDetail. Khi `is_copy`
    là True (dùng cho AI dò cây nước đi), bỏ qua đường dẫn ảnh/ảnh minh họa
    để không tốn RAM nạp ảnh không cần hiển thị.
    """

    from scripts.common import (
        CellPosition, PieceName, PieceDetail, PieceAtk, PieceAvatar, PieceArtWork,
    )

    return {
        "name": getattr(PieceName, key)(side),
        "detail": getattr(PieceDetail, key.upper()),
        "position": getattr(CellPosition, key)(side),
        "atk": getattr(PieceAtk, key.upper()),
        "side": side,
        "image_path": None if is_copy else getattr(PieceAvatar, key)(side),
        "artwork_path": None if is_copy else getattr(PieceArtWork, key)(side),
    }


class Piece:
    """Quân cờ cơ sở, quản lý vị trí, sức mạnh và bốn hướng di chuyển."""

    def __init__(
        self,
        name: str,
        detail: str,
        position: tuple[int, int],
        atk: int,
        side: str,
        image_path: str | None = None,
        artwork_path: str | None = None,
    ) -> None:
        self.name = name  # Tên hiển thị trên thẻ thông tin (khác theo phe).
        self.detail = detail  # Mô tả luật riêng, không phân biệt phe.
        self.position = position  # Tọa độ (cột, hàng) hiện tại trên bàn cờ.
        self.base_atk = atk  # Cấp sức mạnh gốc, dùng lại khi copy() hoặc hồi phục sau bẫy.
        self.atk = atk  # Cấp sức mạnh hiệu lực hiện tại (0 khi đứng trên bẫy đối phương).
        self.side = side  # Phe sở hữu quân: PlayerSide.DARK hoặc LIGHT.
        self.image = self._load_image(image_path, Size.CELL)  # Ảnh 1 ô, None nếu là bản sao AI.
        self.artwork = self._load_image(artwork_path, Size.ARTWORK)  # Ảnh minh họa lớn, None nếu là bản sao AI.

    @staticmethod
    def _load_image(path: str | None, size: tuple[int, int]):
        """Nạp và scale ảnh; bản sao dùng cho AI bỏ qua ảnh để tiết kiệm RAM."""

        return pygame.transform.scale(pygame.image.load(path), size) if path else None

    def copy(self):
        """Tạo bản sao không kèm tài nguyên đồ họa."""

        return Piece(self.name, self.detail, self.position, self.base_atk, self.side)

    def left(self, step: int, board):
        # Đi sang trái `step` ô; None nếu vượt biên trái bàn cờ (x < 0).
        x, y = self.position
        return None if x - step < 0 else board.get_cell((x - step, y))

    def right(self, step: int, board):
        # Đi sang phải `step` ô; None nếu vượt biên phải bàn cờ (x >= W).
        x, y = self.position
        return None if x + step >= common.W else board.get_cell((x + step, y))

    def up(self, step: int, board):
        # Đi lên `step` ô; None nếu vượt biên trên bàn cờ (y < 0).
        x, y = self.position
        return None if y - step < 0 else board.get_cell((x, y - step))

    def down(self, step: int, board):
        # Đi xuống `step` ô; None nếu vượt biên dưới bàn cờ (y >= H).
        x, y = self.position
        return None if y + step >= common.H else board.get_cell((x, y + step))

    def can_defeat(self, piece) -> bool:
        """Quân thường chỉ bắt được quân có cấp không lớn hơn mình."""

        # atk đã tính cả hiệu ứng bẫy (0 khi đứng trên bẫy đối phương) nên so
        # sánh trực tiếp là đủ, không cần biết piece đang ở bẫy hay không.
        return piece is None or self.atk >= piece.atk

    def is_valid_cell(self, cell) -> bool:
        """Kiểm tra luật chung: không vào sông/hang nhà và không đè quân cùng phe."""

        return (
            cell.is_in_board  # Ô phải nằm trong biên bàn cờ.
            and not cell.is_river  # Quân thường không được vào sông (Rat/Dog ghi đè bỏ điều kiện này).
            and not CellLabel.is_player_den(cell.label, self.side)  # Không được vào hang nhà mình.
            and not cell.is_occupied_own(self.side)  # Không được đè lên quân cùng phe.
            and (cell.piece is None or self.can_defeat(cell.piece))  # Ô trống hoặc bắt được quân địch đang đứng đó.
        )

    def available_cells(self, board) -> list:
        """Liệt kê các ô hợp lệ kề theo bốn hướng."""

        cells = []
        for direction in (self.left, self.right, self.up, self.down):
            # Quân thường chỉ đi được 1 ô mỗi hướng (khác RiverJumper nhảy xa).
            cell = direction(1, board)
            if cell and self.is_valid_cell(cell):
                cells.append(cell)

        # Luật chống lặp có thể cấm đúng một ô đích của quân hiện tại.
        if (
            board.forbidden_move
            and board.forbidden_move[0] == self.position
            and board.forbidden_cell in cells
        ):
            cells.remove(board.forbidden_cell)
        return cells

    def weaker_pieces_positions(self, board) -> list[tuple[int, int]]:
        """Trả về các mục tiêu mà quân có thể hướng đến khi tìm đường."""

        opponents = board.pieces_of[PlayerSide.opponent_of(self.side)]
        return [
            PlayerSide.opponent_den_position(self.side),  # Hang đối phương luôn là đích tiềm năng.
            *[piece.position for piece in opponents if piece.atk < self.atk],  # Quân địch yếu hơn có thể ăn được.
        ]

    @property
    def is_dark(self) -> bool:
        return PlayerSide.is_dark(self.side)

    @property
    def is_light(self) -> bool:
        return PlayerSide.is_light(self.side)


class RiverJumper(Piece):
    """Luật dùng chung cho Hổ và Sư tử khi nhảy qua sông.

    Chỉ override available_cells (dùng _jump_destination thay vì đi 1 ô) và
    thêm _jump_destination; is_valid_cell/can_defeat vẫn kế thừa từ Piece.
    """

    def available_cells(self, board) -> list:
        # Giống Piece.available_cells nhưng thay bước "đi 1 ô" bằng "nhảy sông".
        cells = []
        for direction in (self.left, self.right, self.up, self.down):
            destination = self._jump_destination(direction, board)
            if destination and self.is_valid_cell(destination):
                cells.append(destination)

        # Luật chống lặp giống hệt Piece.available_cells.
        if (
            board.forbidden_move
            and board.forbidden_move[0] == self.position
            and board.forbidden_cell in cells
        ):
            cells.remove(board.forbidden_cell)
        return cells

    @staticmethod
    def _jump_destination(direction, board):
        """Trả về bờ đối diện; Chuột trong sông sẽ chặn cú nhảy."""

        step = 1
        cell = direction(step, board)
        if not cell or not cell.is_river:
            # Ô kề không phải sông (hết bàn hoặc đất liền) -> không nhảy, trả nguyên ô đó.
            return cell

        while cell and cell.is_river:
            if cell.piece:
                # Có quân (Chuột hoặc Chó) đứng trong sông chặn đường -> không nhảy được.
                return None
            step += 1
            cell = direction(step, board)
        # Ra khỏi vòng lặp khi hết sông (đến bờ bên kia) hoặc hết bàn cờ (None).
        return cell
