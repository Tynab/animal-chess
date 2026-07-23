# Rung 3 — Outcome-Based Value Target Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train the position evaluator on the actual game outcome `z` (not a hand-crafted heuristic) and prove it plays stronger via a head-to-head arena, without changing the interactive game or the board/encoder formats.

**Architecture:** A headless self-play generator (`tools/selfplay.py`) produces clean, ply-capped, diverse games logged via the existing `Log`; a pure relabel function (`tools/outcome.py`) turns each game's result into a dark-perspective label `z`; `train.ipynb` retrains the CNN with a tanh value head on `z` into a *new* model file; a head-to-head `tools/arena.py` gates promotion. Everything reuses `scripts/encoding.py`, `Log`, `Board`, `Bot`, `ModelEvaluator`, and the `make_move`/`undo_move` simulator.

**Tech Stack:** Python 3.11 (Windows, `py`), Pygame (headless via `SDL_VIDEODRIVER=dummy`), NumPy, pandas, TensorFlow/Keras (GPU for training), stdlib `math`/`random`.

## Global Constraints

- **Dark-perspective label:** `z = +1` dark won, `-1` light won, `0` draw/ply-capped — assigned to EVERY position of a game. Keeps `ai_move`'s dark→argmax / light→argmin unchanged.
- **Derive `z` order-independently:** per game, `z = sum(winner over its rows)` (only the game-ending row is nonzero); drop any game whose `|sum| > 1`.
- **No format / engine changes:** board string, `scripts/encoding.py`, `PIECE_ENCODING`, `Log` schema/columns, and the game are untouched. `tools/smoke_test.py` + the four snapshots stay green.
- **New model is a separate file:** save to `models/best_model_outcome.h5`; NEVER overwrite `models/best_model.h5` (promotion is a manual step only after the arena passes).
- **Value head:** `Dense(1, activation='tanh')`; loss MSE on `z`. Inference is scale-invariant (argmax/argmin), so `ai_move` needs no change.
- **Self-play generator:** randomized minimax via `GameManager.computer_move`; first `OPENING_RANDOM_PLIES` (default 6) plies are uniform-random legal moves; game stopped at `MAX_PLIES` (default 300) and recorded as a draw.
- **Defaults (env knobs):** `SELFPLAY_GAMES=4000`, `MAX_PLIES=300`, `OPENING_RANDOM_PLIES=6`, `ARENA_GAMES=400`. Promotion: tournament score `(wins+0.5·draws)/games ≥ 0.55` AND one-sided binomial `p < 0.05` on decisive games.
- **Style:** Vietnamese comments/docstrings; `py -m ruff check` and `py -m compileall` clean for all new `tools/*.py`.
- **Headless everywhere:** self-play/arena set `SDL_VIDEODRIVER=dummy` and use image-free boards (`Board(is_copy=True)`), so no display/assets needed for logic; the model files ARE needed for the arena.

---

### Task 1: `tools/outcome.py` — outcome relabeling (pure, unit-tested)

**Files:**
- Create: `tools/outcome.py`
- Create: `tools/test_outcome.py`

**Interfaces:**
- Produces: `attach_outcome_labels(df: pd.DataFrame) -> pd.DataFrame` — requires columns `id`, `winner`; returns a copy with a new float column `z` (dark-perspective game outcome broadcast to every row of the game), with rows from games whose `|winner.sum()| > 1` dropped. Consumed by `train.ipynb` (Task 3).

- [ ] **Step 1: Write the failing test**

