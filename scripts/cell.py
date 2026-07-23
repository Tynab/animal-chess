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
        """Tạo ô trống (chưa có quân, chưa nạp ảnh) tại `position` với địa hình `label`."""

        self.label = label
        self.position = position
        self.image = None
        self.piece = None

    def copy(self):
        """Sao chép trạng thái logic, không sao chép ảnh nền.

        Không copy ``self.image`` (surface Pygame) vì bản sao chỉ phục vụ tìm
        kiếm nước đi trong bộ nhớ (xem ``Board.copy``), không bao giờ được vẽ
        lên màn hình nên giữ ảnh chỉ tốn RAM vô ích. Nếu ô có quân, quân cũng
        được nhân bản qua ``piece.copy()`` rồi đặt lại bằng ``add_piece`` để
        ``atk`` được tính lại đúng theo địa hình của ô mới (cùng label nên kết
        quả giống hệt ô gốc).
        """

        copied = Cell(self.label, self.position)
        if self.piece:
            copied.add_piece(self.piece.copy())
        return copied

    def set_image(self, image_path: str) -> None:
        """Nạp và co giãn ảnh nền của ô về đúng kích thước một ô (Size.CELL)."""

        self.image = pygame.transform.scale(pygame.image.load(image_path), Size.CELL)

    def add_piece(self, piece) -> None:
        """Đặt quân vào ô và áp dụng trạng thái mất sức mạnh khi sa bẫy địch.

        Bẫy của phe nào chỉ triệt sức quân đối phương: nếu ô này là bẫy của
        ĐỐI PHƯƠNG so với phe của quân (``CellLabel.is_opponent_trap``), quân
        mất hoàn toàn sức tấn công (``atk = 0``, kể cả Voi cũng có thể bị bắt
        lúc này); ngược lại (ô trống, sông, hay bẫy của chính phe mình) quân
        giữ nguyên sức mạnh gốc ``base_atk``. ``base_atk`` không bao giờ bị
        ghi đè nên khi quân rời bẫy sang ô khác, lần ``add_piece`` kế tiếp tự
        tính lại ``atk`` đúng theo địa hình mới — quân tự phục hồi sức mạnh mà
        không cần logic "thoát bẫy" riêng.
        """

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
        """Kiểm tra ô đang có quân của đúng phe `side` hay không (dùng để phát hiện hang bị chiếm)."""

        return bool(self.piece and self.piece.side == side)

    @property
    def is_in_board(self) -> bool:
        """Toạ độ của ô có nằm trong biên bàn cờ W x H hay không."""

        x, y = self.position
        return 0 <= x < common.W and 0 <= y < common.H

    @property
    def is_river(self) -> bool:
        """Ô có phải địa hình sông hay không (chỉ Chuột/Chó qua được, Hổ/Sư nhảy qua)."""

        return CellLabel.is_river(self.label)

    @property
    def is_dark_trap(self) -> bool:
        """Ô có phải bẫy thuộc lãnh thổ phe tối hay không (triệt sức quân sáng đứng lên)."""

        return CellLabel.is_dark_trap(self.label)

    @property
    def is_light_trap(self) -> bool:
        """Ô có phải bẫy thuộc lãnh thổ phe sáng hay không (triệt sức quân tối đứng lên)."""

        return CellLabel.is_light_trap(self.label)

    @property
    def is_trap(self) -> bool:
        """Ô có phải bẫy (của bất kỳ phe nào) hay không."""

        return CellLabel.is_trap(self.label)

    @property
    def is_dark_den(self) -> bool:
        """Ô có phải hang của phe tối hay không (quân sáng lọt vào đây là thắng)."""

        return CellLabel.is_dark_den(self.label)

    @property
    def is_light_den(self) -> bool:
        """Ô có phải hang của phe sáng hay không (quân tối lọt vào đây là thắng)."""

        return CellLabel.is_light_den(self.label)

    @property
    def is_den(self) -> bool:
        """Ô có phải hang (của bất kỳ phe nào) hay không."""

        return CellLabel.is_den(self.label)
