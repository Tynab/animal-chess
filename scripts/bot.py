"""Các thuật toán quyết định nước đi cho bot.

Module cung cấp đánh giá vật chất, minimax, alpha-beta và hai thuật toán tìm
đường. Mỗi trạng thái tìm đường giữ một bản sao bàn riêng để không đặt cùng một
đối tượng quân lên nhiều ô như phiên bản cũ.
"""

from collections import deque
from heapq import heappop, heappush
from itertools import count

from scripts.common import PlayerSide


class Bot:
    """Nhóm thuật toán thuần, không lưu trạng thái giữa các lượt."""

    @staticmethod
    def evaluate_position(board, current_side: str) -> int:
        """Chấm điểm từ góc nhìn ``current_side`` theo hang và tổng cấp quân."""

        score = 0
        if board.is_opponent_den_invaded(current_side):
            score += 900
        if board.is_opponent_den_invaded(PlayerSide.opponent_of(current_side)):
            score -= 900
        for piece in board.pieces:
            value = piece.atk * 10
            score += value if piece.side == current_side else -value
        return score

    @staticmethod
    def minimax(board, current_side: str, depth: int, maximizing_player: bool):
        """Duyệt cây trò chơi minimax và trả về mọi nước đồng điểm tốt nhất."""

        if depth == 0 or board.is_game_over:
            return Bot.evaluate_position(board, current_side), []

        player_side = (
            current_side if maximizing_player else PlayerSide.opponent_of(current_side)
        )
        moves = board.get_valid_moves(player_side)
        if not moves:
            return Bot.evaluate_position(board, current_side), []

        best_score = float("-inf") if maximizing_player else float("inf")
        best_moves = []
        for move in moves:
            board.make_move(move)
            score, _ = Bot.minimax(
                board, current_side, depth - 1, not maximizing_player
            )
            board.undo_move(move)

            is_better = score > best_score if maximizing_player else score < best_score
            if is_better:
                best_score, best_moves = score, [move]
            elif score == best_score:
                best_moves.append(move)
        return best_score, best_moves

    @staticmethod
    def minimax_alpha_beta_pruning(
        board,
        current_side: str,
        depth: int,
        alpha: float,
        beta: float,
        maximizing_player: bool,
    ):
        """Minimax có cắt tỉa alpha-beta để giảm số trạng thái cần duyệt."""

        if depth == 0 or board.is_game_over:
            return Bot.evaluate_position(board, current_side), []

        player_side = (
            current_side if maximizing_player else PlayerSide.opponent_of(current_side)
        )
        moves = board.get_valid_moves(player_side)
        if not moves:
            return Bot.evaluate_position(board, current_side), []

        best_score = float("-inf") if maximizing_player else float("inf")
        best_moves = []
        for move in moves:
            board.make_move(move)
            score, _ = Bot.minimax_alpha_beta_pruning(
                board, current_side, depth - 1, alpha, beta, not maximizing_player
            )
            board.undo_move(move)

            is_better = score > best_score if maximizing_player else score < best_score
            if is_better:
                best_score, best_moves = score, [move]
            elif score == best_score:
                best_moves.append(move)

            if maximizing_player:
                alpha = max(alpha, score)
            else:
                beta = min(beta, score)
            if alpha >= beta:
                break
        return best_score, best_moves

    @staticmethod
    def breadth_first_search(board, piece, start: tuple[int, int], ends: list):
        """Tìm đường ngắn nhất tới từng mục tiêu bằng BFS trên trạng thái độc lập."""

        targets = set(ends)
        if not targets:
            return None, None
        queue = deque([(board.copy(), start, [start])])
        visited = {start}
        paths = []

        while queue and targets:
            state, position, path = queue.popleft()
            if position in targets:
                paths.append((len(path) - 1, path))
                targets.remove(position)

            moving_piece = state.get_cell(position).piece
            if moving_piece is None:
                continue
            for cell in moving_piece.available_cells(state):
                next_position = cell.position
                if next_position in visited:
                    continue
                visited.add(next_position)
                next_state = state.copy()
                next_state.make_move((position, next_position))
                queue.append((next_state, next_position, [*path, next_position]))

        paths.sort(key=lambda item: item[0])
        return paths or None, None

    @staticmethod
    def a_star_search(board, piece, start: tuple[int, int], ends: list):
        """Tìm đường A* với khoảng cách Manhattan tới mục tiêu gần nhất."""

        targets = set(ends)
        if not targets:
            return None, None

        def heuristic(position: tuple[int, int]) -> int:
            x, y = position
            return min(abs(x - tx) + abs(y - ty) for tx, ty in targets)

        serial = count()
        queue = []
        heappush(
            queue, (heuristic(start), next(serial), 0, start, [start], board.copy())
        )
        best_cost = {start: 0}
        paths = []

        while queue and targets:
            _, _, path_cost, position, path, state = heappop(queue)
            if position in targets:
                paths.append((path_cost, path))
                targets.remove(position)
                if not targets:
                    break

            moving_piece = state.get_cell(position).piece
            if moving_piece is None:
                continue
            for cell in moving_piece.available_cells(state):
                next_position = cell.position
                new_cost = path_cost + 1
                if new_cost >= best_cost.get(next_position, float("inf")):
                    continue
                best_cost[next_position] = new_cost
                next_state = state.copy()
                next_state.make_move((position, next_position))
                priority = new_cost + heuristic(next_position)
                heappush(
                    queue,
                    (
                        priority,
                        next(serial),
                        new_cost,
                        next_position,
                        [*path, next_position],
                        next_state,
                    ),
                )

        paths.sort(key=lambda item: item[0])
        return paths or None, None
