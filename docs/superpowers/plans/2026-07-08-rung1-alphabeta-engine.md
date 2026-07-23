# Rung 1 — Deep Alpha-Beta Search Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the bot a real iterative-deepening alpha-beta engine (transposition table, move ordering, quiescence, time budget) with a fast heuristic+gradient eval, make it the primary move selector, and prove it beats the current bot.

**Architecture:** New `scripts/search.py` holds a `SearchEngine` (negamax alpha-beta + Zobrist TT + ordering + quiescence + iterative deepening) and `search_eval` (= `Bot.evaluate_position` + a side-relative den-gradient). `GameManager.autoplay` and `tools/selfplay.py` switch to it; `Bot.minimax`/`evaluate_position` are untouched (kept as the correctness reference + baseline). Verified by `tools/perft.py` (make/undo + move-gen integrity) and `tools/strength.py` (engine vs the current CNN bot).

**Tech Stack:** Python 3.11 (Windows, `py`), NumPy/TensorFlow (only for the CNN baseline in the strength arena), stdlib `time`/`random`.

## Global Constraints

- **`z`/format invariants:** do NOT change the 63-char board string, `scripts/encoding.py`, `PIECE_ENCODING`, CSV schema, or the `.h5` models. `tools/smoke_test.py` stays `SMOKE_OK`.
- **Do NOT touch** `Bot.minimax`, `Bot.minimax_alpha_beta_pruning`, `Bot.evaluate_position`, BFS/A* — they are the correctness reference and baseline; `bot_golden` must still pass.
- **Eval:** `search_eval(board, side, gradient_coef=1)` = `Bot.evaluate_position(board, side)` + a side-relative den-gradient; with `gradient_coef=0` it must equal `Bot.evaluate_position(board, side)` exactly.
- **Correctness anchor:** with `gradient_coef=0` and `quiescence=False`, `SearchEngine.value(board, side, depth)` MUST equal `Bot.minimax(board, side, depth, True)[0]` (alpha-beta preserves the minimax value; `evaluate_position` is perfectly antisymmetric so negamax ≡ minimax).
- **Perft goldens** (initial board, LIGHT to move): depth 1 = **24**, depth 2 = **576**, depth 3 = **12264**; a full perft leaves the board string identical (undo symmetry).
- **Primary policy:** `GameManager.autoplay` uses `SearchEngine.best_move`; `ai_move`/`computer_move` are kept (arena/baseline) but no longer default. Self-play uses the engine at a fixed `SELFPLAY_MAX_DEPTH` (default 4).
- **Config env:** `SEARCH_TIME_S=1.0`, `SEARCH_MAX_DEPTH` (optional), `SELFPLAY_MAX_DEPTH=4`, `STRENGTH_GAMES=200`, `STRENGTH_SEARCH_TIME`.
- **Style:** Vietnamese comments; `py -m ruff check` and `py -m compileall` clean over `main.py scripts tools`.

---

### Task 1: `tools/perft.py` — make/undo + move-gen integrity harness

**Files:**
- Create: `tools/perft.py`, `tools/test_perft.py`

**Interfaces:**
- Produces: `perft(board, side, depth) -> int` (counts leaf nodes via `make_move`/`undo_move` + `get_valid_moves`). Consumed only by its test + humans.

- [ ] **Step 1: Write the failing test**

