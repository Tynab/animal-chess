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
        # Thưởng/phạt nặng (900 điểm) nếu hang đối phương bị chiếm hoặc hang
        # mình bị chiếm — đây là điều kiện thắng/thua nên trọng số rất lớn.
        if board.is_opponent_den_invaded(current_side):
            score += 900
        if board.is_opponent_den_invaded(PlayerSide.opponent_of(current_side)):
            score -= 900
        # Cộng dồn giá trị vật chất: mỗi quân của current_side cộng điểm
        # theo cấp tấn công (atk * 10), quân đối phương trừ điểm tương ứng.
        for piece in board.pieces:
            value = piece.atk * 10
            score += value if piece.side == current_side else -value
        return score

    @staticmethod
    def _search(
        board,
        current_side: str,
        depth: int,
        maximizing_player: bool,
        alpha: float,
        beta: float,
        prune: bool,
    ):
        """Lõi duyệt cây dùng chung cho ``minimax`` và ``minimax_alpha_beta_pruning``.

        Hàm private này gộp phần "đi bộ" cây trò chơi giống hệt nhau giữa hai
        thuật toán công khai: kiểm tra điều kiện dừng, sinh nước đi cho bên
        đang đi, vòng lặp make_move → đệ quy (depth - 1, đảo bên) → undo_move,
        rồi gom điểm/nước tốt nhất (điểm tốt hơn hẳn thì thay thế, bằng điểm
        thì thêm vào tập đồng điểm). Cờ ``prune`` (True/False) là điểm khác
        biệt DUY NHẤT: chỉ khi bật cắt tỉa mới cập nhật alpha/beta và cắt
        nhánh (``alpha >= beta``) — nhờ vậy alpha-beta có thể trả về tập
        đồng điểm NHỎ HƠN minimax thường (do cắt bớt nhánh hòa điểm), còn khi
        ``prune=False`` hành vi tương đương minimax nguyên bản không cắt tỉa.
        """

        # Điều kiện dừng: hết độ sâu hoặc ván đã kết thúc → chấm điểm lá.
        if depth == 0 or board.is_game_over:
            return Bot.evaluate_position(board, current_side), []

        # Xác định bên đang đi: nếu đang ở lượt "maximizing" thì đó là
        # current_side, ngược lại là đối thủ của current_side.
        player_side = (
            current_side if maximizing_player else PlayerSide.opponent_of(current_side)
        )
        moves = board.get_valid_moves(player_side)
        if not moves:
            return Bot.evaluate_position(board, current_side), []

        # Khởi tạo điểm tốt nhất: -inf nếu đang tối đa hóa, +inf nếu tối
        # thiểu hóa, để so sánh đầu tiên luôn "thắng".
        best_score = float("-inf") if maximizing_player else float("inf")
        best_moves = []
        for move in moves:
            # Thử nước đi, đệ quy tính điểm ở độ sâu thấp hơn với bên đảo
            # ngược, rồi hoàn tác để trả bàn cờ về trạng thái ban đầu.
            board.make_move(move)
            score, _ = Bot._search(
                board, current_side, depth - 1, not maximizing_player, alpha, beta, prune
            )
            board.undo_move(move)

            # So sánh điểm: tốt hơn hẳn thì thay hoàn toàn tập nước đi tốt
            # nhất bằng nước hiện tại; bằng điểm thì gộp thêm vào tập đồng
            # điểm (đây là tập best_moves có thể chứa nhiều nước ngang nhau).
            is_better = score > best_score if maximizing_player else score < best_score
            if is_better:
                best_score, best_moves = score, [move]
            elif score == best_score:
                best_moves.append(move)

            # Chỉ khi bật cắt tỉa mới cập nhật alpha/beta và kiểm tra điều
            # kiện cắt nhánh; minimax thường (prune=False) bỏ qua bước này
            # nên luôn duyệt hết mọi nước đi, không bao giờ break sớm.
            if prune:
                if maximizing_player:
                    alpha = max(alpha, score)
                else:
                    beta = min(beta, score)
                if alpha >= beta:
                    break
        return best_score, best_moves

    @staticmethod
    def minimax(board, current_side: str, depth: int, maximizing_player: bool):
        """Duyệt cây trò chơi minimax và trả về mọi nước đồng điểm tốt nhất.

        Ủy quyền toàn bộ phần duyệt cây cho ``_search`` với ``prune=False``;
        alpha/beta truyền vào chỉ là giá trị khởi tạo vô cực, không được sử
        dụng vì cờ cắt tỉa tắt nên không ảnh hưởng tới kết quả.
        """

        return Bot._search(
            board,
            current_side,
            depth,
            maximizing_player,
            float("-inf"),
            float("inf"),
            False,
        )

    @staticmethod
    def minimax_alpha_beta_pruning(
        board,
        current_side: str,
        depth: int,
        alpha: float,
        beta: float,
        maximizing_player: bool,
    ):
        """Minimax có cắt tỉa alpha-beta để giảm số trạng thái cần duyệt.

        Ủy quyền toàn bộ phần duyệt cây cho ``_search`` với ``prune=True`` và
        alpha/beta do người gọi cung cấp, giữ nguyên hành vi cắt tỉa gốc.
        """

        return Bot._search(
            board, current_side, depth, maximizing_player, alpha, beta, True
        )

    @staticmethod
    def breadth_first_search(board, piece, start: tuple[int, int], ends: list):
        """Tìm đường ngắn nhất tới từng mục tiêu bằng BFS trên trạng thái độc lập."""

        # Không có mục tiêu nào thì khỏi tìm.
        targets = set(ends)
        if not targets:
            return None, None
        # Mỗi phần tử hàng đợi mang theo BẢN SAO bàn cờ riêng (board.copy())
        # để tránh việc di chuyển quân "ảo" trong lúc dò đường làm ảnh hưởng
        # lẫn nhau giữa các nhánh đang xét song song trong BFS.
        queue = deque([(board.copy(), start, [start])])
        visited = {start}
        paths = []

        while queue and targets:
            # Lấy trạng thái đầu hàng đợi (FIFO) → đảm bảo tính chất BFS:
            # duyệt theo từng lớp khoảng cách tăng dần.
            state, position, path = queue.popleft()
            if position in targets:
                paths.append((len(path) - 1, path))
                targets.remove(position)

            moving_piece = state.get_cell(position).piece
            if moving_piece is None:
                continue
            # Mở rộng sang các ô quân có thể đi tới từ vị trí hiện tại, bỏ
            # qua ô đã thăm để tránh lặp vô hạn.
            for cell in moving_piece.available_cells(state):
                next_position = cell.position
                if next_position in visited:
                    continue
                visited.add(next_position)
                # Nhân bản trạng thái rồi thực hiện nước đi trên bản sao đó
                # (không đụng tới ``state`` gốc) để giữ mỗi nhánh độc lập.
                next_state = state.copy()
                next_state.make_move((position, next_position))
                queue.append((next_state, next_position, [*path, next_position]))

        # Sắp xếp các đường tìm được theo độ dài tăng dần trước khi trả về.
        paths.sort(key=lambda item: item[0])
        return paths or None, None

    @staticmethod
    def a_star_search(board, piece, start: tuple[int, int], ends: list):
        """Tìm đường A* với khoảng cách Manhattan tới mục tiêu gần nhất."""

        targets = set(ends)
        if not targets:
            return None, None

        # Hàm heuristic: khoảng cách Manhattan tới mục tiêu GẦN NHẤT trong
        # tập targets còn lại — heuristic này admissible (không đánh giá quá
        # cao chi phí thật) nên A* vẫn đảm bảo tối ưu.
        def heuristic(position: tuple[int, int]) -> int:
            x, y = position
            return min(abs(x - tx) + abs(y - ty) for tx, ty in targets)

        # ``serial`` là bộ đếm dùng để phá vỡ thế bằng (tie-break) khi so
        # sánh các phần tử trong heap có cùng priority, tránh so sánh trực
        # tiếp các đối tượng state/path không hỗ trợ so sánh thứ tự.
        serial = count()
        queue = []
        # Mỗi phần tử heap: (priority ưu tiên, serial, chi phí thật đã đi,
        # vị trí, đường đi, bản sao bàn cờ độc lập của nhánh này).
        heappush(
            queue, (heuristic(start), next(serial), 0, start, [start], board.copy())
        )
        best_cost = {start: 0}
        paths = []

        while queue and targets:
            # Lấy phần tử có priority (f = g + h) nhỏ nhất — đặc trưng A*.
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
                # Chỉ mở rộng nếu tìm được đường tới ``next_position`` rẻ
                # hơn chi phí tốt nhất đã ghi nhận trước đó (relaxation).
                if new_cost >= best_cost.get(next_position, float("inf")):
                    continue
                best_cost[next_position] = new_cost
                # Nhân bản trạng thái cho nhánh mới, thực hiện nước đi trên
                # bản sao để không ảnh hưởng các nhánh khác trong hàng đợi.
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

        # Sắp xếp các đường tìm được theo chi phí tăng dần trước khi trả về.
        paths.sort(key=lambda item: item[0])
        return paths or None, None