```python
# tools/test_outcome.py
"""Kiểm thử attach_outcome_labels: gán z outcome cho mọi vị trí của ván."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from tools.outcome import attach_outcome_labels


def main() -> int:
    # 3 ván: dark thắng (+1), light thắng (-1), cap-draw (0). winner chỉ khác 0 ở dòng cuối.
    df = pd.DataFrame({
        "id":     ["g1","g1","g1", "g2","g2", "g3","g3","g3"],
        "winner": [0,   0,   1,    0,   -1,   0,   0,   0],
        "board":  ["-"] * 8,
    })
    out = attach_outcome_labels(df)
    ok = True
    z1 = out.loc[out.id == "g1", "z"].tolist()
    z2 = out.loc[out.id == "g2", "z"].tolist()
    z3 = out.loc[out.id == "g3", "z"].tolist()
    if z1 != [1.0, 1.0, 1.0]: ok = False; print("[SAI] g1", z1)
    if z2 != [-1.0, -1.0]:    ok = False; print("[SAI] g2", z2)
    if z3 != [0.0, 0.0, 0.0]: ok = False; print("[SAI] g3", z3)
    # Ván dị thường (|sum|>1) phải bị loại.
    bad = pd.DataFrame({"id": ["b","b"], "winner": [1, 1], "board": ["-","-"]})
    if len(attach_outcome_labels(bad)) != 0:
        ok = False; print("[SAI] không loại ván |sum|>1")
    print("OUTCOME_OK" if ok else "OUTCOME_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py tools/test_outcome.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'tools.outcome'`).

- [ ] **Step 3: Write the implementation**

```python
# tools/outcome.py
"""Gán nhãn kết quả ván (outcome) cho từng vị trí, thay cho nhãn heuristic cũ.

z theo góc nhìn phe TỐI: +1 dark thắng, -1 light thắng, 0 hòa/ván bị cắt theo
ply-cap. Vì cột ``winner`` chỉ khác 0 ở đúng dòng kết thúc ván, tổng ``winner``
theo từng ``id`` chính là z (bất biến với thứ tự dòng)."""
import pandas as pd


def attach_outcome_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Trả về bản sao df có thêm cột ``z`` = kết quả ván (broadcast mọi dòng).

    Loại các ván dị thường (|tổng winner| > 1, tức có nhiều hơn một dòng kết
    thúc) để nhãn luôn nằm trong {-1, 0, 1}."""
    outcome = df.groupby("id")["winner"].transform("sum")
    kept = df[outcome.abs() <= 1].copy()
    kept["z"] = kept.groupby("id")["winner"].transform("sum").astype("float32")
    return kept
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py tools/test_outcome.py`
Expected: last line `OUTCOME_OK`, exit 0.

- [ ] **Step 5: Lint + commit**

Run: `py -m ruff check tools/outcome.py tools/test_outcome.py` → clean
```bash
git add tools/outcome.py tools/test_outcome.py
git commit -m "feat: add outcome-label relabeling (dark-perspective z)"
```

---

### Task 2: `tools/selfplay.py` — clean headless self-play generator

**Files:**
- Create: `tools/selfplay.py`
- Modify: `.gitignore` (ignore generated self-play CSVs)

**Interfaces:**
- Consumes: `GameManager.computer_move` (randomized minimax), `Board(is_copy=True)`, `Log`.
- Produces: `data/selfplay_<timestamp>.csv` (existing `Log` schema). Function `generate(games, max_plies, opening_random_plies, out_dir) -> Path` returns the written CSV path.

- [ ] **Step 1: Write the generator**

