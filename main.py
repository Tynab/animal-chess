"""Điểm vào ứng dụng Animal Chess.

Vòng lặp luôn xử lý hàng đợi sự kiện, kể cả khi máy đang tự đấu, để cửa sổ
không bị hệ điều hành đánh dấu “Not responding”. Module an toàn khi import vì
chỉ chạy game bên trong guard ``__main__``.

Ba chế độ chơi (xem ``GameMode`` ở ``scripts.common``) rẽ nhánh xuyên suốt file
này: PvP luôn chờ người, PvC chỉ chờ người khi tới lượt phe sáng (quy ước
``GameManager`` luôn khởi động và reset về phe sáng cho người chơi), còn CvC
để máy tự đấu liên tục nhiều ván (giới hạn bởi ``AUTO_GAME_LIMIT``) — hữu ích
để rả nhàn sinh dữ liệu ván đấu (xem ``scripts.log.Log``) mà không cần người
bấm "Ván mới" thủ công sau mỗi ván.
"""

import asyncio

import pygame

from scripts import common, rendering
from scripts.common import Color, GameMode, GameState, PlayerSide, Size
from scripts.manager import GameManager


DEFAULT_GAME_MODE = GameMode.PvC
# Trần số ván CvC tự động chơi liên tiếp trước khi vòng lặp ngừng reset và để
# màn hình kết quả của ván cuối cùng đứng yên; tránh chạy vô hạn nếu người
# dùng chỉ muốn máy tự đấu để sinh log rồi dừng lại, không phải treo mãi.
AUTO_GAME_LIMIT = 5_000


def is_human_turn(game_manager: GameManager) -> bool:
    """Xác định lượt hiện tại có nhận thao tác bàn cờ từ người chơi hay không.

    PvP: luôn là người (cả hai phe đều do người điều khiển). PvC: chỉ đúng khi
    phe hiện tại là phe SÁNG, vì ``GameManager`` quy ước phe sáng luôn là
    người chơi và phe tối luôn là máy (``reset_game``/``__init__`` đặt
    ``current_side = PlayerSide.LIGHT`` cho lượt đầu). CvC không bao giờ trả
    True vì cả hai phe đều do máy tự chơi (``run_game`` gọi ``autoplay`` thẳng).
    """

    return GameMode.is_pvp(game_manager.game_mode) or (
        GameMode.is_pvc(game_manager.game_mode)
        and PlayerSide.is_light(game_manager.current_side)
    )


def handle_events(game_manager: GameManager) -> bool:
    """Xử lý đóng cửa sổ, nút ván mới và click chọn/di chuyển quân.

    Trả về False khi nhận ``pygame.QUIT`` để ``run_game`` thoát vòng lặp; mọi
    sự kiện khác ngoài click chuột trái đều bị bỏ qua ngay (game không cần
    theo dõi bàn phím hay việc di chuột không bấm nút).
    """

    for current_event in pygame.event.get():
        if current_event.type == pygame.QUIT:
            return False
        if current_event.type != pygame.MOUSEBUTTONDOWN:
            continue

        mouse_position = current_event.pos
        if GameState.is_running(game_manager.game_state):
            # Ván đang chạy: chỉ định tuyến click bàn cờ khi đúng lượt người
            # chơi; click trong lượt máy (PvC phe tối, hoặc CvC) bị bỏ qua vì
            # autoplay() điều khiển bàn cờ, không phải người dùng.
            if not is_human_turn(game_manager):
                continue
            # Click đầu tiên: chưa chọn quân -> thử chọn. Click thứ hai: đã có
            # quân chọn sẵn -> thử coi đây là ô đích để di chuyển; nếu di
            # chuyển thất bại (ô không hợp lệ) thì coi click đó như một lựa
            # chọn quân mới (cho phép đổi quân đang chọn mà không cần bấm huỷ).
            if (
                game_manager.selected_piece is None
                or not game_manager.handle_piece_move(mouse_position)
            ):
                game_manager.handle_piece_selection(mouse_position)
        elif rendering.START_BTN_RECT.collidepoint(mouse_position):
            # Ván chưa chạy (màn hình mở đầu hoặc màn hình kết quả): chỉ nút
            # "Ván mới" mới có tác dụng, click ở nơi khác bị bỏ qua.
            game_manager.reset_game()
    return True


async def run_game(
    game_mode: int = DEFAULT_GAME_MODE,
    auto_game_limit: int = AUTO_GAME_LIMIT,
) -> None:
    """Khởi tạo Pygame và chạy vòng lặp chính bất đồng bộ."""

    pygame.init()
    # SRCALPHA + độ sâu 32-bit để các lớp phủ bán trong suốt (ngôi sao đánh
    # dấu quân, highlight ô đích) trong scripts.rendering blit đúng kênh alpha.
    screen = pygame.display.set_mode(Size.TOTAL, pygame.SRCALPHA, 32)
    pygame.display.set_caption(common.TIT)
    rendering.initialize()
    clock = pygame.time.Clock()
    game_manager = GameManager(game_mode)
    remaining_auto_games = auto_game_limit
    running = True

    try:
        while running:
            running = handle_events(game_manager)
            screen.fill(Color.WHITE)

            if GameState.is_running(game_manager.game_state):
                if GameMode.is_cvc(game_manager.game_mode) or (
                    GameMode.is_pvc(game_manager.game_mode)
                    and PlayerSide.is_dark(game_manager.current_side)
                ):
                    # Lượt của máy: CvC luôn tự chơi cả hai phe; PvC chỉ tự
                    # chơi khi tới lượt phe tối (phe sáng dành cho người, xem
                    # is_human_turn ở trên).
                    game_manager.autoplay()
                else:
                    # Lượt người: không có sự kiện click nào bắt buộc phải xảy
                    # ra mỗi frame, nhưng vẫn cần theo dõi quân đang bị trỏ
                    # chuột để panel bên phải cập nhật ảnh minh hoạ theo thời
                    # gian thực (xem GameManager.handle_piece_focus).
                    game_manager.handle_piece_focus(pygame.mouse.get_pos())
                rendering.draw_game(screen, game_manager)
            elif GameMode.is_cvc(game_manager.game_mode) and remaining_auto_games > 0:
                # CvC vừa kết thúc một ván (hoặc mới khởi động): tự động mở
                # ván tiếp theo thay vì chờ người bấm "Ván mới", cho tới khi
                # dùng hết hạn mức remaining_auto_games; frame này không vẽ gì
                # thêm ngoài nền trắng vì bàn cờ vừa được reset.
                game_manager.reset_game()
                remaining_auto_games -= 1
            else:
                # Không phải CvC (hoặc CvC đã hết hạn mức tự chơi): hiển thị
                # màn hình mở đầu/kết quả cùng nút "Ván mới" cho người bấm.
                rendering.draw_screen(screen, game_manager)

            pygame.display.flip()
            clock.tick(common.FPS)
            # Nhường quyền điều khiển cho event loop asyncio đúng một tick mỗi
            # frame. Không có dòng này, vòng lặp while đồng bộ chiếm trọn CPU
            # và event loop không có cơ hội xử lý việc khác (ví dụ khi build
            # chạy trên nền asyncio/WASM qua pygbag) — cửa sổ dễ bị hệ điều
            # hành coi là treo dù logic game vẫn chạy đúng, đặc biệt trong lúc
            # CvC tự đấu liên tục không có input người dùng để "đánh thức" nó.
            await asyncio.sleep(0)
    finally:
        pygame.quit()


if __name__ == "__main__":
    asyncio.run(run_game())
