"""Engine tìm kiếm alpha-beta sâu cho Animal Chess.

Iterative deepening + negamax alpha-beta + transposition table (Zobrist) + sắp
xếp nước (TT move, MVV-LVA, killer, history) + quiescence. Eval nhanh
``search_eval`` = ``Bot.evaluate_position`` + gradient tiến-về-hang. KHÔNG đụng
``Bot.minimax``/``evaluate_position`` (giữ smoke/bot_golden)."""
import random
import time

from scripts.bot import Bot
from scripts.common import H, PlayerSide, W

INF = 10**9
_EXACT, _LOWER, _UPPER = 0, 1, 2

_Z_CELLS = None
_Z_SIDE = None


def _init_zobrist() -> None:
    global _Z_CELLS, _Z_SIDE
    rng = random.Random(20240526)  # seed cố định -> khoá tái lập giữa các lần chạy
    _Z_CELLS = [[rng.getrandbits(64) for _ in range(16)] for _ in range(W * H)]
    _Z_SIDE = rng.getrandbits(64)


def _piece_kind(piece) -> int:
    # (phe, cấp) định danh duy nhất một loại quân: dark 0..7, light 8..15.
    side_offset = 0 if PlayerSide.is_dark(piece.side) else 8
    return side_offset + (piece.base_atk - 1)


def zobrist_key(board, side) -> int:
    """Khoá Zobrist của thế cờ (vị trí quân + phe đi); atk-bẫy là hàm của vị trí nên bỏ qua."""
    if _Z_CELLS is None:
        _init_zobrist()
    key = 0
    for piece in board.pieces:
        x, y = piece.position
        key ^= _Z_CELLS[x * H + y][_piece_kind(piece)]
    if PlayerSide.is_light(side):
        key ^= _Z_SIDE
    return key


_MAX_DIST = (W - 1) + (H - 1)


def _den_gradient(board, side, coef) -> int:
    """Thưởng nhỏ khi quân ta tiến gần hang địch; trừ đối xứng cho quân địch. Góc nhìn `side`."""
    if not coef:
        return 0
    mtx, mty = PlayerSide.opponent_den_position(side)                              # hang địch
    otx, oty = PlayerSide.opponent_den_position(PlayerSide.opponent_of(side))      # hang ta
    total = 0
    for piece in board.pieces:
        px, py = piece.position
        if piece.side == side:
            total += coef * (_MAX_DIST - abs(px - mtx) - abs(py - mty))
        else:
            total -= coef * (_MAX_DIST - abs(px - otx) - abs(py - oty))
    return total


def search_eval(board, side, gradient_coef=1) -> int:
    """Điểm thế cờ theo góc nhìn `side` = vật chất+hang + gradient nhỏ."""
    return Bot.evaluate_position(board, side) + _den_gradient(board, side, gradient_coef)


