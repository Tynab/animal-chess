"""Điểm vào ứng dụng Animal Chess.

Vòng lặp luôn xử lý hàng đợi sự kiện, kể cả khi máy đang tự đấu, để cửa sổ
không bị hệ điều hành đánh dấu “Not responding”. Module an toàn khi import vì
chỉ chạy game bên trong guard ``__main__``.
"""

import asyncio

import pygame

from scripts import common, rendering
from scripts.common import Color, GameMode, GameState, PlayerSide, Size
from scripts.manager import GameManager


DEFAULT_GAME_MODE = GameMode.PvC
AUTO_GAME_LIMIT = 5_000


def is_human_turn(game_manager: GameManager) -> bool:
    """Xác định lượt hiện tại có nhận thao tác bàn cờ từ người chơi hay không."""

    return GameMode.is_pvp(game_manager.game_mode) or (
        GameMode.is_pvc(game_manager.game_mode)
        and PlayerSide.is_light(game_manager.current_side)
    )


def handle_events(game_manager: GameManager) -> bool:
    """Xử lý đóng cửa sổ, nút ván mới và click chọn/di chuyển quân."""

    for current_event in pygame.event.get():
        if current_event.type == pygame.QUIT:
            return False
        if current_event.type != pygame.MOUSEBUTTONDOWN:
            continue

        mouse_position = current_event.pos
        if GameState.is_running(game_manager.game_state):
            if not is_human_turn(game_manager):
                continue
            if (
                game_manager.selected_piece is None
                or not game_manager.handle_piece_move(mouse_position)
            ):
                game_manager.handle_piece_selection(mouse_position)
        elif rendering.START_BTN_RECT.collidepoint(mouse_position):
            game_manager.reset_game()
    return True


async def run_game(
    game_mode: int = DEFAULT_GAME_MODE,
    auto_game_limit: int = AUTO_GAME_LIMIT,
) -> None:
    """Khởi tạo Pygame và chạy vòng lặp chính bất đồng bộ."""

    pygame.init()
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
                    game_manager.autoplay()
                else:
                    game_manager.handle_piece_focus(pygame.mouse.get_pos())
                rendering.draw_game(screen, game_manager)
            elif GameMode.is_cvc(game_manager.game_mode) and remaining_auto_games > 0:
                game_manager.reset_game()
                remaining_auto_games -= 1
            else:
                rendering.draw_screen(screen, game_manager)

            pygame.display.flip()
            clock.tick(common.FPS)
            await asyncio.sleep(0)
    finally:
        pygame.quit()


if __name__ == "__main__":
    asyncio.run(run_game())