```python
# tools/selfplay.py
"""Sinh dữ liệu self-play SẠCH cho Rung 3 (headless, không cần màn hình).

Chính sách sinh: minimax ngẫu nhiên (GameManager.computer_move) + ngẫu nhiên
hoá khai cuộc (OPENING_RANDOM_PLIES ply đầu) để đa dạng ván. Ván vượt MAX_PLIES
bị cắt và tính hòa (dòng cuối winner=0). Ghi qua Log rồi đổi tên file thành
selfplay_<timestamp>.csv để tách khỏi log 'dark_*' cũ."""
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
from scripts.common import DATA_DIR, GameMode, PlayerSide
from scripts.log import Log
from scripts.manager import GameManager


def _play_one_game(gm: GameManager, max_plies: int, opening_random_plies: int) -> None:
    """Chơi một ván tới khi kết thúc hoặc chạm ply-cap; ghi từng nước qua gm.log."""
    gm.board = Board(is_copy=True)                       # bàn logic không ảnh
    gm.current_side, gm.opponent_side = PlayerSide.LIGHT, PlayerSide.DARK
    for ply in range(max_plies):
        if gm.board.is_game_over:
            break
        if ply < opening_random_plies:                  # ngẫu nhiên hoá khai cuộc
            moves = gm.board.get_valid_moves(gm.current_side)
            if not moves:
                break
            move = random.choice(moves)
        else:
            move = gm.computer_move()                    # minimax ngẫu nhiên
            if move is None:
                break
        gm.board.make_move(move)
        gm.log.insert_chess_record(gm.board, move)
        if gm.board.is_game_over:                         # nước vừa đi kết thúc ván
            break
        gm.switch_player()
    gm.log.save()                                         # lưu ván (kể cả cap-draw)


def generate(games: int, max_plies: int, opening_random_plies: int, out_dir: Path) -> Path:
    """Sinh `games` ván, trả về đường dẫn CSV selfplay_<timestamp>.csv."""
    gm = GameManager(GameMode.CvC)
    gm.log = Log(output_dir=out_dir)
    for i in range(games):
        _play_one_game(gm, max_plies, opening_random_plies)
        if (i + 1) % 100 == 0:
            print(f"selfplay: {i + 1}/{games} ván")
    src = Path(gm.log.output_file)
    dst = src.with_name(f"selfplay_{src.stem.split('_', 1)[1]}.csv")
    if src.exists():
        src.rename(dst)
    return dst


def main() -> int:
    games = int(os.getenv("SELFPLAY_GAMES", "4000"))
    max_plies = int(os.getenv("MAX_PLIES", "300"))
    opening = int(os.getenv("OPENING_RANDOM_PLIES", "6"))
    seed = os.getenv("SELFPLAY_SEED")
    if seed is not None:
        random.seed(int(seed))
    path = generate(games, max_plies, opening, DATA_DIR)
    print(f"SELFPLAY_DONE {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Ignore generated self-play data**

Add to `.gitignore` under the "Large derived datasets" block:
```gitignore
data/selfplay_*.csv
```

- [ ] **Step 3: Smoke-run a tiny batch (deterministic seed)**

Run: `SELFPLAY_SEED=1 SELFPLAY_GAMES=8 MAX_PLIES=60 OPENING_RANDOM_PLIES=6 py tools/selfplay.py`
Expected: prints `SELFPLAY_DONE .../data/selfplay_<ts>.csv`, exit 0, file created.

- [ ] **Step 4: Assert the output is valid (schema + per-game outcome)**

Run:
```bash
py -c "import pandas as pd, glob; f=sorted(glob.glob('data/selfplay_*.csv'))[-1]; d=pd.read_csv(f); \
print('cols_ok', list(d.columns)==['id','board','side','piece','atk','move','river','trap','den','score','winner']); \
s=d.groupby('id')['winner'].sum(); print('outcomes_in_range', bool(s.abs().le(1).all())); \
print('games', d['id'].nunique(), 'rows', len(d))"
```
Expected: `cols_ok True`, `outcomes_in_range True`, games=8.

- [ ] **Step 5: Confirm the engine is untouched**

Run: `py tools/smoke_test.py` → `SMOKE_OK`; `py -m ruff check tools/selfplay.py` → clean.

- [ ] **Step 6: Commit**

```bash
git add tools/selfplay.py .gitignore
git commit -m "feat: add headless clean self-play generator (ply cap + opening random)"
```

---

### Task 3: `train.ipynb` — retrain on outcome `z` with a tanh value head

**Files:**
- Modify: `train.ipynb` (config source glob, load path, model head, output path)

**Interfaces:**
- Consumes: `data/selfplay_*.csv`, `tools.outcome.attach_outcome_labels`, `scripts.encoding.encode_board`.
- Produces: `models/best_model_outcome.h5` (a tanh-value-head CNN trained on `z`). `models/best_model.h5` untouched.

- [ ] **Step 1: Repoint the source glob + output path (config cell)**

In `train.ipynb` cell `e97e20b8`, change the source glob and model path (leave the rest):
```python
SOURCE_FILES = sorted(DATA_DIR.glob('selfplay_*.csv'))   # dữ liệu outcome sạch (Rung 3)
MODEL_PATH = MODEL_DIR / 'best_model_outcome.h5'          # KHÔNG ghi đè best_model.h5
```

- [ ] **Step 2: Relabel to outcome `z` in the load path**

In `train.ipynb`, change `load_training_data` (cell `7cb7c1a5`) to read whole files, attach `z`, and use `z` as the label instead of `score`:
```python
import sys as _sys
_sys.path.insert(0, str(DATA_DIR.parent))
from tools.outcome import attach_outcome_labels   # gán z từ kết quả ván

