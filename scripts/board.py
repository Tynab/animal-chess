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

    # Tám loại quân duyệt qua khi dựng bàn mới (_set_up_pieces); thứ tự liệt
    # kê ở đây không ảnh hưởng luật, chỉ cần đủ tám loại cho mỗi phe.
    PIECE_TYPES = (Rat, Cat, Dog, Wolf, Leopard, Tiger, Lion, Elephant)

    def __init__(self, with_pieces: bool = True, is_copy: bool = False) -> None:
        # with_pieces=False: dựng bàn trống địa hình thuần (dùng nội bộ bởi
        # copy() rồi tự gán lại self.cells, tránh dựng quân hai lần).
        # is_copy=True: không nạp ảnh Pygame cho ô/quân -> bàn "logic" nhẹ
        # hơn, dùng cho các bản sao chỉ phục vụ tìm kiếm nước đi (minimax/AI),
        # không bao giờ được vẽ lên màn hình.
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
        """Tạo bản sao logic độc lập, nhẹ hơn vì không giữ surface Pygame.

        ``is_copy=True`` khiến ``__init__`` bỏ qua toàn bộ nạp ảnh terrain/
        quân (xem ``_set_up_terrain``/``_set_up_pieces``); mỗi ``cell.copy()``
        cũng không sao chép ``Cell.image``. Nhờ vậy bản sao rẻ để tạo hàng
        loạt trong minimax/alpha-beta hay khi AI thử từng nước ứng viên, mà
        vẫn giữ đủ dữ liệu logic (lịch sử nước đi, quân bị bắt, nước cấm) để
        ``make_move``/``undo_move``/``get_valid_moves`` hoạt động y hệt bàn
        thật.
        """

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
        """Tra ô tại toạ độ (x, y); không kiểm tra biên (gọi is_in_board trước nếu cần)."""

        x, y = position
        return self.cells[x][y]

    def get_valid_moves(self, side: str) -> list[tuple]:
        """Sinh toàn bộ nước hợp lệ của một phe.

        Gộp nước đi khả dĩ của từng quân (``piece.available_cells``, luật
        riêng theo loài) rồi lọc bỏ đúng một nước trùng ``self.forbidden_move``
        (nước cấm lặp 3 lần liên tiếp, xem ``get_forbidden``); các nước còn
        lại của cùng quân đó tới cùng ô đích khác vẫn hợp lệ bình thường.
        """

        return [
            (piece.position, cell.position)
            for piece in self.pieces_of[side]
            for cell in piece.available_cells(self)
            if (piece.position, cell.position) != self.forbidden_move
        ]

    def get_forbidden(self):
        """Phát hiện một nước lặp lại ba lần theo chu kỳ bốn ply.

        Luật chống lặp: một cặp (nước của mình, nước đáp trả của đối phương)
        không được diễn ra ba lần liên tiếp giống hệt nhau, vì mỗi lần "mình"
        đi lại đúng nước đó cách nhau đúng 4 ply (mình - đối - mình - đối).
        ``move_history[-4:-13:-4]`` lấy tối đa 3 phần tử ở các vị trí -4, -8,
        -12 (bước nhảy -4, dừng trước -13) — tức đúng những lần "mình" đã đi
        ở 3 lượt gần nhất của riêng phe này. Nếu cả 3 giống nhau
        (``len(set(...)) == 1``) thì nước đó bị cấm lặp lại lần thứ tư; nước
        bị cấm luôn được exclude khỏi ``get_valid_moves`` cho tới khi lịch sử
        thay đổi (một nước khác được đi) khiến hàm này trả None trở lại.
        """

        repeated = self.move_history[-4:-13:-4]
        return repeated[0] if len(repeated) == 3 and len(set(repeated)) == 1 else None

    def make_move(self, move: tuple[tuple[int, int], tuple[int, int]]) -> None:
        """Áp dụng nước đi và lưu đủ dữ liệu để hoàn tác chính xác.

        Đối xứng có chủ ý với ``undo_move``: mọi thứ bị thay đổi ở đây
        (``captured_pieces``, ``move_history``, ``forbidden_move``,
        ``pieces``/``pieces_of`` qua ``update_pieces``) đều được ``undo_move``
        đảo ngược đúng thứ tự ngược lại, để minimax/alpha-beta có thể
        make/undo hàng loạt nước ứng viên trên cùng một bàn mà không cần
        ``copy()`` cho mỗi bước thử.
        """

        source_cell = self.get_cell(move[0])
        target_cell = self.get_cell(move[1])
        if source_cell.piece is None:
            raise ValueError(f"Ô nguồn {move[0]} không có quân.")

        # Luôn push một bản ghi vào captured_pieces dù ô đích trống (None) —
        # captured_pieces và move_history nhờ vậy luôn cùng độ dài và cùng
        # chỉ số, để undo_move có thể pop() cả hai theo cặp mà không lệch nhịp.
        captured = target_cell.remove_piece() if target_cell.piece else None
        self.captured_pieces.append((captured, move[1]))
        target_cell.add_piece(source_cell.remove_piece())
        self.move_history.append(move)
        self.forbidden_move = self.get_forbidden()
        self.update_pieces()

    def undo_move(self, move: tuple[tuple[int, int], tuple[int, int]]) -> None:
        """Hoàn tác đúng nước vừa đi, kể cả quân bị bắt và nước cấm.

        Chỉ cho phép hoàn tác nước ở đỉnh ``move_history`` (undo theo ngăn
        xếp, không undo tuỳ ý giữa chừng) để đảm bảo tính đối xứng với
        ``make_move``.
        """

        if not self.move_history or self.move_history[-1] != move:
            raise ValueError("Chỉ có thể hoàn tác nước đi mới nhất.")

        source_cell = self.get_cell(move[0])
        target_cell = self.get_cell(move[1])
        source_cell.add_piece(target_cell.remove_piece())
        captured, captured_position = self.captured_pieces.pop()
        # Vì make_move luôn push captured_pieces cùng lúc với move_history
        # (xem ghi chú ở make_move), vị trí vừa pop PHẢI trùng move[1]; sai
        # lệch ở đây nghĩa là hai danh sách đã bị thao túng ngoài cặp
        # make_move/undo_move (lỗi lập trình nghiêm trọng), nên raise thay vì
        # âm thầm phục hồi sai quân.
        if captured_position != move[1]:
            raise RuntimeError("Ngăn xếp quân bị bắt không đồng bộ với lịch sử.")
        if captured:
            target_cell.add_piece(captured)

        self.move_history.pop()
        self.forbidden_move = self.get_forbidden()
        self.update_pieces()

    def update_pieces(self) -> None:
        """Tái tạo các chỉ mục quân sau mỗi thay đổi bàn cờ.

        Duyệt ``self.cells`` theo đúng thứ tự lồng vòng lặp trong ``__init__``
        (ngoài theo cột x, trong theo hàng y) nên ``self.pieces`` liệt kê quân
        theo thứ tự cột-trước (column-major); thứ tự này không ảnh hưởng luật
        (chỉ dùng để lặp qua quân) nhưng được giữ ổn định để kết quả
        ``get_valid_moves``/serialize bàn cờ (``Log.board_to_enum``) không phụ
        thuộc thứ tự duyệt dict/list ngẫu nhiên.
        """

        self.pieces = [
            cell.piece for column in self.cells for cell in column if cell.piece
        ]
        self.pieces_of = {
            side: [piece for piece in self.pieces if piece.side == side]
            for side in (PlayerSide.DARK, PlayerSide.LIGHT)
        }

    def is_opponent_pieceless(self, side: str) -> bool:
        """Kiểm tra phe `side` đã bị bắt sạch quân hay chưa (điều kiện thắng cho đối thủ)."""

        return not self.pieces_of[side]

    def is_opponent_den_invaded(self, side: str) -> bool:
        """Kiểm tra phe `side` đã có quân đứng trong hang đối phương hay chưa."""

        den = self.get_cell(PlayerSide.opponent_den_position(side))
        return den.is_occupied_own(side)

    @property
    def forbidden_cell(self):
        """Ô đích của nước đang bị cấm lặp (None nếu hiện không có nước nào bị cấm)."""

        return self.get_cell(self.forbidden_move[1]) if self.forbidden_move else None

    def _side_has_won(self, side: str) -> bool:
        """Ba điều kiện thắng độc lập, chỉ cần một điều kiện đúng là đủ:
        (1) `side` đã đưa quân vào hang đối phương, (2) đối phương hết sạch
        quân, hoặc (3) đối phương không còn nước đi hợp lệ nào (bị chiếu bí/
        kẹt hoàn toàn) ở chính lượt của họ.
        """

        opponent = PlayerSide.opponent_of(side)
        return (
            self.is_opponent_den_invaded(side)
            or self.is_opponent_pieceless(opponent)
            or not self.get_valid_moves(opponent)
        )

    @property
    def is_dark_win(self) -> bool:
        """True nếu phe tối đã thắng theo một trong ba điều kiện ở _side_has_won."""

        return self._side_has_won(PlayerSide.DARK)

    @property
    def is_light_win(self) -> bool:
        """True nếu phe sáng đã thắng theo một trong ba điều kiện ở _side_has_won."""

        return self._side_has_won(PlayerSide.LIGHT)

    @property
    def is_game_over(self) -> bool:
        """True nếu ván đấu đã kết thúc (có phe thắng, bất kể phe nào)."""

        return self.is_dark_win or self.is_light_win

    @property
    def winner(self):
        """Phe thắng cuộc (PlayerSide.DARK/LIGHT), hoặc None nếu chưa/không phân thắng bại."""

        if self.is_dark_win:
            return PlayerSide.DARK
        if self.is_light_win:
            return PlayerSide.LIGHT
        return None
