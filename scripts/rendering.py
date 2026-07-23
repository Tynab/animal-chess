"""Render giao diện Pygame cho màn hình bắt đầu, bàn cờ và thẻ quân.

Tài nguyên được khởi tạo lười sau ``pygame.init()`` thay vì ngay khi import.
Điều này giúp các module logic có thể được import và kiểm thử headless.
"""

import math

import pygame

from scripts import common
from scripts.common import Color, FontName, GameState, ImagePath, Size


# Rect hình học của nút "Ván mới", tính sẵn ngay lúc import (chỉ dùng
# Size.BOARD/Size.START_BTN từ scripts.common nên KHÔNG cần pygame.init()
# trước). Được export để main.handle_events dùng collidepoint() phát hiện
# click nút mà không phải phụ thuộc vào initialize()/render nào khác — hit
# test và vẽ nút luôn dùng chung đúng một hình chữ nhật.
START_BTN_RECT = pygame.Rect(
    (Size.BOARD[0] - Size.START_BTN[0]) / 2,
    Size.BOARD[1] - Size.START_BTN[1] - 25,
    *Size.START_BTN,
)
# Các hằng số toạ độ/layout dưới đây đều suy ra từ Size (scripts.common) để
# canh giữa tiêu đề/kết quả trên bàn cờ và canh lề panel mô tả quân bên phải;
# đổi Size ở common.py sẽ tự động kéo theo layout ở đây, không cần sửa số cứng.
X_RESULT, Y_RESULT = Size.BOARD[0] / 2, Size.BOARD[1] / 2 + Size.PADDING[1] * 9
X_DESCRIPTION = Size.PADDING[0] * 2
Y_DESCRIPTION = Size.ARTWORK[1] + Size.PADDING[1] * 7
Y_ARTWORK = Size.PADDING[1] * 2
LINE_SPACE = Size.PADDING[1] / 2
DESCRIPTION_WIDTH = Size.SUBSCREEN[0] - Size.PADDING[0] * 3
HIGHLIGHT_CENTER = (common.SPAN // 2, common.SPAN // 2)
HIGHLIGHT_RADIUS = common.SPAN // 4
OPACITY = 192

# Tài nguyên Pygame (ảnh/font) không thể nạp trước pygame.init()/pygame.font
# sẵn sàng, nên chỉ được khai báo placeholder None ở đây rồi nạp thật trong
# initialize(); None còn đóng vai trò cờ "chưa nạp" cho guard bên dưới.
COVER_SCALED = None
START_BTN_SCALED = None
GUIDE_SCALED = None
CARD_SCALED = None
SUBSCREEN_SURFACE = None
FONT_TITLE = None
FONT_BUTTON = None
FONT_RESULT = None


def initialize() -> None:
    """Nạp ảnh và font đúng một lần sau khi Pygame đã sẵn sàng."""

    global COVER_SCALED, START_BTN_SCALED, GUIDE_SCALED, CARD_SCALED
    global SUBSCREEN_SURFACE, FONT_TITLE, FONT_BUTTON, FONT_RESULT
    # Guard idempotent: mọi hàm draw_* đều tự gọi initialize() trước khi vẽ,
    # nên hàm này phải an toàn khi gọi lại nhiều lần mỗi frame — chỉ nạp ảnh/
    # font thật một lần duy nhất (khi COVER_SCALED còn None), các lần sau chỉ
    # là no-op rẻ tiền.
    if COVER_SCALED is not None:
        return
    COVER_SCALED = pygame.transform.scale(
        pygame.image.load(ImagePath.COVER), Size.BOARD
    )
    START_BTN_SCALED = pygame.transform.scale(
        pygame.image.load(ImagePath.START_BTN), Size.START_BTN
    )
    GUIDE_SCALED = pygame.transform.scale(
        pygame.image.load(ImagePath.GUIDE), Size.SUBSCREEN
    )
    CARD_SCALED = pygame.transform.scale(
        pygame.image.load(ImagePath.CARD), Size.SUBSCREEN
    )
    SUBSCREEN_SURFACE = pygame.Surface(Size.SUBSCREEN)
    FONT_TITLE = pygame.font.SysFont(FontName.TIT, 45, bold=True)
    FONT_BUTTON = pygame.font.SysFont(FontName.BTN, 23, bold=True)
    FONT_RESULT = pygame.font.SysFont(FontName.TXT, 57, bold=True)


def _set_cursor(cursor: int) -> None:
    """Đổi con trỏ khi backend hỗ trợ; dummy/headless có thể không tạo được."""

    try:
        pygame.mouse.set_cursor(cursor)
    except pygame.error:
        pass


def draw_screen(screen: pygame.Surface, game_manager) -> None:
    """Vẽ màn hình bắt đầu hoặc kết quả cùng nút tạo ván mới."""

    initialize()
    screen.blit(COVER_SCALED, (0, 0))
    title = FONT_TITLE.render(common.TIT, True, Color.WHITE)
    screen.blit(title, title.get_rect(center=(X_RESULT, 25)))

    if GameState.is_over(game_manager.game_state):
        # game_result có thể là nhiều dòng ("<PHE>\nWIN!!!" hoặc "DRAW"), mỗi
        # dòng được vẽ và xếp chồng xuống dưới dựa theo chiều cao dòng trước
        # cộng khoảng cách dòng (LINE_SPACE), không phải toạ độ cố định.
        for index, line in enumerate(game_manager.game_result.split("\n")):
            result = FONT_RESULT.render(line, True, Color.YELLOW)
            position = Y_RESULT + index * (result.get_height() + LINE_SPACE)
            screen.blit(result, result.get_rect(center=(X_RESULT, position)))

    hovered = START_BTN_RECT.collidepoint(pygame.mouse.get_pos())
    _set_cursor(pygame.SYSTEM_CURSOR_HAND if hovered else pygame.SYSTEM_CURSOR_ARROW)
    screen.blit(START_BTN_SCALED, START_BTN_RECT.topleft)
    label = FONT_BUTTON.render(
        "Ván mới", True, Color.YELLOW if hovered else Color.WHITE
    )
    screen.blit(label, label.get_rect(center=START_BTN_RECT.center))
    draw_guide(screen)


def draw_game(screen: pygame.Surface, game_manager) -> None:
    """Vẽ bàn, quân, các nước hợp lệ và bảng thông tin bên phải."""

    initialize()
    cursor_hand = False
    mouse_position = pygame.mouse.get_pos()
    for column in game_manager.board.cells:
        for cell in column:
            x, y = cell.position[0] * common.SPAN, cell.position[1] * common.SPAN
            cell_rect = pygame.Rect(x, y, common.SPAN, common.SPAN)
            pygame.draw.rect(screen, Color.WHITE, cell_rect)
            if cell.image:
                screen.blit(cell.image, (x, y))
            pygame.draw.rect(screen, Color.GREY, cell_rect, 1)

            if cell.piece:
                # Con trỏ chỉ đổi thành bàn tay khi ô đang trỏ chuột có quân
                # của ĐÚNG phe đang tới lượt (current_side) — gợi ý quân nào
                # có thể bấm chọn ngay bây giờ.
                cursor_hand |= (
                    cell_rect.collidepoint(mouse_position)
                    and cell.piece.side == game_manager.current_side
                )
                # Ngôi sao bán trong suốt vẽ TRƯỚC ảnh quân (nằm dưới) để làm
                # nền đánh dấu màu theo phe (cam cho tối, cyan cho sáng - xem
                # Color.star_color), không che khuất hình quân vẽ đè lên trên.
                draw_star(
                    screen,
                    Color.star_color(cell.piece.side),
                    cell_rect.center,
                    40,
                    20,
                    OPACITY,
                    20,
                )
                # Quân đứng ở nửa bàn bên phải (cột x > 3) được lật ngang khi
                # vẽ để tạo cảm giác đối xứng thị giác giữa hai nửa bàn cờ;
                # việc lật này chỉ dựa vào cột hiện tại, không phụ thuộc phe.
                image = (
                    pygame.transform.flip(cell.piece.image, True, False)
                    if cell.position[0] > 3
                    else cell.piece.image
                )
                screen.blit(image, (x, y))

    if game_manager.selected_piece:
        for cell in game_manager.selected_piece.available_cells(game_manager.board):
            x, y = cell.position[0] * common.SPAN, cell.position[1] * common.SPAN
            cell_rect = pygame.Rect(x, y, common.SPAN, common.SPAN)
            cursor_hand |= cell_rect.collidepoint(mouse_position)
            highlight = pygame.Surface((common.SPAN, common.SPAN), pygame.SRCALPHA)
            # "Nhảy" (is_jump) chỉ để CHỌN MÀU highlight, không phải kiểm tra
            # luật (luật đã được available_cells lọc từ trước): ô sông, hoặc ô
            # cách quân đang chọn hơn 1 bước theo cột/hàng, được coi là một
            # bước nhảy (Hổ/Sư nhảy qua sông, Chuột/Chó lội qua từng ô sông)
            # thay vì một bước đi liền kề thông thường.
            is_jump = (
                cell.is_river
                or abs(cell.position[0] - game_manager.selected_piece.position[0]) > 1
                or abs(cell.position[1] - game_manager.selected_piece.position[1]) > 1
            )
            # Ưu tiên màu theo thứ tự: đỏ nếu ô đích có quân địch (sẽ bị ăn),
            # xanh lá nếu là một bước nhảy không ăn quân, còn lại (bước đi
            # thường không ăn quân) tô vàng.
            color = (
                Color.RED if cell.piece else Color.GREEN if is_jump else Color.YELLOW
            )
            pygame.draw.circle(
                highlight, (*color, OPACITY), HIGHLIGHT_CENTER, HIGHLIGHT_RADIUS
            )
            screen.blit(highlight, (x, y))

    _set_cursor(
        pygame.SYSTEM_CURSOR_HAND if cursor_hand else pygame.SYSTEM_CURSOR_ARROW
    )
    if game_manager.focused_piece:
        draw_subscreen(screen, game_manager)
    else:
        draw_guide(screen)


def draw_guide(screen: pygame.Surface) -> None:
    """Vẽ ảnh hướng dẫn ở panel bên phải."""

    initialize()
    SUBSCREEN_SURFACE.blit(GUIDE_SCALED, (0, 0))
    screen.blit(SUBSCREEN_SURFACE, (Size.BOARD[0], 0))


def draw_subscreen(screen: pygame.Surface, game_manager) -> None:
    """Vẽ artwork và mô tả của quân đang được trỏ chuột."""

    initialize()
    piece = game_manager.focused_piece
    SUBSCREEN_SURFACE.blit(CARD_SCALED, (0, 0))
    SUBSCREEN_SURFACE.blit(piece.artwork, (Size.PADDING[0], Y_ARTWORK))
    # piece.atk phản ánh SỨC MẠNH HIỆN TẠI (có thể là 0 nếu quân đang đứng
    # trên bẫy của đối phương, xem Cell.add_piece), không phải cấp cơ bản cố
    # định — panel hiển thị đúng trạng thái tại thời điểm này để người chơi
    # biết quân có đang bị triệt sức hay không.
    description = (
        f"Tên: {piece.name}\nPhe: {piece.side}\nLoại: {type(piece).__name__}\n"
        f"Sức mạnh: {piece.atk}\n{piece.detail}"
    )
    y_position = Y_DESCRIPTION
    for line in wrap_text(description, FONT_BUTTON, DESCRIPTION_WIDTH):
        text = FONT_BUTTON.render(line, True, Color.WHITE)
        SUBSCREEN_SURFACE.blit(text, (X_DESCRIPTION, y_position))
        y_position += text.get_height() + LINE_SPACE
    screen.blit(SUBSCREEN_SURFACE, (Size.BOARD[0], 0))


def draw_star(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    center: tuple[int, int],
    outer_radius: int,
    inner_radius: int,
    opacity: int = 255,
    points: int = 5,
) -> None:
    """Vẽ ngôi sao bán trong suốt ở tâm quân."""

    # Surface riêng đúng bằng đường kính ngoài để vùng vẽ luôn đủ chứa ngôi
    # sao rồi blit cả khối vào đúng tâm mong muốn (bù trừ bằng outer_radius).
    star = pygame.Surface((2 * outer_radius, 2 * outer_radius), pygame.SRCALPHA)
    angle_step = 2 * math.pi / points
    star_center = (outer_radius, outer_radius)
    vertices = []
    for index in range(points):
        # Ngôi sao "points" cánh được dựng từ 2*points đỉnh xen kẽ ngoài/trong:
        # đỉnh ngoài (outer_radius) là chóp cánh sao, đỉnh trong (inner_radius,
        # lệch nửa bước góc so với đỉnh ngoài) là hõm giữa hai cánh liền kề.
        # Bắt đầu từ góc pi/2 (hướng lên) rồi quay dần theo chiều kim đồng hồ.
        outer_angle = math.pi / 2 - index * angle_step
        inner_angle = math.pi / 2 - (index + 0.5) * angle_step
        vertices.extend(
            (
                (
                    star_center[0] + math.cos(outer_angle) * outer_radius,
                    star_center[1] - math.sin(outer_angle) * outer_radius,
                ),
                (
                    star_center[0] + math.cos(inner_angle) * inner_radius,
                    star_center[1] - math.sin(inner_angle) * inner_radius,
                ),
            )
        )
    pygame.draw.polygon(star, (*color, opacity), vertices)
    surface.blit(star, (center[0] - outer_radius, center[1] - outer_radius))


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Ngắt văn bản theo từ để không vượt chiều rộng panel.

    Xuống dòng "cứng" (``\\n`` có sẵn trong mô tả quân) được giữ nguyên ranh
    giới — mỗi dòng gốc được ngắt từ độc lập, không gộp chữ giữa hai dòng gốc
    khác nhau. Trong mỗi dòng, thuật toán tham lam (greedy word-wrap): thử
    thêm từng từ vào dòng hiện tại, đo bề rộng thực tế bằng font đã chọn; hễ
    vượt quá ``max_width`` thì chốt dòng hiện tại và bắt đầu dòng mới với từ
    vừa vượt quá đó (từ đầu tiên của một dòng luôn được giữ dù tự nó đã dài
    hơn max_width, tránh vòng lặp vô hạn không bao giờ chốt được dòng).
    """

    wrapped = []
    for source_line in text.splitlines():
        current = []
        for word in source_line.split():
            candidate = " ".join((*current, word))
            if not current or font.size(candidate)[0] <= max_width:
                current.append(word)
            else:
                wrapped.append(" ".join(current))
                current = [word]
        wrapped.append(" ".join(current))
    return wrapped