class SearchEngine:
    """Alpha-beta iterative-deepening có TT; dùng search_eval làm đánh giá lá."""

    def __init__(self, time_budget_s=1.0, max_depth=None, tt_size=2**20,
                 gradient_coef=1, quiescence=True) -> None:
        self.time_budget_s = time_budget_s
        self.max_depth = max_depth
        self.tt_size = tt_size
        self.gradient_coef = gradient_coef
        self.quiescence = quiescence
        self.tt = {}
        self.killers = {}
        self.history = {}
        self.nodes = 0
        self._deadline = None

    def _ordered(self, board, side, moves, tt_move, ply):
        killers = self.killers.get(ply, ())

        def key(mv):
            if mv == tt_move:
                return 10**9
            victim = board.get_cell(mv[1]).piece
            if victim is not None:                       # ăn quân: MVV-LVA
                attacker = board.get_cell(mv[0]).piece
                return 10**6 + victim.base_atk * 16 - attacker.base_atk
            if mv in killers:
                return 10**5
            return self.history.get((side, mv), 0)

        return sorted(moves, key=key, reverse=True)

    def _quiescence(self, board, side, alpha, beta):
        self.nodes += 1
        stand = search_eval(board, side, self.gradient_coef)
        if board.is_game_over or stand >= beta:
            return beta if stand >= beta else stand
        if stand > alpha:
            alpha = stand
        for mv in board.get_valid_moves(side):
            if board.get_cell(mv[1]).piece is None:      # chỉ đào nước ăn quân
                continue
            board.make_move(mv)
            try:
                val = -self._quiescence(board, PlayerSide.opponent_of(side), -beta, -alpha)
            finally:
                board.undo_move(mv)
            if val >= beta:
                return beta
            if val > alpha:
                alpha = val
        return alpha

    def _negamax(self, board, side, depth, alpha, beta, ply):
        self.nodes += 1
        if self._deadline is not None and time.perf_counter() > self._deadline:
            raise TimeoutError
        alpha_orig = alpha
        key = zobrist_key(board, side)
        entry = self.tt.get(key)
        tt_move = entry[3] if entry is not None else None
        if entry is not None and entry[0] >= depth:
            _, val, flag, _ = entry
            if flag == _EXACT:
                return val
            if flag == _LOWER and val > alpha:
                alpha = val
            elif flag == _UPPER and val < beta:
                beta = val
            if alpha >= beta:
                return val

        if board.is_game_over:
            return search_eval(board, side, self.gradient_coef)
        if depth == 0:
            if self.quiescence:
                return self._quiescence(board, side, alpha, beta)
            return search_eval(board, side, self.gradient_coef)

        moves = board.get_valid_moves(side)
        if not moves:
            return search_eval(board, side, self.gradient_coef)

        best_val, best_move = -INF, None
        for mv in self._ordered(board, side, moves, tt_move, ply):
            board.make_move(mv)
            try:
                val = -self._negamax(board, PlayerSide.opponent_of(side), depth - 1, -beta, -alpha, ply + 1)
            finally:
                board.undo_move(mv)
            if val > best_val:
                best_val, best_move = val, mv
            if val > alpha:
                alpha = val
            if alpha >= beta:
                if board.get_cell(mv[1]).piece is None:   # nước "yên" -> killer/history
                    self.killers[ply] = (mv,) + self.killers.get(ply, ())[:1]
                    self.history[(side, mv)] = self.history.get((side, mv), 0) + depth * depth
                break

        flag = _EXACT
        if best_val <= alpha_orig:
            flag = _UPPER
        elif best_val >= beta:
            flag = _LOWER
        if len(self.tt) >= self.tt_size:
            self.tt.clear()                               # thay-toàn-bộ đơn giản khi TT đầy
        self.tt[key] = (depth, best_val, flag, best_move)
        return best_val

    def value(self, board, side, depth):
        """Giá trị negamax ở độ sâu cố định (không ngân sách) — dùng cho test tương đương minimax."""
        self._deadline = None
        return self._negamax(board, side, depth, -INF, INF, 0)

    def best_move(self, board, side):
        """Iterative deepening tới khi hết ngân sách thời gian / chạm max_depth; trả (move, info)."""
        self.nodes = 0
        self.tt.clear()
        self.killers.clear()
        self.history.clear()
        self._deadline = time.perf_counter() + self.time_budget_s if self.time_budget_s else None
        moves = board.get_valid_moves(side)
        if not moves:
            return None, {"depth": 0, "score": None, "nodes": 0, "pv": []}
        best = moves[0]
        info = {"depth": 0, "score": None, "nodes": 0, "pv": [best]}
        cap = self.max_depth or 64
        opponent = PlayerSide.opponent_of(side)
        depth = 1
        while depth <= cap:
            try:
                alpha, local_best, local_score = -INF, best, -INF
                tt_entry = self.tt.get(zobrist_key(board, side))
                tt_move = tt_entry[3] if tt_entry else best
                for mv in self._ordered(board, side, moves, tt_move, 0):
                    board.make_move(mv)
                    try:
                        val = -self._negamax(board, opponent, depth - 1, -INF, -alpha, 1)
                    finally:
                        board.undo_move(mv)
                    if val > local_score:
                        local_score, local_best = val, mv
                    if val > alpha:
                        alpha = val
                best = local_best
                info = {"depth": depth, "score": local_score, "nodes": self.nodes, "pv": [best]}
            except TimeoutError:
                break
            depth += 1
        return best, info