```python
# tools/test_perft.py
"""Kiểm thử perft: số node lá cố định + make/undo đối xứng (chuỗi bàn không đổi)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.board import Board
from scripts.common import PlayerSide
from scripts.log import Log
from tools.perft import perft


def main() -> int:
    b = Board(is_copy=True)
    before = Log.board_to_enum(b)
    ok = True
    for depth, want in ((1, 24), (2, 576), (3, 12264)):
        got = perft(b, PlayerSide.LIGHT, depth)
        if got != want:
            ok = False
            print(f"[SAI] perft d{depth}: want {want} got {got}")
    if Log.board_to_enum(b) != before:
        ok = False
        print("[SAI] make/undo không khôi phục bàn (chuỗi bàn đổi sau perft)")
    print("PERFT_OK" if ok else "PERFT_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `py tools/test_perft.py` → FAIL (`ModuleNotFoundError: No module named 'tools.perft'`).

- [ ] **Step 3: Write `tools/perft.py`**

```python
# tools/perft.py
"""Perft: đếm số node lá ở độ sâu N qua make_move/undo_move + get_valid_moves.

Dùng để tin cậy tính đúng của bộ sinh nước + tính đối xứng make/undo mà engine
alpha-beta phụ thuộc. Không nằm trên đường chơi."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ruff: noqa: E402
from scripts.common import PlayerSide


def perft(board, side, depth: int) -> int:
    """Số chuỗi nước hợp lệ độ dài `depth` từ thế cờ hiện tại (khôi phục bàn khi xong)."""
    if depth == 0:
        return 1
    total = 0
    opponent = PlayerSide.opponent_of(side)
    for move in board.get_valid_moves(side):
        board.make_move(move)
        total += perft(board, opponent, depth - 1)
        board.undo_move(move)
    return total


if __name__ == "__main__":
    from scripts.board import Board
    b = Board(is_copy=True)
    for d in (1, 2, 3):
        print(f"perft(initial, LIGHT, {d}) = {perft(b, PlayerSide.LIGHT, d)}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py tools/test_perft.py` → `PERFT_OK`, exit 0.

- [ ] **Step 5: Lint + commit**

Run: `py -m ruff check tools/perft.py tools/test_perft.py` → clean
```bash
git add tools/perft.py tools/test_perft.py
git commit -m "test: add perft harness (golden node counts + make/undo round-trip)"
```

---

### Task 2: `scripts/search.py` — the alpha-beta engine

**Files:**
- Create: `scripts/search.py`, `tools/test_search.py`

**Interfaces:**
- Consumes: `Bot.evaluate_position`, `make_move`/`undo_move`, `get_valid_moves`, `PlayerSide`, `common.W/H`.
- Produces: `zobrist_key(board, side) -> int`; `search_eval(board, side, gradient_coef=1) -> int`; `SearchEngine(time_budget_s=1.0, max_depth=None, tt_size=2**20, gradient_coef=1, quiescence=True)` with `.best_move(board, side) -> (move, info)` and `.value(board, side, depth) -> int`.

- [ ] **Step 1: Write the failing test**

```python
# tools/test_search.py
"""Kiểm thử engine: zobrist, search_eval, tương đương Bot.minimax, ngân sách."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.board import Board
from scripts.bot import Bot
from scripts.common import PlayerSide
from scripts.search import SearchEngine, search_eval, zobrist_key


def _advance(board, side, plies):
    # Tạo thế cờ tái lập: luôn đi nước hợp lệ đầu tiên.
    for _ in range(plies):
        moves = board.get_valid_moves(side)
        if not moves:
            break
        board.make_move(moves[0])
        side = PlayerSide.opponent_of(side)
    return side


