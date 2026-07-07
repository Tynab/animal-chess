"""Thu thập và tuần tự hóa dữ liệu ván đấu sang CSV.

Mỗi lượt được giữ trong danh sách dict và chỉ dựng DataFrame khi cần ghi, tránh
``pandas.concat`` sau từng nước. Một file phiên trong ``data/`` nhận nhiều ván,
giúp chế độ máy-máy không tạo hàng nghìn file nhỏ.

Phần lớn nội dung file là các bộ chuyển đổi enum (``*_to_enum``/``enum_to_*``)
dùng để nén trạng thái ván cờ (bàn cờ, phe, nước đi, ô) thành số/chuỗi ngắn gọn
cho CSV, và giải mã ngược khi cần đọc lại. Các bộ chuyển đổi được nhóm theo chủ
đề: mã hóa phe, mã hóa quân cờ, mã hóa vị trí/nước đi, mã hóa ô/địa hình, mã
hóa toàn bàn cờ.
"""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from scripts.bot import Bot
from scripts.common import DATA_DIR, PlayerSide
from scripts.encoding import PIECE_SYMBOLS


class Log:
    """Bộ ghi dữ liệu huấn luyện cho một phiên chạy game.

    Mỗi ván tích lũy bản ghi (một dict mỗi nước đi) vào ``self.records``;
    ``save()`` nối toàn bộ ván vào một file CSV dùng chung cho cả phiên
    (``self.output_file``), rồi mở lại bộ đếm cho ván kế tiếp qua ``new_df()``.
    Schema cột (``COLUMNS``) và các hàm ``*_to_enum``/``enum_to_*`` bên dưới
    phải khớp với định dạng dữ liệu huấn luyện cũ để không phá vỡ các notebook/
    script đọc CSV đã có từ trước.
    """

    # Thứ tự cột CSV — phải khớp thứ tự key trong insert_chess_record():
    # id: mã ván | board: 63 ô tuần tự hóa | side: phe vừa đi | piece: quân tại
    # ô đích | atk: chỉ số tấn công quân | move: nước đi dạng "A1B2" |
    # river/trap/den: cờ địa hình tại ô đích | score: điểm đánh giá theo phe
    # tối | winner: phe thắng (nếu ván đã kết thúc).
    COLUMNS = (
        "id",
        "board",
        "side",
        "piece",
        "atk",
        "move",
        "river",
        "trap",
        "den",
        "score",
        "winner",
    )

    def __init__(self, output_dir: str | Path = DATA_DIR) -> None:
        """Tạo thư mục xuất (nếu chưa có) và mở một file CSV mới cho phiên này."""

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Tên file gắn timestamp để mỗi lần chạy chương trình có file riêng,
        # nhưng nhiều ván trong cùng một lần chạy sẽ được nối vào chung file.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = self.output_dir / f"dark_{timestamp}.csv"
        self.new_df()

    # ==================== Vòng đời ghi dữ liệu theo ván ====================

    def new_df(self) -> None:
        """Bắt đầu bộ bản ghi cho một ván mới."""

        self.id = str(uuid4())
        self.records: list[dict] = []

    @property
    def df(self) -> pd.DataFrame:
        """Cung cấp DataFrame tương thích API cũ khi cần kiểm tra dữ liệu."""

        return pd.DataFrame.from_records(self.records, columns=self.COLUMNS)

    def insert_chess_record(self, board, move: tuple) -> None:
        """Ghi trạng thái sau nước đi cùng điểm đánh giá từ phía phe tối."""

        # Ô đích của nước đi quyết định quân/địa hình cần mã hóa cho bản ghi.
        cell = board.get_cell(move[1])
        piece = cell.piece
        self.records.append(
            {
                "id": self.id,
                "board": self.board_to_enum(board),
                "side": self.side_to_enum(piece.side),
                "piece": self.cell_piece_to_enum(cell),
                "atk": piece.atk,
                "move": self.move_to_enum(move),
                "river": self.cell_river_to_enum(cell),
                "trap": self.cell_trap_to_enum(cell),
                "den": self.cell_den_to_enum(cell),
                # Điểm luôn theo góc nhìn phe tối để nhãn huấn luyện nhất quán,
                # bất kể phe nào vừa đi.
                "score": Bot.evaluate_position(board, PlayerSide.DARK),
                "winner": self.side_to_enum(board.winner),
            }
        )

    def save(self) -> Path | None:
        """Nối ván hiện tại vào file phiên và trả về đường dẫn đã ghi."""

        if not self.records:
            return None
        frame = self.df
        frame.to_csv(
            self.output_file,
            mode="a",
            # Chỉ ghi header nếu file phiên chưa tồn tại (ván đầu tiên).
            header=not self.output_file.exists(),
            index=False,
        )
        self.new_df()
        return self.output_file

    # ==================== Mã hóa phe (side) ====================

    @staticmethod
    def side_to_enum(side: str | None) -> int:
        """Mã hóa phe: 1 = phe tối, -1 = phe sáng, 0 = không xác định."""

        return 0 if side is None else 1 if PlayerSide.is_dark(side) else -1

    @staticmethod
    def enum_to_side(encoded: int) -> str | None:
        """Giải mã ngược của ``side_to_enum``: 1/-1/0 → phe tối/sáng/None."""

        return (
            PlayerSide.DARK
            if encoded == 1
            else PlayerSide.LIGHT
            if encoded == -1
            else None
        )

    # ==================== Mã hóa quân cờ (piece) ====================

    @staticmethod
    def map_piece_name(piece) -> str:
        """Mã hóa loại quân; chữ thường là phe tối, chữ hoa là phe sáng."""

        symbol = PIECE_SYMBOLS.get(type(piece).__name__.lower(), "-")
        return symbol if piece.is_dark else symbol.upper()

    @staticmethod
    def cell_piece_to_enum(cell) -> str:
        """Mã hóa quân tại ô; trả về "-" nếu ô trống."""

        return Log.map_piece_name(cell.piece) if cell.piece else "-"

    # ==================== Mã hóa vị trí & nước đi (move) ====================

    @staticmethod
    def enum_to_position(encoded: str) -> tuple[int, int]:
        """Giải mã tọa độ dạng "A1" (chữ cột + số hàng) thành (cột, hàng) 0-based."""

        return ord(encoded[0]) - ord("A"), int(encoded[1]) - 1

    # Giữ alias sai chính tả của phiên bản cũ để không phá notebook bên ngoài.
    enum_to_postion = enum_to_position

    @staticmethod
    def move_to_enum(move: tuple) -> str:
        """Mã hóa nước đi (start, end) thành chuỗi 4 ký tự dạng "A1B2"."""

        start, end = move
        return (
            f"{chr(ord('A') + start[0])}{start[1] + 1}"
            f"{chr(ord('A') + end[0])}{end[1] + 1}"
        )

    @staticmethod
    def enum_to_move(encoded: str) -> tuple[tuple[int, int], tuple[int, int]]:
        """Giải mã chuỗi nước đi "A1B2" thành cặp tọa độ (điểm đi, điểm đến)."""

        return Log.enum_to_position(encoded[:2]), Log.enum_to_position(encoded[2:])

    # ==================== Mã hóa ô / địa hình (cell terrain) ====================

    @staticmethod
    def cell_trap_to_enum(cell) -> int:
        """Mã hóa bẫy tại ô: -1 bẫy phe sáng, 1 bẫy phe tối, 0 không phải bẫy."""

        return -1 if cell.is_light_trap else 1 if cell.is_dark_trap else 0

    @staticmethod
    def cell_den_to_enum(cell) -> int:
        """Mã hóa hang/tổ tại ô: -1 hang phe sáng, 1 hang phe tối, 0 không phải."""

        return -1 if cell.is_light_den else 1 if cell.is_dark_den else 0

    @staticmethod
    def cell_river_to_enum(cell) -> int:
        """Mã hóa ô sông: 1 nếu là ô sông, 0 nếu không."""

        return int(cell.is_river)

    # ==================== Mã hóa toàn bàn cờ (board) ====================

    @staticmethod
    def board_to_enum(board) -> str:
        """Tuần tự hóa 63 ô theo thứ tự cột-major tương thích tập dữ liệu cũ."""

        return "".join(
            Log.cell_piece_to_enum(cell) for column in board.cells for cell in column
        )
