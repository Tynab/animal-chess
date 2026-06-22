"""Lớp quân cờ cơ sở và luật di chuyển dùng chung.

Mỗi quân cụ thể chỉ cần cung cấp metadata và ghi đè phần luật đặc biệt. Module
không phụ thuộc các lớp quân con nên tránh được vòng import với ``Cell``.
"""

import pygame

from scripts import common
from scripts.common import CellLabel, PlayerSide, Size


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
        self.name = name
        self.detail = detail
        self.position = position
        self.base_atk = atk
        self.atk = atk
        self.side = side
        self.image = self._load_image(image_path, Size.CELL)
        self.artwork = self._load_image(artwork_path, Size.ARTWORK)

    @staticmethod
    def _load_image(path: str | None, size: tuple[int, int]):
        """Nạp và scale ảnh; bản sao dùng cho AI bỏ qua ảnh để tiết kiệm RAM."""

        return pygame.transform.scale(pygame.image.load(path), size) if path else None

    def copy(self):
        """Tạo bản sao không kèm tài nguyên đồ họa."""

        return Piece(self.name, self.detail, self.position, self.base_atk, self.side)

    def left(self, step: int, board):
        x, y = self.position
        return None if x - step < 0 else board.get_cell((x - step, y))

    def right(self, step: int, board):
        x, y = self.position
        return None if x + step >= common.W else board.get_cell((x + step, y))

    def up(self, step: int, board):
        x, y = self.position
        return None if y - step < 0 else board.get_cell((x, y - step))

    def down(self, step: int, board):
        x, y = self.position
        return None if y + step >= common.H else board.get_cell((x, y + step))

    def can_defeat(self, piece) -> bool:
        """Quân thường chỉ bắt được quân có cấp không lớn hơn mình."""

        return piece is None or self.atk >= piece.atk

    def is_valid_cell(self, cell) -> bool:
        """Kiểm tra luật chung: không vào sông/hang nhà và không đè quân cùng phe."""

        return (
            cell.is_in_board
            and not cell.is_river
            and not CellLabel.is_player_den(cell.label, self.side)
            and not cell.is_occupied_own(self.side)
            and (cell.piece is None or self.can_defeat(cell.piece))
        )

    def available_cells(self, board) -> list:
        """Liệt kê các ô hợp lệ kề theo bốn hướng."""

        cells = []
        for direction in (self.left, self.right, self.up, self.down):
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
            PlayerSide.opponent_den_position(self.side),
            *[piece.position for piece in opponents if piece.atk < self.atk],
        ]

    @property
    def is_dark(self) -> bool:
        return PlayerSide.is_dark(self.side)

    @property
    def is_light(self) -> bool:
        return PlayerSide.is_light(self.side)


class RiverJumper(Piece):
    """Luật dùng chung cho Hổ và Sư tử khi nhảy qua sông."""

    def available_cells(self, board) -> list:
        cells = []
        for direction in (self.left, self.right, self.up, self.down):
            destination = self._jump_destination(direction, board)
            if destination and self.is_valid_cell(destination):
                cells.append(destination)

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
            return cell

        while cell and cell.is_river:
            if cell.piece:
                return None
            step += 1
            cell = direction(step, board)
        return cell