def main() -> int:
    ok = True
    b = Board(is_copy=True)

    # 1) Zobrist: ổn định, nhạy phe, bất biến qua make+undo.
    k1 = zobrist_key(b, PlayerSide.LIGHT)
    if zobrist_key(b, PlayerSide.LIGHT) != k1:
        ok = False; print("[SAI] zobrist không ổn định")
    if zobrist_key(b, PlayerSide.DARK) == k1:
        ok = False; print("[SAI] zobrist không phân biệt phe")
    mv = b.get_valid_moves(PlayerSide.LIGHT)[0]
    b.make_move(mv); b.undo_move(mv)
    if zobrist_key(b, PlayerSide.LIGHT) != k1:
        ok = False; print("[SAI] zobrist đổi sau make+undo")

    # 2) search_eval: gradient=0 -> đúng bằng evaluate_position.
    if search_eval(b, PlayerSide.DARK, 0) != Bot.evaluate_position(b, PlayerSide.DARK):
        ok = False; print("[SAI] search_eval(gradient=0) != evaluate_position")

    # 3) Tương đương Bot.minimax (gradient=0, quiescence=off) trên vài thế cờ/độ sâu.
    eng = SearchEngine(gradient_coef=0, quiescence=False)
    for plies in (0, 2, 4):
        pos = Board(is_copy=True)
        side = _advance(pos, PlayerSide.LIGHT, plies)
        for depth in (1, 2, 3):
            got = eng.value(pos, side, depth)
            want = Bot.minimax(pos, side, depth, True)[0]
            if got != want:
                ok = False
                print(f"[SAI] value!=minimax plies={plies} d{depth}: {got} vs {want}")

    # 4) best_move trả nước hợp lệ trong ngân sách; max_depth được tôn trọng.
    eng2 = SearchEngine(time_budget_s=0.3)
    move, info = eng2.best_move(Board(is_copy=True), PlayerSide.LIGHT)
    if move not in Board(is_copy=True).get_valid_moves(PlayerSide.LIGHT):
        ok = False; print("[SAI] best_move trả nước không hợp lệ")
    if info["depth"] < 1:
        ok = False; print("[SAI] best_move không đạt nổi depth 1")
    eng3 = SearchEngine(time_budget_s=None, max_depth=2)
    _, info3 = eng3.best_move(Board(is_copy=True), PlayerSide.LIGHT)
    if info3["depth"] != 2:
        ok = False; print(f"[SAI] max_depth không tôn trọng: {info3['depth']}")

    print("SEARCH_OK" if ok else "SEARCH_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `py tools/test_search.py` → FAIL (`ModuleNotFoundError: No module named 'scripts.search'`).

- [ ] **Step 3: Write `scripts/search.py`**

```python
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
            val = -self._quiescence(board, PlayerSide.opponent_of(side), -beta, -alpha)
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
            val = -self._negamax(board, PlayerSide.opponent_of(side), depth - 1, -beta, -alpha, ply + 1)
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
                    val = -self._negamax(board, opponent, depth - 1, -INF, -alpha, 1)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py tools/test_search.py` → `SEARCH_OK`, exit 0. (If the equivalence check fails, the alpha-beta/TT has a bug — the value MUST match `Bot.minimax`; fix until it does.)

- [ ] **Step 5: Engine untouched-reference + lint**

Run: `py tools/smoke_test.py` → `SMOKE_OK` (Bot.minimax untouched).
Run: `py -m compileall -q scripts/search.py tools/test_search.py` → no errors.
Run: `py -m ruff check scripts/search.py tools/test_search.py` → clean.

- [ ] **Step 6: Commit**

```bash
git add scripts/search.py tools/test_search.py
git commit -m "feat: add deep alpha-beta search engine (TT/ordering/quiescence/ID)"
```

---

### Task 3: Wire the engine as primary (`manager.py` + `selfplay.py`)

**Files:**
- Modify: `scripts/manager.py` (autoplay uses the engine; `ai_move`/`computer_move` kept)
- Modify: `tools/selfplay.py` (generator uses the engine at `SELFPLAY_MAX_DEPTH`)

**Interfaces:**
- Consumes: `SearchEngine` (Task 2).
- Produces: `GameManager.engine` (a `SearchEngine`); `autoplay` selects via it. `selfplay.generate` uses a `SearchEngine(max_depth=SELFPLAY_MAX_DEPTH, time_budget_s=None)`.

- [ ] **Step 1: `GameManager` — construct + use the engine**

In `scripts/manager.py`, add `import os` (if absent) and `from scripts.search import SearchEngine`. In `GameManager.__init__`, add:
```python
        self.engine = SearchEngine(time_budget_s=float(os.getenv("SEARCH_TIME_S", "1.0")))
```
Replace the `autoplay` move selection line `move = self.ai_move() or self.computer_move()` with:
```python
        move, _ = self.engine.best_move(self.board, self.current_side)
```
Keep `ai_move`, `computer_move`, `ModelEvaluator`, and all routing methods unchanged (used by the arenas).

- [ ] **Step 2: `selfplay.py` — generate with the engine**

In `tools/selfplay.py`, import `from scripts.search import SearchEngine`, read `SELFPLAY_MAX_DEPTH = int(os.getenv("SELFPLAY_MAX_DEPTH", "4"))`, construct one engine `engine = SearchEngine(time_budget_s=None, max_depth=SELFPLAY_MAX_DEPTH)` in `generate()`, and in `_play_one_game` replace the non-opening branch `move = gm.computer_move()` with:
```python
            move, _ = engine.best_move(gm.board, gm.current_side)
```
(Pass `engine` into `_play_one_game`.) Keep opening randomization, the ply cap, and `Log` logging unchanged.

- [ ] **Step 3: Gate — engine drives play, headless, fast**

Run (autoplay uses the engine; use a fast engine for the check):
```bash
SDL_VIDEODRIVER=dummy py -c "
import os; os.environ['SEARCH_TIME_S']='0.05'
from scripts.common import GameMode, GameState
from scripts.manager import GameManager
from scripts.search import SearchEngine
from scripts.board import Board
gm = GameManager(GameMode.CvC); gm.board = Board(is_copy=True); gm.engine = SearchEngine(time_budget_s=None, max_depth=2)
from scripts.common import PlayerSide
gm.current_side, gm.opponent_side = PlayerSide.LIGHT, PlayerSide.DARK
n=0
for _ in range(12):
    if not gm.board.is_game_over:
        mv,_=gm.engine.best_move(gm.board, gm.current_side)
        assert mv in gm.board.get_valid_moves(gm.current_side)
        gm.board.make_move(mv); n+=1
        gm.current_side, gm.opponent_side = gm.opponent_side, gm.current_side
print('ENGINE_PLAY_OK plies', n)
" 2>&1 | tail -1
```
Expected: `ENGINE_PLAY_OK plies 12`.

Run self-play smoke: `SELFPLAY_SEED=1 SELFPLAY_GAMES=4 MAX_PLIES=60 SELFPLAY_MAX_DEPTH=2 py tools/selfplay.py` → `SELFPLAY_DONE ...`, exit 0.

Run: `py tools/smoke_test.py` → `SMOKE_OK`; `py -m ruff check scripts/manager.py tools/selfplay.py` → clean.

- [ ] **Step 4: Commit**

```bash
git add scripts/manager.py tools/selfplay.py
git commit -m "feat: use deep search engine as primary policy (autoplay + self-play)"
```

---

### Task 4: `tools/strength.py` — engine-vs-current-bot arena

**Files:**
- Create: `tools/strength.py`, `tools/test_strength.py`

**Interfaces:**
- Consumes: `SearchEngine`, `ModelEvaluator`, `Board`, `PlayerSide`, and `one_sided_binom_p` from `tools.arena`.
- Produces: `play_strength(engine_factory, baseline_eval, games, max_plies, opening_random_plies) -> dict` and a CLI reporting `STRENGTH_PROMOTE`/`STRENGTH_NO`.

- [ ] **Step 1: Write the failing stats/import test**

```python
# tools/test_strength.py
"""Kiểm thử tiện ích strength: tái dùng thống kê nhị thức + import chạy được."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.strength import one_sided_binom_p


def main() -> int:
    ok = True
    if abs(one_sided_binom_p(160, 200) - 0.0) > 1e-6 and one_sided_binom_p(160, 200) >= 1e-6:
        ok = False
        print("[SAI] 160/200 phải rất nhỏ")
    if one_sided_binom_p(160, 200) >= 0.05:
        ok = False
        print("[SAI] 160/200 (80%) phải <0.05")
    print("STRENGTH_STATS_OK" if ok else "STRENGTH_STATS_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `py tools/test_strength.py` → FAIL (`ModuleNotFoundError: No module named 'tools.strength'`).

- [ ] **Step 3: Write `tools/strength.py`**

```python
# tools/strength.py
"""Đấu ENGINE (alpha-beta sâu) vs bot CNN hiện tại để đo Rung 1 có mạnh hơn không.

Thành công = engine đạt score >= 0.80 và nhị thức một phía p<0.05. Tái dùng
one_sided_binom_p của arena. Headless, có random khai cuộc + ply-cap."""
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from scripts.board import Board
from scripts.common import BEST_MODEL_PATH, PlayerSide
from scripts.manager import ModelEvaluator
from scripts.search import SearchEngine
from tools.arena import one_sided_binom_p


def _play_game(engine, evaluator, engine_side, max_plies, opening_random_plies):
    board = Board(is_copy=True)
    side = PlayerSide.LIGHT
    for ply in range(max_plies):
        if board.is_game_over:
            break
        if ply < opening_random_plies:
            moves = board.get_valid_moves(side)
            if not moves:
                break
            move = random.choice(moves)
        elif side == engine_side:
            move, _ = engine.best_move(board, side)
        else:
            move = evaluator.best_move(board, side)
        if move is None:
            break
        board.make_move(move)
        if board.is_game_over:
            break
        side = PlayerSide.opponent_of(side)
    winner = board.winner
    if winner is None:
        return "draw"
    return "engine" if winner == engine_side else "baseline"


def play_strength(search_time, max_depth, games, max_plies, opening_random_plies, model_path):
    evaluator = ModelEvaluator(model_path)
    engine = SearchEngine(time_budget_s=search_time, max_depth=max_depth)
    ew = bw = draws = 0
    for i in range(games):
        engine_side = PlayerSide.DARK if i % 2 == 0 else PlayerSide.LIGHT
        r = _play_game(engine, evaluator, engine_side, max_plies, opening_random_plies)
        if r == "engine":
            ew += 1
        elif r == "baseline":
            bw += 1
        else:
            draws += 1
    score = (ew + 0.5 * draws) / games if games else 0.0
    decisive = ew + bw
    p = one_sided_binom_p(ew, decisive)
    return {"engine_wins": ew, "baseline_wins": bw, "draws": draws,
            "score": score, "p_value": p, "pass": bool(score >= 0.80 and p < 0.05)}


def main() -> int:
    games = int(os.getenv("STRENGTH_GAMES", "200"))
    max_plies = int(os.getenv("MAX_PLIES", "300"))
    opening = int(os.getenv("OPENING_RANDOM_PLIES", "6"))
    search_time = os.getenv("STRENGTH_SEARCH_TIME")
    search_time = float(search_time) if search_time else None
    max_depth = int(os.getenv("STRENGTH_MAX_DEPTH", "4")) if search_time is None else None
    seed = os.getenv("STRENGTH_SEED")
    if seed is not None:
        random.seed(int(seed))
    res = play_strength(search_time, max_depth, games, max_plies, opening,
                        os.getenv("BASELINE_MODEL", str(BEST_MODEL_PATH)))
    print(f"engine_wins={res['engine_wins']} baseline_wins={res['baseline_wins']} draws={res['draws']}")
    print(f"score={res['score']:.4f} p={res['p_value']:.4g} pass={res['pass']}")
    print("STRENGTH_PROMOTE" if res["pass"] else "STRENGTH_NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the stats test to pass**

Run: `py tools/test_strength.py` → `STRENGTH_STATS_OK`, exit 0.

- [ ] **Step 5: Tiny smoke run (engine vs CNN, few games, shallow)**

Run: `STRENGTH_SEED=1 STRENGTH_GAMES=4 MAX_PLIES=60 STRENGTH_MAX_DEPTH=2 py tools/strength.py` → prints an `engine_wins/…` line + `score=…` + `STRENGTH_PROMOTE`/`STRENGTH_NO`, exit 0. (This proves the runner works; the real 200-game run is the manual success metric.)

- [ ] **Step 6: Lint + commit**

Run: `py -m ruff check tools/strength.py tools/test_strength.py` → clean.
```bash
git add tools/strength.py tools/test_strength.py
git commit -m "feat: add engine-vs-CNN strength arena (>=0.80 promotion bar)"
```

---

### Task 5: Documentation + full verification

**Files:**
- Modify: `README.md`, `CLAUDE.md`

**Interfaces:** none (docs + verification).

- [ ] **Step 1: Document the engine in `CLAUDE.md`**

In the "Cách máy chọn nước đi" / bot area, add:
```markdown
- **Rung 1 (deep search, primary):** `scripts/search.py` `SearchEngine` — iterative-deepening alpha-beta + Zobrist TT + move ordering + quiescence, eval = `Bot.evaluate_position` + a den-gradient. `GameManager.autoplay` and `tools/selfplay.py` use it (time budget `SEARCH_TIME_S`; self-play uses `SELFPLAY_MAX_DEPTH`). `Bot.minimax`/`evaluate_position` are kept untouched as the reference/baseline. Verify with `tools/perft.py` (make/undo integrity) + `tools/strength.py` (engine vs the CNN bot).
```

- [ ] **Step 2: Document in `README.md`**

Add a short subsection near the bot description noting the deep-search engine is now the primary move selector, with `py tools\strength.py` as the strength check and `SEARCH_TIME_S`/`SELFPLAY_MAX_DEPTH` knobs.

- [ ] **Step 3: Full verification**

Run each; all must pass:
- `py tools/test_perft.py` → `PERFT_OK`
- `py tools/test_search.py` → `SEARCH_OK`
- `py tools/test_strength.py` → `STRENGTH_STATS_OK`
- `py tools/smoke_test.py` → `SMOKE_OK` (engine reference untouched)
- `py -m compileall -q main.py scripts tools` → clean
- `py -m ruff check main.py scripts tools` → clean

- [ ] **Step 4: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: document the Rung 1 deep-search engine as primary policy"
```

---

## Self-Review

**Spec coverage:** §3.1 engine → Task 2. §3.2 primary-policy swap → Task 3. §3.3 self-play adoption → Task 3. §5 config env → Tasks 3/4. §6 perft → Task 1; strength arena → Task 4; smoke/bot_golden green → Tasks 2/3/5 gates. §2 "don't touch Bot.minimax/evaluate_position" → enforced (search.py is additive; gates run smoke). The eval-gradient (arena-tuned, 0=off) and drop-routing (autoplay no longer calls computer_move; routing code stays for the baseline) → Tasks 2/3. No gaps.

**Placeholder scan:** No TBD/TODO. The engine code is complete; the dead `ref = … if False` line in the Task 2 test was removed during self-review. All commands have concrete expected output. Perft goldens are real (24/576/12264).

**Type consistency:** `SearchEngine(time_budget_s, max_depth, tt_size, gradient_coef, quiescence)`, `.best_move(board, side)->(move, info)`, `.value(board, side, depth)->int`, `search_eval(board, side, gradient_coef)`, `zobrist_key(board, side)` — defined in Task 2, consumed identically in Tasks 3/4. `one_sided_binom_p(wins, decisive)` imported from `tools.arena` in Task 4 matches its Rung-3 definition. `ModelEvaluator(path).best_move(board, side)` matches manager.py.