def load_training_data(source_files, max_rows):
    """Đọc self-play, gán nhãn outcome z (góc nhìn phe tối), mã hóa bàn -> tensor."""
    frames = []
    remaining = max_rows
    for source in source_files:
        df = pd.read_csv(source, usecols=['id', 'board', 'winner'])
        df = attach_outcome_labels(df)               # thêm cột z, loại ván dị thường
        if remaining is not None:
            df = df.iloc[:remaining]
            remaining -= len(df)
        frames.append(df)
        if remaining is not None and remaining <= 0:
            break
    data = pd.concat(frames, ignore_index=True)
    x = np.stack(data['board'].map(encode_board).to_numpy())[..., np.newaxis]
    y = data['z'].to_numpy(dtype=np.float32)         # nhãn = kết quả ván, KHÔNG phải heuristic
    return x, y
```
(Keep the preview cell `64f6d37a` working — it reads `board`/`score`; change its `usecols` to `['board','winner']` and stop referencing `score`, e.g. print `winner` instead.)

- [ ] **Step 3: Switch the value head to tanh**

In `train.ipynb` `build_model` (cell `7cb7c1a5`), change the final layer:
```python
Dense(1, activation='tanh'),      # đầu ra value trong (-1,1) khớp nhãn z
```
(Keep `loss='mean_squared_error'`.)

- [ ] **Step 4: Generate a tiny self-play file so the preview has data**

Run: `SELFPLAY_SEED=2 SELFPLAY_GAMES=30 MAX_PLIES=80 py tools/selfplay.py`
Expected: `SELFPLAY_DONE ...`.

- [ ] **Step 5: Preview-execute the notebook (no training) to exercise new code**

Run: `py -m jupyter nbconvert --to notebook --execute --stdout train.ipynb > /dev/null`
Expected: exit 0 — the relabel + `encode_board` preview + `build_model` (tanh) all run in preview mode; prints the "Chế độ preview..." message (RUN_MODEL_TRAINING unset).

- [ ] **Step 6: Assert the model head is tanh (unit check)**

Run:
```bash
py -c "import nbformat; nb=nbformat.read('train.ipynb', 4); src='\n'.join(c.source for c in nb.cells); \
assert \"Dense(1, activation='tanh')\" in src, 'tanh head missing'; \
assert 'attach_outcome_labels' in src, 'relabel missing'; \
assert 'best_model_outcome.h5' in src, 'output path missing'; print('TRAIN_NB_OK')"
```
Expected: `TRAIN_NB_OK`.

- [ ] **Step 7: Commit**

```bash
git add train.ipynb
git commit -m "feat: retrain evaluator on outcome z with tanh value head -> best_model_outcome.h5"
```

> **Note (manual, heavy step — not part of the gate):** the real training run is
> `$env:RUN_MODEL_TRAINING='1'; py -m jupyter nbconvert --to notebook --execute --inplace train.ipynb --ExecutePreprocessor.timeout=-1`
> after generating full self-play data (`py tools/selfplay.py`). It writes `models/best_model_outcome.h5`.

---

### Task 4: `tools/arena.py` — new-vs-old promotion gate

**Files:**
- Create: `tools/arena.py`
- Create: `tools/test_arena.py`

**Interfaces:**
- Consumes: `ModelEvaluator`, `Board(is_copy=True)`, `PlayerSide`.
- Produces: `one_sided_binom_p(wins: int, decisive: int) -> float` (P(X≥wins) under Binom(decisive, 0.5), stdlib); `play_match(new_path, old_path, games, max_plies, opening_random_plies) -> dict` with keys `new_wins,old_wins,draws,score,p_value,promote`.

- [ ] **Step 1: Write the failing stats test**

```python
# tools/test_arena.py
"""Kiểm thử thống kê nhị thức một phía của arena."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.arena import one_sided_binom_p


def main() -> int:
    ok = True
    if abs(one_sided_binom_p(5, 10) - 0.6230) > 1e-3: ok = False; print("[SAI] 5/10")
    if one_sided_binom_p(10, 10) >= 0.01: ok = False; print("[SAI] 10/10 phải rất nhỏ")
    if abs(one_sided_binom_p(0, 0) - 1.0) > 1e-9: ok = False; print("[SAI] 0/0")
    # 220/400 (55%) phải có ý nghĩa một phía p<0.05.
    if one_sided_binom_p(220, 400) >= 0.05: ok = False; print("[SAI] 220/400 phải <0.05")
    print("ARENA_STATS_OK" if ok else "ARENA_STATS_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `py tools/test_arena.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'tools.arena'`).

- [ ] **Step 3: Write `tools/arena.py`**

```python
# tools/arena.py
"""Đấu model MỚI vs model CŨ để đo mạnh-yếu (headless). Chỉ khi model mới đạt
score >= 0.55 và có ý nghĩa nhị thức một phía (p<0.05) mới nên promote thủ công
best_model_outcome.h5 -> best_model.h5."""
import os
import random
import sys
from math import comb
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from scripts.board import Board
from scripts.common import BEST_MODEL_PATH, MODEL_DIR, PlayerSide
from scripts.manager import ModelEvaluator


def one_sided_binom_p(wins: int, decisive: int) -> float:
    """P(X >= wins) với X ~ Binomial(decisive, 0.5). decisive=0 -> 1.0."""
    if decisive <= 0:
        return 1.0
    tail = sum(comb(decisive, k) for k in range(wins, decisive + 1))
    return tail / (2 ** decisive)


def _winner_of(new_eval, old_eval, new_side, max_plies, opening_random_plies):
    """Chơi một ván; trả 'new'/'old'/'draw' theo phe mà model mới cầm."""
    board = Board(is_copy=True)
    side, opp = PlayerSide.LIGHT, PlayerSide.DARK
    for ply in range(max_plies):
        if board.is_game_over:
            break
        if ply < opening_random_plies:
            moves = board.get_valid_moves(side)
            if not moves:
                break
            move = random.choice(moves)
        else:
            ev = new_eval if side == new_side else old_eval
            move = ev.best_move(board, side)
            if move is None:
                break
        board.make_move(move)
        if board.is_game_over:
            break
        side, opp = opp, side
    winner = board.winner                            # PlayerSide hoặc None (hòa/cap)
    if winner is None:
        return "draw"
    return "new" if winner == new_side else "old"


def play_match(new_path, old_path, games, max_plies, opening_random_plies) -> dict:
    """Đấu `games` ván, đổi màu một nửa; trả thống kê + khuyến nghị promote."""
    new_eval = ModelEvaluator(new_path)
    old_eval = ModelEvaluator(old_path)
    new_wins = old_wins = draws = 0
    for i in range(games):
        new_side = PlayerSide.DARK if i % 2 == 0 else PlayerSide.LIGHT
        r = _winner_of(new_eval, old_eval, new_side, max_plies, opening_random_plies)
        if r == "new": new_wins += 1
        elif r == "old": old_wins += 1
        else: draws += 1
    score = (new_wins + 0.5 * draws) / games if games else 0.0
    decisive = new_wins + old_wins
    p = one_sided_binom_p(new_wins, decisive)
    return {
        "new_wins": new_wins, "old_wins": old_wins, "draws": draws,
        "score": score, "p_value": p,
        "promote": bool(score >= 0.55 and p < 0.05),
    }


def main() -> int:
    games = int(os.getenv("ARENA_GAMES", "400"))
    max_plies = int(os.getenv("MAX_PLIES", "300"))
    opening = int(os.getenv("OPENING_RANDOM_PLIES", "6"))
    seed = os.getenv("ARENA_SEED")
    if seed is not None:
        random.seed(int(seed))
    new_path = os.getenv("NEW_MODEL", str(MODEL_DIR / "best_model_outcome.h5"))
    old_path = os.getenv("OLD_MODEL", str(BEST_MODEL_PATH))
    res = play_match(new_path, old_path, games, max_plies, opening)
    print(f"new_wins={res['new_wins']} old_wins={res['old_wins']} draws={res['draws']}")
    print(f"score={res['score']:.4f} p={res['p_value']:.4g} promote={res['promote']}")
    print("ARENA_PROMOTE" if res["promote"] else "ARENA_NO_PROMOTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the stats test to verify it passes**

Run: `py tools/test_arena.py`
Expected: last line `ARENA_STATS_OK`, exit 0.

- [ ] **Step 5: Smoke-run a tiny arena (old-vs-old sanity → ~50%, no crash)**

Run: `ARENA_SEED=1 ARENA_GAMES=6 MAX_PLIES=60 NEW_MODEL=models/best_model.h5 OLD_MODEL=models/best_model.h5 py tools/arena.py`
Expected: prints a `new_wins/old_wins/draws` tally and `score=...`, exit 0. (Same model both sides → no real edge; this only proves the runner works.)

- [ ] **Step 6: Lint + commit**

Run: `py -m ruff check tools/arena.py tools/test_arena.py` → clean
```bash
git add tools/arena.py tools/test_arena.py
git commit -m "feat: add new-vs-old arena with one-sided binomial promotion gate"
```

---

### Task 5: Documentation + full verification

**Files:**
- Modify: `README.md` (a short "Rung 3" usage block), `CLAUDE.md` (one line in the pipeline area)

**Interfaces:** none (docs + verification only).

- [ ] **Step 1: Document the Rung 3 workflow in `README.md`**

Add a subsection after the training section:
```markdown
### Rung 3 — Value học từ kết quả ván (tùy chọn)

py tools\selfplay.py                 # sinh self-play sạch -> data/selfplay_*.csv (env: SELFPLAY_GAMES, MAX_PLIES, OPENING_RANDOM_PLIES)
# rồi train (RUN_MODEL_TRAINING=1) -> models/best_model_outcome.h5 (KHÔNG ghi đè best_model.h5)
py tools\arena.py                    # đấu model mới vs cũ (env: ARENA_GAMES); promote thủ công nếu ARENA_PROMOTE
```

- [ ] **Step 2: One-line pointer in `CLAUDE.md`**

In `CLAUDE.md`, in the pipeline area, add:
```markdown
- **Rung 3 (outcome value):** `tools/selfplay.py` (clean capped self-play) → `train.ipynb` relabels to dark-perspective `z` via `tools/outcome.py` + a tanh head → `models/best_model_outcome.h5`; `tools/arena.py` gates promotion (never auto-overwrites `best_model.h5`).
```

- [ ] **Step 3: Full verification**

Run each; all must pass:
- `py tools/test_outcome.py` → `OUTCOME_OK`
- `py tools/test_arena.py` → `ARENA_STATS_OK`
- `py tools/smoke_test.py` → `SMOKE_OK`
- `py -m compileall -q main.py scripts tools` → clean
- `py -m ruff check main.py scripts tools` → clean
- Snapshots (engine unchanged): rerun the four snapshot checks from the earlier scratchpad harness (meta/rules/bot/log) → all OK, if that harness is still available; otherwise `SMOKE_OK` suffices since no engine file changed.

- [ ] **Step 4: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: document Rung 3 self-play/outcome-training/arena workflow"
```

---

## Self-Review

**Spec coverage:** §3.1 selfplay → Task 2. §3.2 relabel → Task 1 (+ used in Task 3). §3.3 retrain/tanh/new-file → Task 3. §3.4 arena/binomial/promotion → Task 4. §5 reuse/no-format-change → enforced by Task 2/4 (image-free boards, `Log` reuse) + Task 5 verification (smoke green). §6 verification → Tasks 1–5 gates + Task 5 full pass. §7 out-of-scope respected (no MCTS/policy-head/auto-promotion). §8 risks: opening randomization (Tasks 2, 4), separate model file (Task 3), 400-game binomial (Task 4). No gaps.

**Placeholder scan:** No TBD/TODO. Every code step has complete code; the heavy full-training run is explicitly flagged as a manual out-of-gate step (Task 3 note), not a placeholder. The snapshot fallback in Task 5 Step 3 names the exact condition ("no engine file changed") rather than hand-waving.

**Type consistency:** `attach_outcome_labels(df)->df with float `z`` defined in Task 1, consumed identically in Task 3. `one_sided_binom_p(wins, decisive)->float` defined and tested in Task 4. `ModelEvaluator(path).best_move(board, side)` used in Task 4 matches the signature established when it was created (manager.py). `Board(is_copy=True)`, `GameManager.computer_move`, `Log(output_dir=...)`, `Log.insert_chess_record/save` all match existing signatures.
