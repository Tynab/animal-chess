"""Điều phối ván chơi, thao tác chuột và lựa chọn nước đi của máy.

Model Keras được nạp lười đúng một lần và dự đoán toàn bộ nước hợp lệ theo
batch. Khi model thiếu hoặc không tương thích, game tự hạ cấp sang minimax thay
vì dừng đột ngột.
"""

from pathlib import Path
import random
import warnings

import numpy as np

from scripts.board import Board
from scripts.bot import Bot
from scripts.common import BEST_MODEL_PATH, GameMode, GameState, PlayerSide, Size, SPAN
from scripts.encoding import PIECE_ENCODING, encode_board, encode_piece
from scripts.log import Log


class GameManager:
    """Giữ state ván chơi và nối UI với bàn cờ, bot, log, model AI."""

    # Giữ alias để code/test cũ dùng GameManager.PIECE_ENCODING vẫn chạy được.
    PIECE_ENCODING = PIECE_ENCODING

    def __init__(
        self, game_mode: int = GameMode.PvC, model_path=BEST_MODEL_PATH
    ) -> None:
        self.game_mode = game_mode
        self.model_path = Path(model_path)
        self._model = None
        self._model_unavailable = False
        self.log = Log()
        self.board = Board()
        self.game_state = GameState.NEW
        self.game_result = None
        self.current_side = PlayerSide.LIGHT
        self.opponent_side = PlayerSide.DARK
        self.selected_piece = None
        self.focused_piece = None

    def reset_game(self) -> None:
        """Khởi tạo ván mới và luôn trả lượt đầu cho phe sáng."""

        self.board = Board()
        self.game_state = GameState.RUNNING
        self.game_result = None
        self.current_side = PlayerSide.LIGHT
        self.opponent_side = PlayerSide.DARK
        self.selected_piece = None
        self.focused_piece = None

    def switch_player(self) -> None:
        self.current_side, self.opponent_side = self.opponent_side, self.current_side
        # Ngăn xếp undo chỉ phục vụ tìm kiếm trong một lượt thực tế.
        self.board.captured_pieces.clear()

    def _cell_at_mouse(self, mouse_position: tuple[int, int]):
        """Đổi pixel sang ô và chặn click ngoài vùng bàn cờ."""

        x, y = mouse_position
        if not (0 <= x < Size.BOARD[0] and 0 <= y < Size.BOARD[1]):
            return None
        return self.board.get_cell((x // SPAN, y // SPAN))

    def handle_piece_focus(self, mouse_position: tuple[int, int]) -> None:
        cell = self._cell_at_mouse(mouse_position)
        self.focused_piece = cell.piece if cell else None

    def handle_piece_selection(self, mouse_position: tuple[int, int]) -> None:
        cell = self._cell_at_mouse(mouse_position)
        if cell and cell.piece and cell.piece.side == self.current_side:
            self.selected_piece = cell.piece

    def handle_piece_move(self, mouse_position: tuple[int, int]) -> bool:
        """Thử di chuyển quân đang chọn; trả về True khi đã đi thành công."""

        target_cell = self._cell_at_mouse(mouse_position)
        if self.selected_piece is None or target_cell is None:
            return False
        if target_cell not in self.selected_piece.available_cells(self.board):
            return False

        move = (self.selected_piece.position, target_cell.position)
        self.board.make_move(move)
        self.selected_piece = None
        self.log.insert_chess_record(self.board, move)
        if self.is_game_end:
            self.log.save()
            return True
        self.switch_player()
        return True

    def autoplay(self) -> None:
        """Cho máy đi bằng model; tự dùng minimax nếu model không khả dụng."""

        move = self.ai_move() or self.computer_move()
        if move is None:
            self.is_game_end
            return
        self.board.make_move(move)
        self.log.insert_chess_record(self.board, move)
        if self.is_game_end:
            self.log.save()
            return
        self.switch_player()

    def computer_move(self):
        """Chọn nước bằng minimax/alpha-beta rồi ưu tiên lộ trình ngắn."""

        search_board = self.board.copy()
        if random.choice((False, True)):
            _, best_moves = Bot.minimax(search_board, self.current_side, 2, True)
        else:
            _, best_moves = Bot.minimax_alpha_beta_pruning(
                search_board,
                self.current_side,
                2,
                float("-inf"),
                float("inf"),
                True,
            )
        best_moves = best_moves or self.board.get_valid_moves(self.current_side)
        if not best_moves:
            return None

        use_bfs = (
            self.algorithm_random(len(self.board.pieces_of[self.opponent_side])) == 1
        )
        routed = (
            self.breadth_first_search_moves(best_moves)
            if use_bfs
            else self.a_star_search_moves(best_moves)
        )
        return random.choice(routed or best_moves)

    def _route_moves(self, best_moves: list[tuple], search) -> list[tuple]:
        """Lọc các nước tốt đồng thời là bước đầu của lộ trình ngắn nhất."""

        shortest = float("inf")
        routed = []
        for piece in self.board.pieces_of[self.current_side]:
            paths, _ = search(
                self.board,
                piece,
                piece.position,
                piece.weaker_pieces_positions(self.board),
            )
            if not paths:
                continue
            for distance, path in paths:
                if len(path) < 2:
                    continue
                move = (path[0], path[1])
                if move not in best_moves:
                    continue
                if distance < shortest:
                    shortest, routed = distance, [move]
                elif distance == shortest:
                    routed.append(move)
        # Khử trùng lặp nhưng giữ nguyên thứ tự để kết quả dễ kiểm tra.
        return list(dict.fromkeys(routed))

    def breadth_first_search_moves(self, best_moves: list[tuple]) -> list[tuple]:
        return self._route_moves(best_moves, Bot.breadth_first_search)

    def a_star_search_moves(self, best_moves: list[tuple]) -> list[tuple]:
        return self._route_moves(best_moves, Bot.a_star_search)

    def _load_model(self):
        """Nạp model một lần; ghi nhớ lỗi để không thử lại ở mỗi frame."""

        if self._model is not None:
            return self._model
        if self._model_unavailable:
            return None
        try:
            from tensorflow.keras.models import load_model

            self._model = load_model(self.model_path, compile=False)
        except (OSError, ValueError, ImportError) as error:
            self._model_unavailable = True
            warnings.warn(
                f"Không thể nạp model {self.model_path}: {error}", stacklevel=2
            )
        return self._model

    def ai_move(self):
        """Dự đoán batch và chọn max cho phe tối, min cho phe sáng."""

        model = self._load_model()
        moves = self.board.get_valid_moves(self.current_side)
        if model is None or not moves:
            return None

        encoded_boards = []
        for move in moves:
            candidate = self.board.copy()
            candidate.make_move(move)
            encoded_boards.append(encode_board(Log.board_to_enum(candidate)))
        batch = np.stack(encoded_boards, axis=0)[..., np.newaxis]
        scores = np.asarray(model.predict(batch, verbose=0)).reshape(-1)
        index = int(
            np.argmax(scores)
            if PlayerSide.is_dark(self.current_side)
            else np.argmin(scores)
        )
        return moves[index]

    @property
    def is_game_end(self) -> bool:
        if not self.board.is_game_over:
            return False
        winner = self.board.winner
        self.game_state = GameState.OVER
        self.game_result = f"{winner.upper()}\nWIN!!!" if winner else "DRAW"
        return True

    # Giữ API cũ: GameManager.encode_board/encode_piece vẫn gọi được như trước,
    # nhưng triển khai thật nay chỉ còn ở scripts.encoding (một nguồn sự thật).
    encode_piece = staticmethod(encode_piece)
    encode_board = staticmethod(encode_board)

    @staticmethod
    def algorithm_random(opponent_pieces: int) -> int:
        """Nghiêng về BFS khi đối phương còn nhiều quân; nghiêng về A* ở tàn cuộc."""

        bounded = max(0, min(8, opponent_pieces))
        return random.choice([1] * (8 + bounded * 2) + [2] * (24 - bounded * 2))
