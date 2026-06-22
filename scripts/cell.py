"""Mô hình một ô trên bàn cờ.

Ô chịu trách nhiệm đồng bộ vị trí của quân và hiệu lực bẫy. Sức mạnh gốc nằm
trên ``Piece.base_atk`` nên module này không cần import tám lớp quân cụ thể.
"""

import pygame

from scripts import common
from scripts.common import CellLabel, Size


class Cell:
    """Một ô địa hình có thể chứa tối đa một quân cờ."""

    def __init__(self, label: int, position: tuple[int, int]) -> None:
        self.label = label
        self.position = position
        self.image = None
        self.piece = None

    def copy(self):
        """Sao chép trạng thái logic, không sao chép ảnh nền."""

        copied = Cell(self.label, self.position)
        if self.piece:
            copied.add_piece(self.piece.copy())
        return copied

    def set_image(self, image_path: str) -> None:
        self.image = pygame.transform.scale(pygame.image.load(image_path), Size.CELL)

    def add_piece(self, piece) -> None:
        """Đặt quân vào ô và áp dụng trạng thái mất sức mạnh khi sa bẫy địch."""

        if piece is None:
            raise ValueError("Không thể đặt quân rỗng vào ô.")
        self.piece = piece
        piece.position = self.position
        piece.atk = (
            0 if CellLabel.is_opponent_trap(self.label, piece.side) else piece.base_atk
        )

    def remove_piece(self):
        """Lấy quân khỏi ô và trả về quân vừa lấy."""

        piece, self.piece = self.piece, None
        return piece

    def is_occupied_own(self, side: str) -> bool:
        return bool(self.piece and self.piece.side == side)

    @property
    def is_in_board(self) -> bool:
        x, y = self.position
        return 0 <= x < common.W and 0 <= y < common.H

    @property
    def is_river(self) -> bool:
        return CellLabel.is_river(self.label)

    @property
    def is_dark_trap(self) -> bool:
        return CellLabel.is_dark_trap(self.label)

    @property
    def is_light_trap(self) -> bool:
        return CellLabel.is_light_trap(self.label)

    @property
    def is_trap(self) -> bool:
        return CellLabel.is_trap(self.label)

    @property
    def is_dark_den(self) -> bool:
        return CellLabel.is_dark_den(self.label)

    @property
    def is_light_den(self) -> bool:
        return CellLabel.is_light_den(self.label)

    @property
    def is_den(self) -> bool:
        return CellLabel.is_den(self.label)
