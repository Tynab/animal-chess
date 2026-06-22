"""Trạng thái bàn cờ và các thao tác di chuyển có thể hoàn tác.

``Board`` là nguồn dữ liệu duy nhất cho quân, lịch sử và luật thắng. Cặp
``make_move``/``undo_move`` được thiết kế đối xứng để minimax có thể duyệt nhiều
nhánh mà không làm thay đổi trạng thái ban đầu.
"""

from scripts import common
from scripts.cell import Cell
from scripts.common import CellImage, CellLabel, CellPosition, PlayerSide
from scripts.pieces.cat import Cat
from scripts.pieces.dog import Dog
from scripts.pieces.elephant import Elephant
from scripts.pieces.leopard import Leopard
from scripts.pieces.lion import Lion
from scripts.pieces.rat import Rat
from scripts.pieces.tiger import Tiger
from scripts.pieces.wolf import Wolf


class Board:
    """Bàn cờ 7x9, bao gồm địa hình, quân và lịch sử nước đi."""

    PIECE_TYPES = (Rat, Cat, Dog, Wolf, Leopard, Tiger, Lion, Elephant)

    def __init__(self, with_pieces: bool = True, is_copy: bool = False) -> None:
        self.cells = [
            [Cell(CellLabel.EMPTY, (x, y)) for y in range(common.H)]
            for x in range(common.W)
        ]
        self._set_up_terrain(load_images=not is_copy)
        if with_pieces:
            self._set_up_pieces(load_images=not is_copy)

        self.move_history: list[tuple[tuple[int, int], tuple[int, int]]] = []
        # Mỗi nước đều có một bản ghi (quân bị bắt hoặc None) để undo luôn đối xứng.
        self.captured_pieces: list[tuple[object | None, tuple[int, int]]] = []
        self.forbidden_move = None
        self.update_pieces()

    def _set_up_terrain(self, load_images: bool) -> None:
        """Gắn nhãn và tùy chọn nạp ảnh cho sông, bẫy, hang."""

        for position in CellPosition.RIVERS:
            self.get_cell(position).label = CellLabel.RIVER
        for position in CellPosition.DARK_TRAPS:
            self.get_cell(position).label = CellLabel.DARK_TRAP
        for position in CellPosition.LIGHT_TRAPS:
            self.get_cell(position).label = CellLabel.LIGHT_TRAP
        self.get_cell(CellPosition.DARK_DEN).label = CellLabel.DARK_DEN
        self.get_cell(CellPosition.LIGHT_DEN).label = CellLabel.LIGHT_DEN

        if not load_images:
            return
        for position, image_path in zip(CellPosition.RIVERS, CellImage.RIVERS):
            self.get_cell(position).set_image(image_path)
        for position in (*CellPosition.DARK_TRAPS, *CellPosition.LIGHT_TRAPS):
            self.get_cell(position).set_image(CellImage.TRAP)
        for position in (CellPosition.DARK_DEN, CellPosition.LIGHT_DEN):
            self.get_cell(position).set_image(CellImage.DEN)

    def _set_up_pieces(self, load_images: bool) -> None:
        """Đặt đủ tám quân của mỗi phe vào vị trí xuất phát."""

        for side in (PlayerSide.DARK, PlayerSide.LIGHT):
            for piece_type in self.PIECE_TYPES:
                piece = piece_type(side, is_copy=not load_images)
                self.get_cell(piece.position).add_piece(piece)

    def copy(self):
        """Tạo bản sao logic độc lập, nhẹ hơn vì không giữ surface Pygame."""

        copied = Board(with_pieces=False, is_copy=True)
        copied.cells = [[cell.copy() for cell in column] for column in self.cells]
        copied.move_history = self.move_history.copy()
        copied.captured_pieces = [
            (piece.copy() if piece else None, position)
            for piece, position in self.captured_pieces
        ]
        copied.forbidden_move = self.forbidden_move
        copied.update_pieces()
        return copied

    def get_cell(self, position: tuple[int, int]) -> Cell:
        x, y = position
        return self.cells[x][y]

    def get_valid_moves(self, side: str) -> list[tuple]:
        """Sinh toàn bộ nước hợp lệ của một phe."""

        return [
            (piece.position, cell.position)
            for piece in self.pieces_of[side]
            for cell in piece.available_cells(self)
            if (piece.position, cell.position) != self.forbidden_move
        ]

    def get_forbidden(self):
        """Phát hiện một nước lặp lại ba lần theo chu kỳ bốn ply."""

        repeated = self.move_history[-4:-13:-4]
        return repeated[0] if len(repeated) == 3 and len(set(repeated)) == 1 else None

    def make_move(self, move: tuple[tuple[int, int], tuple[int, int]]) -> None:
        """Áp dụng nước đi và lưu đủ dữ liệu để hoàn tác chính xác."""

        source_cell = self.get_cell(move[0])
        target_cell = self.get_cell(move[1])
        if source_cell.piece is None:
            raise ValueError(f"Ô nguồn {move[0]} không có quân.")

        captured = target_cell.remove_piece() if target_cell.piece else None
        self.captured_pieces.append((captured, move[1]))
        target_cell.add_piece(source_cell.remove_piece())
        self.move_history.append(move)
        self.forbidden_move = self.get_forbidden()
        self.update_pieces()

    def undo_move(self, move: tuple[tuple[int, int], tuple[int, int]]) -> None:
        """Hoàn tác đúng nước vừa đi, kể cả quân bị bắt và nước cấm."""

        if not self.move_history or self.move_history[-1] != move:
            raise ValueError("Chỉ có thể hoàn tác nước đi mới nhất.")

        source_cell = self.get_cell(move[0])
        target_cell = self.get_cell(move[1])
        source_cell.add_piece(target_cell.remove_piece())
        captured, captured_position = self.captured_pieces.pop()
        if captured_position != move[1]:
            raise RuntimeError("Ngăn xếp quân bị bắt không đồng bộ với lịch sử.")
        if captured:
            target_cell.add_piece(captured)

        self.move_history.pop()
        self.forbidden_move = self.get_forbidden()
        self.update_pieces()

    def update_pieces(self) -> None:
        """Tái tạo các chỉ mục quân sau mỗi thay đổi bàn cờ."""

        self.pieces = [
            cell.piece for column in self.cells for cell in column if cell.piece
        ]
        self.pieces_of = {
            side: [piece for piece in self.pieces if piece.side == side]
            for side in (PlayerSide.DARK, PlayerSide.LIGHT)
        }

    def is_opponent_pieceless(self, side: str) -> bool:
        return not self.pieces_of[side]

    def is_opponent_den_invaded(self, side: str) -> bool:
        den = self.get_cell(PlayerSide.opponent_den_position(side))
        return den.is_occupied_own(side)

    @property
    def forbidden_cell(self):
        return self.get_cell(self.forbidden_move[1]) if self.forbidden_move else None

    def _side_has_won(self, side: str) -> bool:
        opponent = PlayerSide.opponent_of(side)
        return (
            self.is_opponent_den_invaded(side)
            or self.is_opponent_pieceless(opponent)
            or not self.get_valid_moves(opponent)
        )

    @property
    def is_dark_win(self) -> bool:
        return self._side_has_won(PlayerSide.DARK)

    @property
    def is_light_win(self) -> bool:
        return self._side_has_won(PlayerSide.LIGHT)

    @property
    def is_game_over(self) -> bool:
        return self.is_dark_win or self.is_light_win

    @property
    def winner(self):
        if self.is_dark_win:
            return PlayerSide.DARK
        if self.is_light_win:
            return PlayerSide.LIGHT
        return None
