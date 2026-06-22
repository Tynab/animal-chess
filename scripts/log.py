"""Thu thập và tuần tự hóa dữ liệu ván đấu sang CSV.

Mỗi lượt được giữ trong danh sách dict và chỉ dựng DataFrame khi cần ghi, tránh
``pandas.concat`` sau từng nước. Một file phiên trong ``data/`` nhận nhiều ván,
giúp chế độ máy-máy không tạo hàng nghìn file nhỏ.
"""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from scripts.bot import Bot
from scripts.common import DATA_DIR, PlayerSide


class Log:
    """Bộ ghi dữ liệu huấn luyện cho một phiên chạy game."""

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
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = self.output_dir / f"dark_{timestamp}.csv"
        self.new_df()

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
            header=not self.output_file.exists(),
            index=False,
        )
        self.new_df()
        return self.output_file

    @staticmethod
    def map_piece_name(piece) -> str:
        """Mã hóa loại quân; chữ thường là phe tối, chữ hoa là phe sáng."""

        symbol = {
            "rat": "r",
            "cat": "c",
            "dog": "d",
            "wolf": "w",
            "leopard": "p",
            "tiger": "t",
            "lion": "l",
            "elephant": "e",
        }.get(type(piece).__name__.lower(), "-")
        return symbol if piece.is_dark else symbol.upper()

    @staticmethod
    def side_to_enum(side: str | None) -> int:
        return 0 if side is None else 1 if PlayerSide.is_dark(side) else -1

    @staticmethod
    def enum_to_side(encoded: int) -> str | None:
        return (
            PlayerSide.DARK
            if encoded == 1
            else PlayerSide.LIGHT
            if encoded == -1
            else None
        )

    @staticmethod
    def enum_to_position(encoded: str) -> tuple[int, int]:
        return ord(encoded[0]) - ord("A"), int(encoded[1]) - 1

    # Giữ alias sai chính tả của phiên bản cũ để không phá notebook bên ngoài.
    enum_to_postion = enum_to_position

    @staticmethod
    def move_to_enum(move: tuple) -> str:
        start, end = move
        return (
            f"{chr(ord('A') + start[0])}{start[1] + 1}"
            f"{chr(ord('A') + end[0])}{end[1] + 1}"
        )

    @staticmethod
    def enum_to_move(encoded: str) -> tuple[tuple[int, int], tuple[int, int]]:
        return Log.enum_to_position(encoded[:2]), Log.enum_to_position(encoded[2:])

    @staticmethod
    def cell_piece_to_enum(cell) -> str:
        return Log.map_piece_name(cell.piece) if cell.piece else "-"

    @staticmethod
    def cell_trap_to_enum(cell) -> int:
        return -1 if cell.is_light_trap else 1 if cell.is_dark_trap else 0

    @staticmethod
    def cell_den_to_enum(cell) -> int:
        return -1 if cell.is_light_den else 1 if cell.is_dark_den else 0

    @staticmethod
    def cell_river_to_enum(cell) -> int:
        return int(cell.is_river)

    @staticmethod
    def board_to_enum(board) -> str:
        """Tuần tự hóa 63 ô theo thứ tự cột-major tương thích tập dữ liệu cũ."""

        return "".join(
            Log.cell_piece_to_enum(cell) for column in board.cells for cell in column
        )
