"""Hằng số và ánh xạ dùng chung của Animal Chess.

Module gom cấu hình bàn cờ, trạng thái, tài nguyên và thông tin quân cờ vào một
nơi duy nhất. Các lớp giữ API cũ để những module game không phải biết cách tài
nguyên được tổ chức trên đĩa.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"
BEST_MODEL_PATH = MODEL_DIR / "best_model.h5"

W = 7
H = 9
FPS = 60
TIT = "Animal Chess"
SPAN = 100


def _asset_path(*parts: str) -> str:
    """Trả về đường dẫn tuyệt đối để game chạy được từ mọi thư mục hiện hành."""

    return str(PROJECT_ROOT.joinpath("assets", *parts))


def _select_by_side(side: str, dark_value, light_value):
    """Chọn giá trị tương ứng với phe tối hoặc phe sáng."""

    return dark_value if PlayerSide.is_dark(side) else light_value


class Size:
    """Kích thước cửa sổ, bàn cờ và các thành phần giao diện."""

    BOARD = (W * SPAN, H * SPAN)
    SUBSCREEN = (500, BOARD[1])
    TOTAL = (BOARD[0] + SUBSCREEN[0], BOARD[1])
    CELL = (SPAN, SPAN)
    ARTWORK = (480, 480)
    START_BTN = (190, 50)
    PADDING = (10, 10)


class ImagePath:
    """Đường dẫn ảnh nền của giao diện."""

    COVER = _asset_path("images", "cover.png")
    START_BTN = _asset_path("images", "button.png")
    GUIDE = _asset_path("images", "guide.png")
    CARD = _asset_path("images", "card.png")


class FontName:
    """Tên font ưu tiên; Pygame sẽ tự chọn font thay thế khi máy không có font."""

    TIT = "Garamond"
    BTN = "Lato"
    TXT = "Arial"


class Color:
    """Bảng màu RGB dùng khi render."""

    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    ORANGE = (255, 165, 0)
    YELLOW = (255, 255, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    PINK = (255, 192, 203)
    PURPLE = (128, 0, 128)
    CYAN = (0, 255, 255)
    GREY = (128, 128, 128)

    @staticmethod
    def star_color(side: str) -> tuple[int, int, int]:
        """Trả về màu đánh dấu quân theo phe."""

        return Color.ORANGE if PlayerSide.is_dark(side) else Color.CYAN


class GameMode:
    """Các chế độ người-người, người-máy và máy-máy."""

    PvP = 1
    PvC = 2
    CvC = 3

    @staticmethod
    def is_pvp(mode: int) -> bool:
        return mode == GameMode.PvP

    @staticmethod
    def is_pvc(mode: int) -> bool:
        return mode == GameMode.PvC

    @staticmethod
    def is_cvc(mode: int) -> bool:
        return mode == GameMode.CvC


class GameState:
    """Vòng đời của một ván chơi."""

    NEW = 1
    RUNNING = 2
    OVER = 3

    @staticmethod
    def is_new(state: int) -> bool:
        return state == GameState.NEW

    @staticmethod
    def is_running(state: int) -> bool:
        return state == GameState.RUNNING

    @staticmethod
    def is_over(state: int) -> bool:
        return state == GameState.OVER


class PlayerSide:
    """Định danh hai phe và các phép chuyển đổi liên quan."""

    DARK = "Dark"
    LIGHT = "Light"

    @staticmethod
    def is_dark(side: str) -> bool:
        return side == PlayerSide.DARK

    @staticmethod
    def is_light(side: str) -> bool:
        return side == PlayerSide.LIGHT

    @staticmethod
    def player_den_position(side: str) -> tuple[int, int]:
        return _select_by_side(side, CellPosition.DARK_DEN, CellPosition.LIGHT_DEN)

    @staticmethod
    def opponent_den_position(side: str) -> tuple[int, int]:
        return _select_by_side(side, CellPosition.LIGHT_DEN, CellPosition.DARK_DEN)

    @staticmethod
    def player_of(side: str) -> str:
        return side

    @staticmethod
    def opponent_of(side: str) -> str:
        return PlayerSide.LIGHT if PlayerSide.is_dark(side) else PlayerSide.DARK


class CellLabel:
    """Loại địa hình của một ô và các hàm kiểm tra theo phe."""

    EMPTY = 1
    RIVER = 2
    DARK_TRAP = 3
    LIGHT_TRAP = 4
    DARK_DEN = 5
    LIGHT_DEN = 6

    @staticmethod
    def is_empty(label: int) -> bool:
        return label == CellLabel.EMPTY

    @staticmethod
    def is_river(label: int) -> bool:
        return label == CellLabel.RIVER

    @staticmethod
    def is_dark_trap(label: int) -> bool:
        return label == CellLabel.DARK_TRAP

    @staticmethod
    def is_light_trap(label: int) -> bool:
        return label == CellLabel.LIGHT_TRAP

    @staticmethod
    def is_trap(label: int) -> bool:
        return label in (CellLabel.DARK_TRAP, CellLabel.LIGHT_TRAP)

    @staticmethod
    def is_player_trap(label: int, side: str) -> bool:
        return label == _select_by_side(side, CellLabel.DARK_TRAP, CellLabel.LIGHT_TRAP)

    @staticmethod
    def is_opponent_trap(label: int, side: str) -> bool:
        return label == _select_by_side(side, CellLabel.LIGHT_TRAP, CellLabel.DARK_TRAP)

    @staticmethod
    def is_dark_den(label: int) -> bool:
        return label == CellLabel.DARK_DEN

    @staticmethod
    def is_light_den(label: int) -> bool:
        return label == CellLabel.LIGHT_DEN

    @staticmethod
    def is_den(label: int) -> bool:
        return label in (CellLabel.DARK_DEN, CellLabel.LIGHT_DEN)

    @staticmethod
    def is_player_den(label: int, side: str) -> bool:
        return label == _select_by_side(side, CellLabel.DARK_DEN, CellLabel.LIGHT_DEN)

    @staticmethod
    def is_opponent_den(label: int, side: str) -> bool:
        return label == _select_by_side(side, CellLabel.LIGHT_DEN, CellLabel.DARK_DEN)


class CellPosition:
    """Tọa độ địa hình và vị trí xuất phát của các quân."""

    RIVER_1_1 = (1, 3)
    RIVER_1_2 = (2, 3)
    RIVER_1_3 = (1, 4)
    RIVER_1_4 = (2, 4)
    RIVER_1_5 = (1, 5)
    RIVER_1_6 = (2, 5)
    RIVER_2_1 = (4, 3)
    RIVER_2_2 = (5, 3)
    RIVER_2_3 = (4, 4)
    RIVER_2_4 = (5, 4)
    RIVER_2_5 = (4, 5)
    RIVER_2_6 = (5, 5)
    DARK_TRAP_1 = (3, 1)
    DARK_TRAP_2 = (2, 0)
    DARK_TRAP_3 = (4, 0)
    LIGHT_TRAP_1 = (3, 7)
    LIGHT_TRAP_2 = (2, 8)
    LIGHT_TRAP_3 = (4, 8)
    DARK_DEN = (3, 0)
    LIGHT_DEN = (3, 8)
    DARK_RAT = (0, 2)
    DARK_CAT = (5, 1)
    DARK_DOG = (1, 1)
    DARK_WOLF = (4, 2)
    DARK_LEOPARD = (2, 2)
    DARK_TIGER = (6, 0)
    DARK_LION = (0, 0)
    DARK_ELEPHANT = (6, 2)
    LIGHT_RAT = (6, 6)
    LIGHT_CAT = (1, 7)
    LIGHT_DOG = (5, 7)
    LIGHT_WOLF = (2, 6)
    LIGHT_LEOPARD = (4, 6)
    LIGHT_TIGER = (0, 8)
    LIGHT_LION = (6, 8)
    LIGHT_ELEPHANT = (0, 6)

    RIVERS = (
        RIVER_1_1,
        RIVER_1_2,
        RIVER_1_3,
        RIVER_1_4,
        RIVER_1_5,
        RIVER_1_6,
        RIVER_2_1,
        RIVER_2_2,
        RIVER_2_3,
        RIVER_2_4,
        RIVER_2_5,
        RIVER_2_6,
    )
    DARK_TRAPS = (DARK_TRAP_1, DARK_TRAP_2, DARK_TRAP_3)
    LIGHT_TRAPS = (LIGHT_TRAP_1, LIGHT_TRAP_2, LIGHT_TRAP_3)

    @staticmethod
    def rat(side: str) -> tuple[int, int]:
        return _select_by_side(side, CellPosition.DARK_RAT, CellPosition.LIGHT_RAT)

    @staticmethod
    def cat(side: str) -> tuple[int, int]:
        return _select_by_side(side, CellPosition.DARK_CAT, CellPosition.LIGHT_CAT)

    @staticmethod
    def dog(side: str) -> tuple[int, int]:
        return _select_by_side(side, CellPosition.DARK_DOG, CellPosition.LIGHT_DOG)

    @staticmethod
    def wolf(side: str) -> tuple[int, int]:
        return _select_by_side(side, CellPosition.DARK_WOLF, CellPosition.LIGHT_WOLF)

    @staticmethod
    def leopard(side: str) -> tuple[int, int]:
        return _select_by_side(
            side, CellPosition.DARK_LEOPARD, CellPosition.LIGHT_LEOPARD
        )

    @staticmethod
    def tiger(side: str) -> tuple[int, int]:
        return _select_by_side(side, CellPosition.DARK_TIGER, CellPosition.LIGHT_TIGER)

    @staticmethod
    def lion(side: str) -> tuple[int, int]:
        return _select_by_side(side, CellPosition.DARK_LION, CellPosition.LIGHT_LION)

    @staticmethod
    def elephant(side: str) -> tuple[int, int]:
        return _select_by_side(
            side, CellPosition.DARK_ELEPHANT, CellPosition.LIGHT_ELEPHANT
        )


class CellImage:
    """Ảnh đại diện cho hang, bẫy và sáu mảnh sông."""

    DEN = _asset_path("images", "den.png")
    TRAP = _asset_path("images", "trap.png")
    RIVER_1 = _asset_path("images", "rivers", "river_1.png")
    RIVER_2 = _asset_path("images", "rivers", "river_2.png")
    RIVER_3 = _asset_path("images", "rivers", "river_3.png")
    RIVER_4 = _asset_path("images", "rivers", "river_4.png")
    RIVER_5 = _asset_path("images", "rivers", "river_5.png")
    RIVER_6 = _asset_path("images", "rivers", "river_6.png")
    RIVERS = (RIVER_1, RIVER_2, RIVER_3, RIVER_4, RIVER_5, RIVER_6) * 2


class PieceName:
    """Tên hiển thị riêng của từng quân ở hai phe."""

    DARK_RAT = "Rat"
    DARK_CAT = "Sphynx"
    DARK_DOG = "Saluki"
    DARK_WOLF = "Grey Wolf"
    DARK_LEOPARD = "Black Panther"
    DARK_TIGER = "White Tiger"
    DARK_LION = "Smilodon"
    DARK_ELEPHANT = "Mammoth"
    LIGHT_RAT = "Mouse"
    LIGHT_CAT = "Wildcat"
    LIGHT_DOG = "Pitbull"
    LIGHT_WOLF = "Silver Fang"
    LIGHT_LEOPARD = "Siberi Leopard"
    LIGHT_TIGER = "Bengal Tiger"
    LIGHT_LION = "Panthera Leo"
    LIGHT_ELEPHANT = "Loxodonta"

    @staticmethod
    def rat(side: str) -> str:
        return _select_by_side(side, PieceName.DARK_RAT, PieceName.LIGHT_RAT)

    @staticmethod
    def cat(side: str) -> str:
        return _select_by_side(side, PieceName.DARK_CAT, PieceName.LIGHT_CAT)

    @staticmethod
    def dog(side: str) -> str:
        return _select_by_side(side, PieceName.DARK_DOG, PieceName.LIGHT_DOG)

    @staticmethod
    def wolf(side: str) -> str:
        return _select_by_side(side, PieceName.DARK_WOLF, PieceName.LIGHT_WOLF)

    @staticmethod
    def leopard(side: str) -> str:
        return _select_by_side(side, PieceName.DARK_LEOPARD, PieceName.LIGHT_LEOPARD)

    @staticmethod
    def tiger(side: str) -> str:
        return _select_by_side(side, PieceName.DARK_TIGER, PieceName.LIGHT_TIGER)

    @staticmethod
    def lion(side: str) -> str:
        return _select_by_side(side, PieceName.DARK_LION, PieceName.LIGHT_LION)

    @staticmethod
    def elephant(side: str) -> str:
        return _select_by_side(side, PieceName.DARK_ELEPHANT, PieceName.LIGHT_ELEPHANT)


class PieceDetail:
    """Mô tả tiếng Việt được hiển thị trên thẻ thông tin quân."""

    RAT = (
        "Hiệu ứng:\n- Chuột có thể đi vào sông.\n- Chuột có cấp thấp nhất "
        "nhưng có thể hạ Voi khi tấn công từ đất liền."
    )
    CAT = "Mô tả: Mèo có thể hạ Chuột."
    DOG = "Mô tả: Chó có thể hạ Mèo và Chuột.\nHiệu ứng: Chó có thể đi vào sông."
    WOLF = "Mô tả: Sói có thể hạ Chó, Mèo và Chuột."
    LEOPARD = "Mô tả: Báo có thể hạ Sói, Chó, Mèo và Chuột."
    TIGER = "Mô tả: Hổ có thể hạ Báo, Sói, Chó, Mèo và Chuột."
    LION = "Mô tả: Sư tử có thể hạ Hổ, Báo, Sói, Chó, Mèo và Chuột."
    ELEPHANT = "Mô tả: Voi có thể hạ Sư tử, Hổ, Báo, Sói, Chó và Mèo."


class PieceAtk:
    """Cấp sức mạnh cơ bản theo luật Đấu Thú Kỳ."""

    RAT = 1
    CAT = 2
    DOG = 3
    WOLF = 4
    LEOPARD = 5
    TIGER = 6
    LION = 7
    ELEPHANT = 8


class PieceAvatar:
    """Ảnh quân cờ kích thước một ô."""

    @staticmethod
    def _path(side: str, piece: str) -> str:
        color = "dark" if PlayerSide.is_dark(side) else "light"
        return _asset_path("pieces", color, f"{piece}.png")

    rat = staticmethod(lambda side: PieceAvatar._path(side, "rat"))
    cat = staticmethod(lambda side: PieceAvatar._path(side, "cat"))
    dog = staticmethod(lambda side: PieceAvatar._path(side, "dog"))
    wolf = staticmethod(lambda side: PieceAvatar._path(side, "wolf"))
    leopard = staticmethod(lambda side: PieceAvatar._path(side, "leopard"))
    tiger = staticmethod(lambda side: PieceAvatar._path(side, "tiger"))
    lion = staticmethod(lambda side: PieceAvatar._path(side, "lion"))
    elephant = staticmethod(lambda side: PieceAvatar._path(side, "elephant"))


class PieceArtWork:
    """Ảnh minh họa lớn dùng trên bảng thông tin."""

    @staticmethod
    def _path(side: str, piece: str) -> str:
        color = "dark" if PlayerSide.is_dark(side) else "light"
        return _asset_path("artworks", color, f"{piece}.png")

    rat = staticmethod(lambda side: PieceArtWork._path(side, "rat"))
    cat = staticmethod(lambda side: PieceArtWork._path(side, "cat"))
    dog = staticmethod(lambda side: PieceArtWork._path(side, "dog"))
    wolf = staticmethod(lambda side: PieceArtWork._path(side, "wolf"))
    leopard = staticmethod(lambda side: PieceArtWork._path(side, "leopard"))
    tiger = staticmethod(lambda side: PieceArtWork._path(side, "tiger"))
    lion = staticmethod(lambda side: PieceArtWork._path(side, "lion"))
    elephant = staticmethod(lambda side: PieceArtWork._path(side, "elephant"))
