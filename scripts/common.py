"""Hằng số và ánh xạ dùng chung của Animal Chess.

Module gom cấu hình bàn cờ, trạng thái, tài nguyên và thông tin quân cờ vào một
nơi duy nhất. Các lớp giữ API cũ để những module game không phải biết cách tài
nguyên được tổ chức trên đĩa.

``PIECES`` là NGUỒN SỰ THẬT DUY NHẤT cho vị trí xuất phát, tên hiển thị, điểm
tấn công và mô tả luật riêng của tám quân cờ. Trước khi có bảng này, các lớp
CellPosition/PieceName lặp lại tám staticmethod gần như giống hệt nhau (chỉ
khác tên quân) để tra vị trí/tên riêng theo phe, còn PieceAtk/PieceDetail liệt
kê tám hằng số song song theo đúng thứ tự quân - sửa một giá trị phải nhớ sửa
ở bốn, năm chỗ. Nay CellPosition/PieceName/PieceAtk/PieceDetail chỉ tra bảng
PIECES và giữ nguyên tên/API công khai cũ để không phá vỡ những module đã
import chúng; riêng PieceAvatar/PieceArtWork KHÔNG tra PIECES mà tự dựng
đường dẫn tài nguyên trực tiếp từ khóa (slug) của quân (vd. `_path(side,
"rat")`), vì khóa đó cũng chính là tên file ảnh/minh họa trên đĩa.
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


# ---------------------------------------------------------------------------
# Bảng metadata tám quân cờ - NGUỒN SỰ THẬT DUY NHẤT.
#
# Khóa ngoài cùng là "slug" viết thường của quân (rat, cat, dog, wolf,
# leopard, tiger, lion, elephant); slug này cũng chính là tên file ảnh dùng
# trong assets/pieces/{dark|light}/{slug}.png và assets/artworks/{dark|
# light}/{slug}.png, nên không cần cột slug riêng. Mỗi quân có:
#   dark_pos / light_pos   : tọa độ (cột, hàng) xuất phát theo phe.
#   dark_name / light_name : tên hiển thị trên thẻ thông tin theo phe.
#   atk                    : cấp sức mạnh cơ bản (1 yếu nhất .. 8 mạnh nhất,
#                            trùng đúng thứ tự bát thú của luật Đấu Thú Kỳ).
#   detail                 : mô tả/luật riêng hiển thị trên thẻ thông tin.
# Thứ tự khóa (rat -> elephant) được giữ đúng như thứ tự khai báo cũ trong
# CellPosition/PieceName/PieceAtk để không đổi ý nghĩa "bát thú" quen thuộc.
# ---------------------------------------------------------------------------
PIECES = {
    "rat": {
        "dark_pos": (0, 2), "light_pos": (6, 6),
        "dark_name": "Rat", "light_name": "Mouse",
        "atk": 1,
        "detail": (
            "Hiệu ứng:\n- Chuột có thể đi vào sông.\n- Chuột có cấp thấp nhất "
            "nhưng có thể hạ Voi khi tấn công từ đất liền."
        ),
    },
    "cat": {
        "dark_pos": (5, 1), "light_pos": (1, 7),
        "dark_name": "Sphynx", "light_name": "Wildcat",
        "atk": 2,
        "detail": "Mô tả: Mèo có thể hạ Chuột.",
    },
    "dog": {
        "dark_pos": (1, 1), "light_pos": (5, 7),
        "dark_name": "Saluki", "light_name": "Pitbull",
        "atk": 3,
        "detail": (
            "Mô tả: Chó có thể hạ Mèo và Chuột.\nHiệu ứng: Chó có thể đi vào sông."
        ),
    },
    "wolf": {
        "dark_pos": (4, 2), "light_pos": (2, 6),
        "dark_name": "Grey Wolf", "light_name": "Silver Fang",
        "atk": 4,
        "detail": "Mô tả: Sói có thể hạ Chó, Mèo và Chuột.",
    },
    "leopard": {
        "dark_pos": (2, 2), "light_pos": (4, 6),
        "dark_name": "Black Panther", "light_name": "Siberi Leopard",
        "atk": 5,
        "detail": "Mô tả: Báo có thể hạ Sói, Chó, Mèo và Chuột.",
    },
    "tiger": {
        "dark_pos": (6, 0), "light_pos": (0, 8),
        "dark_name": "White Tiger", "light_name": "Bengal Tiger",
        "atk": 6,
        "detail": "Mô tả: Hổ có thể hạ Báo, Sói, Chó, Mèo và Chuột.",
    },
    "lion": {
        "dark_pos": (0, 0), "light_pos": (6, 8),
        "dark_name": "Smilodon", "light_name": "Panthera Leo",
        "atk": 7,
        "detail": "Mô tả: Sư tử có thể hạ Hổ, Báo, Sói, Chó, Mèo và Chuột.",
    },
    "elephant": {
        "dark_pos": (6, 2), "light_pos": (0, 6),
        "dark_name": "Mammoth", "light_name": "Loxodonta",
        "atk": 8,
        "detail": "Mô tả: Voi có thể hạ Sư tử, Hổ, Báo, Sói, Chó và Mèo.",
    },
}


def _piece_position(key: str, side: str) -> tuple[int, int]:
    """Tra tọa độ xuất phát của quân `key` (slug trong PIECES) theo phe."""

    meta = PIECES[key]
    return _select_by_side(side, meta["dark_pos"], meta["light_pos"])


def _piece_name(key: str, side: str) -> str:
    """Tra tên hiển thị của quân `key` (slug trong PIECES) theo phe."""

    meta = PIECES[key]
    return _select_by_side(side, meta["dark_name"], meta["light_name"])


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

    # Tám staticmethod dưới đây thay cho tám hằng số DARK_*/LIGHT_* trước kia
    # (DARK_RAT, LIGHT_RAT, ..., DARK_ELEPHANT, LIGHT_ELEPHANT): tọa độ xuất
    # phát giờ tra thẳng từ bảng PIECES qua _piece_position, chỉ còn một nơi
    # lưu tọa độ cho mỗi quân thay vì lặp lại ở hằng số lẫn ở đây.
    @staticmethod
    def rat(side: str) -> tuple[int, int]:
        """Vị trí xuất phát của Chuột theo phe."""

        return _piece_position("rat", side)

    @staticmethod
    def cat(side: str) -> tuple[int, int]:
        """Vị trí xuất phát của Mèo theo phe."""

        return _piece_position("cat", side)

    @staticmethod
    def dog(side: str) -> tuple[int, int]:
        """Vị trí xuất phát của Chó theo phe."""

        return _piece_position("dog", side)

    @staticmethod
    def wolf(side: str) -> tuple[int, int]:
        """Vị trí xuất phát của Sói theo phe."""

        return _piece_position("wolf", side)

    @staticmethod
    def leopard(side: str) -> tuple[int, int]:
        """Vị trí xuất phát của Báo theo phe."""

        return _piece_position("leopard", side)

    @staticmethod
    def tiger(side: str) -> tuple[int, int]:
        """Vị trí xuất phát của Hổ theo phe."""

        return _piece_position("tiger", side)

    @staticmethod
    def lion(side: str) -> tuple[int, int]:
        """Vị trí xuất phát của Sư tử theo phe."""

        return _piece_position("lion", side)

    @staticmethod
    def elephant(side: str) -> tuple[int, int]:
        """Vị trí xuất phát của Voi theo phe."""

        return _piece_position("elephant", side)


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
    """Tên hiển thị riêng của từng quân ở hai phe, tra theo bảng PIECES."""

    @staticmethod
    def rat(side: str) -> str:
        """Tên hiển thị của Chuột theo phe."""

        return _piece_name("rat", side)

    @staticmethod
    def cat(side: str) -> str:
        """Tên hiển thị của Mèo theo phe."""

        return _piece_name("cat", side)

    @staticmethod
    def dog(side: str) -> str:
        """Tên hiển thị của Chó theo phe."""

        return _piece_name("dog", side)

    @staticmethod
    def wolf(side: str) -> str:
        """Tên hiển thị của Sói theo phe."""

        return _piece_name("wolf", side)

    @staticmethod
    def leopard(side: str) -> str:
        """Tên hiển thị của Báo theo phe."""

        return _piece_name("leopard", side)

    @staticmethod
    def tiger(side: str) -> str:
        """Tên hiển thị của Hổ theo phe."""

        return _piece_name("tiger", side)

    @staticmethod
    def lion(side: str) -> str:
        """Tên hiển thị của Sư tử theo phe."""

        return _piece_name("lion", side)

    @staticmethod
    def elephant(side: str) -> str:
        """Tên hiển thị của Voi theo phe."""

        return _piece_name("elephant", side)


class PieceDetail:
    """Mô tả tiếng Việt hiển thị trên thẻ thông tin quân.

    Không phân biệt phe (khác PieceName/CellPosition) nên chỉ cần đọc thẳng
    trường "detail" của mỗi quân trong PIECES tại thời điểm định nghĩa lớp.
    """

    RAT = PIECES["rat"]["detail"]
    CAT = PIECES["cat"]["detail"]
    DOG = PIECES["dog"]["detail"]
    WOLF = PIECES["wolf"]["detail"]
    LEOPARD = PIECES["leopard"]["detail"]
    TIGER = PIECES["tiger"]["detail"]
    LION = PIECES["lion"]["detail"]
    ELEPHANT = PIECES["elephant"]["detail"]


class PieceAtk:
    """Cấp sức mạnh cơ bản theo luật Đấu Thú Kỳ.

    Không phân biệt phe nên chỉ cần đọc thẳng trường "atk" của mỗi quân
    trong PIECES tại thời điểm định nghĩa lớp (1 yếu nhất .. 8 mạnh nhất).
    """

    RAT = PIECES["rat"]["atk"]
    CAT = PIECES["cat"]["atk"]
    DOG = PIECES["dog"]["atk"]
    WOLF = PIECES["wolf"]["atk"]
    LEOPARD = PIECES["leopard"]["atk"]
    TIGER = PIECES["tiger"]["atk"]
    LION = PIECES["lion"]["atk"]
    ELEPHANT = PIECES["elephant"]["atk"]


class PieceAvatar:
    """Ảnh quân cờ kích thước một ô.

    Đường dẫn được dựng từ slug quân (khóa của PIECES, cũng là tên file:
    assets/pieces/{dark|light}/{slug}.png) chứ không cần thêm dữ liệu mới.
    """

    @staticmethod
    def _path(side: str, piece: str) -> str:
        """Ghép thư mục theo phe (dark/light) với tên file ảnh của quân."""

        color = "dark" if PlayerSide.is_dark(side) else "light"
        return _asset_path("pieces", color, f"{piece}.png")

    @staticmethod
    def rat(side: str) -> str:
        """Ảnh đại diện của Chuột theo phe."""

        return PieceAvatar._path(side, "rat")

    @staticmethod
    def cat(side: str) -> str:
        """Ảnh đại diện của Mèo theo phe."""

        return PieceAvatar._path(side, "cat")

    @staticmethod
    def dog(side: str) -> str:
        """Ảnh đại diện của Chó theo phe."""

        return PieceAvatar._path(side, "dog")

    @staticmethod
    def wolf(side: str) -> str:
        """Ảnh đại diện của Sói theo phe."""

        return PieceAvatar._path(side, "wolf")

    @staticmethod
    def leopard(side: str) -> str:
        """Ảnh đại diện của Báo theo phe."""

        return PieceAvatar._path(side, "leopard")

    @staticmethod
    def tiger(side: str) -> str:
        """Ảnh đại diện của Hổ theo phe."""

        return PieceAvatar._path(side, "tiger")

    @staticmethod
    def lion(side: str) -> str:
        """Ảnh đại diện của Sư tử theo phe."""

        return PieceAvatar._path(side, "lion")

    @staticmethod
    def elephant(side: str) -> str:
        """Ảnh đại diện của Voi theo phe."""

        return PieceAvatar._path(side, "elephant")


class PieceArtWork:
    """Ảnh minh họa lớn dùng trên bảng thông tin.

    Cùng slug với PieceAvatar nhưng đọc từ thư mục assets/artworks thay vì
    assets/pieces, phục vụ khung ảnh lớn (Size.ARTWORK) trên thẻ thông tin.
    """

    @staticmethod
    def _path(side: str, piece: str) -> str:
        """Ghép thư mục theo phe (dark/light) với tên file minh họa của quân."""

        color = "dark" if PlayerSide.is_dark(side) else "light"
        return _asset_path("artworks", color, f"{piece}.png")

    @staticmethod
    def rat(side: str) -> str:
        """Ảnh minh họa của Chuột theo phe."""

        return PieceArtWork._path(side, "rat")

    @staticmethod
    def cat(side: str) -> str:
        """Ảnh minh họa của Mèo theo phe."""

        return PieceArtWork._path(side, "cat")

    @staticmethod
    def dog(side: str) -> str:
        """Ảnh minh họa của Chó theo phe."""

        return PieceArtWork._path(side, "dog")

    @staticmethod
    def wolf(side: str) -> str:
        """Ảnh minh họa của Sói theo phe."""

        return PieceArtWork._path(side, "wolf")

    @staticmethod
    def leopard(side: str) -> str:
        """Ảnh minh họa của Báo theo phe."""

        return PieceArtWork._path(side, "leopard")

    @staticmethod
    def tiger(side: str) -> str:
        """Ảnh minh họa của Hổ theo phe."""

        return PieceArtWork._path(side, "tiger")

    @staticmethod
    def lion(side: str) -> str:
        """Ảnh minh họa của Sư tử theo phe."""

        return PieceArtWork._path(side, "lion")

    @staticmethod
    def elephant(side: str) -> str:
        """Ảnh minh họa của Voi theo phe."""

        return PieceArtWork._path(side, "elephant")
