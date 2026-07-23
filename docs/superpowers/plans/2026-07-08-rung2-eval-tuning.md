# Rung 2 — Positional Eval Terms + Engine-vs-Engine Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a coefficient-controlled den-defense term to the search's leaf eval (default off) plus an engine-vs-engine A/B arena, so the bot's eval can be tuned empirically without touching `Bot.evaluate_position` or any format.

**Architecture:** Extend `scripts/search.py` `search_eval` with a `defense_coef` param + `_den_defense` term, threaded through `SearchEngine`; the term is **off by default** (`defense_coef=0`) so all Rung-0/1 gates stay green. A new `tools/evalarena.py` pits two `SearchEngine` configs and reports a keep/drop verdict via `one_sided_binom_p`. A controller-run tuning sweep then sets or leaves the default coefficient.

**Tech Stack:** Python 3.11 (Windows, `py`), stdlib `time`/`random`/`math`.

## Global Constraints

- **`defense_coef` default 0** everywhere (`search_eval`, `SearchEngine`). With `gradient_coef=0, defense_coef=0`, `search_eval(board, side, 0, 0) == Bot.evaluate_position(board, side)` exactly.
- **Do NOT touch** `Bot.evaluate_position`/`Bot.minimax`, the existing `_den_gradient`, the 63-char board string, `scripts/encoding.py`, `PIECE_ENCODING`, CSV schema, or the `.h5` models. `SMOKE_OK`, `PERFT_OK`, and `SEARCH_OK` (incl. `value==minimax` equivalence) must stay green.
- **Keep bar** (arena): a config is kept iff tournament score `(a_wins+0.5·draws)/games ≥ 0.55` AND one-sided binomial p < 0.05 on decisive games. Reuse `one_sided_binom_p` from `tools/arena.py`.
- **Den-defense term** (side-relative, `O(pieces)` arithmetic): `+coef·(3−d)` for each friendly piece with Manhattan `d ≤ 2` of its OWN den (`PlayerSide.player_den_position(side)`); `−coef·(3−d)` for each enemy piece within `d ≤ 2` of the ENEMY den (`PlayerSide.opponent_den_position(side)`).
- **Style:** Vietnamese comments; `py -m ruff check` + `py -m compileall` clean over `main.py scripts tools`.

---

### Task 1: Den-defense eval term in `scripts/search.py`

**Files:**
- Modify: `scripts/search.py` (add `_den_defense`, extend `search_eval` + `SearchEngine`)
- Modify: `tools/test_search.py` (add defense assertions)

**Interfaces:**
- Consumes: `Bot.evaluate_position`, `PlayerSide.player_den_position`/`opponent_den_position`, `board.pieces`.
- Produces: `search_eval(board, side, gradient_coef=1, defense_coef=0)`; `SearchEngine(..., gradient_coef=1, defense_coef=0)` threading `defense_coef` to all `search_eval` calls.

- [ ] **Step 1: Extend the test first** — in `tools/test_search.py`, add these imports near the top (after the existing imports):
```python
from scripts.search import search_eval  # (already imported — ensure it's in the import list)
from scripts.pieces.rat import Rat
```
and insert this block immediately BEFORE the final `print("SEARCH_OK" ...)` line:
```python
    # Rung 2 — số hạng phòng thủ hang.
    if search_eval(b, PlayerSide.DARK, 0, 0) != Bot.evaluate_position(b, PlayerSide.DARK):
        ok = False
        print("[SAI] search_eval(0,0) != evaluate_position")
    # Đặt một quân TỐI trong bán kính hang tối (3,0) -> defense dương cho DARK, âm cho LIGHT.
    guard = Board(with_pieces=False, is_copy=True)
    guard.get_cell((3, 2)).add_piece(Rat(PlayerSide.DARK, is_copy=True))
    guard.update_pieces()
    dark_contrib = search_eval(guard, PlayerSide.DARK, 0, 1) - search_eval(guard, PlayerSide.DARK, 0, 0)
    light_contrib = search_eval(guard, PlayerSide.LIGHT, 0, 1) - search_eval(guard, PlayerSide.LIGHT, 0, 0)
    if dark_contrib <= 0:
        ok = False
        print(f"[SAI] defense không dương khi có quân canh hang nhà: {dark_contrib}")
    if light_contrib >= 0:
        ok = False
        print(f"[SAI] defense không âm cho phe đối diện: {light_contrib}")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `py tools/test_search.py` → FAIL (`TypeError: search_eval() takes ... positional arguments but 4 were given`).

- [ ] **Step 3: Add `_den_defense` + extend `search_eval`** in `scripts/search.py`. Add after `_den_gradient`:
```python
def _den_defense(board, side, coef) -> int:
    """Thưởng khi quân ta canh hang NHÀ (chặn xâm nhập); trừ khi địch canh hang địch
    (ta khó xâm nhập). Góc nhìn `side`, số học rẻ trên board.pieces."""
    if not coef:
        return 0
    mdx, mdy = PlayerSide.player_den_position(side)            # hang nhà
    odx, ody = PlayerSide.opponent_den_position(side)          # hang địch
    total = 0
    for piece in board.pieces:
        px, py = piece.position
        if piece.side == side:
            d = abs(px - mdx) + abs(py - mdy)
            if d <= 2:
                total += coef * (3 - d)
        else:
            d = abs(px - odx) + abs(py - ody)
            if d <= 2:
                total -= coef * (3 - d)
    return total
```
and change `search_eval` to:
```python
def search_eval(board, side, gradient_coef=1, defense_coef=0) -> int:
    """Điểm thế cờ theo góc nhìn `side` = vật chất+hang + gradient + phòng thủ hang."""
    return (Bot.evaluate_position(board, side)
            + _den_gradient(board, side, gradient_coef)
            + _den_defense(board, side, defense_coef))
```

- [ ] **Step 4: Thread `defense_coef` through `SearchEngine`** — in `SearchEngine.__init__`, add the param and store it:
```python
    def __init__(self, time_budget_s=1.0, max_depth=None, tt_size=2**20,
                 gradient_coef=1, quiescence=True, defense_coef=0) -> None:
```
add `self.defense_coef = defense_coef` alongside the other assignments, and update ALL THREE `search_eval(board, side, self.gradient_coef)` call sites (in `_quiescence` and `_negamax`) to `search_eval(board, side, self.gradient_coef, self.defense_coef)`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `py tools/test_search.py` → `SEARCH_OK` (defense assertions + the unchanged `value==minimax` equivalence both pass; `defense_coef` defaults 0 so equivalence is unaffected).
Run: `py tools/smoke_test.py` → `SMOKE_OK`; `py tools/test_perft.py` → `PERFT_OK`.
Run: `py -m compileall -q scripts/search.py tools/test_search.py` → clean; `py -m ruff check scripts/search.py tools/test_search.py` → clean.

- [ ] **Step 6: Commit**

```bash
git add scripts/search.py tools/test_search.py
git commit -m "feat: add coefficient-gated den-defense term to search eval (default off)"
```

---

### Task 2: `tools/evalarena.py` — engine-vs-engine A/B

**Files:**
- Create: `tools/evalarena.py`, `tools/test_evalarena.py`

**Interfaces:**
- Consumes: `SearchEngine` (with `defense_coef`), `one_sided_binom_p` from `tools.arena`, `Board`, `PlayerSide`.
- Produces: `play_ab(a_kwargs, b_kwargs, games, max_plies, opening_random_plies) -> dict` (`a_wins,b_wins,draws,score,p_value,keep`); a CLI reporting `EVAL_KEEP`/`EVAL_NO`.

- [ ] **Step 1: Write the failing stats test**

```python
# tools/test_evalarena.py
"""Kiểm thử tiện ích evalarena: re-export thống kê nhị thức chạy được."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.evalarena import one_sided_binom_p


def main() -> int:
    ok = True
    if one_sided_binom_p(120, 200) >= 0.05:      # 60% -> có ý nghĩa
        ok = False
        print("[SAI] 120/200 phải <0.05")
    if one_sided_binom_p(0, 0) != 1.0:
        ok = False
        print("[SAI] decisive=0 phải 1.0")
    print("EVALARENA_STATS_OK" if ok else "EVALARENA_STATS_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `py tools/test_evalarena.py` → FAIL (`ModuleNotFoundError: No module named 'tools.evalarena'`).

- [ ] **Step 3: Write `tools/evalarena.py`**

```python
# tools/evalarena.py
"""A/B eval: đấu HAI cấu hình SearchEngine (khác hệ số eval, cùng độ sâu) để
quyết định giữ hay bỏ một số hạng. Tái dùng one_sided_binom_p của arena.
Giữ số hạng nếu cấu hình A thắng score >= 0.55 và p<0.05."""
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
from scripts.common import PlayerSide
from scripts.search import SearchEngine
from tools.arena import one_sided_binom_p


def _play_game(engine_a, engine_b, a_side, max_plies, opening_random_plies):
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
        else:
            engine = engine_a if side == a_side else engine_b
            move, _ = engine.best_move(board, side)
        if move is None:
            break
        board.make_move(move)
        if board.is_game_over:
            break
        side = PlayerSide.opponent_of(side)
    winner = board.winner
    if winner is None:
        return "draw"
    return "a" if winner == a_side else "b"


def play_ab(a_kwargs, b_kwargs, games, max_plies, opening_random_plies):
    engine_a = SearchEngine(**a_kwargs)
    engine_b = SearchEngine(**b_kwargs)
    aw = bw = draws = 0
    for i in range(games):
        a_side = PlayerSide.DARK if i % 2 == 0 else PlayerSide.LIGHT
        r = _play_game(engine_a, engine_b, a_side, max_plies, opening_random_plies)
        if r == "a":
            aw += 1
        elif r == "b":
            bw += 1
        else:
            draws += 1
    score = (aw + 0.5 * draws) / games if games else 0.0
    decisive = aw + bw
    p = one_sided_binom_p(aw, decisive)
    return {"a_wins": aw, "b_wins": bw, "draws": draws, "score": score,
            "p_value": p, "keep": bool(score >= 0.55 and p < 0.05)}


def main() -> int:
    games = int(os.getenv("EVALARENA_GAMES", "200"))
    max_plies = int(os.getenv("MAX_PLIES", "200"))
    opening = int(os.getenv("OPENING_RANDOM_PLIES", "6"))
    depth = int(os.getenv("EVAL_MAX_DEPTH", "3"))
    a = {"time_budget_s": None, "max_depth": depth,
         "gradient_coef": int(os.getenv("A_GRADIENT_COEF", "1")),
         "defense_coef": int(os.getenv("A_DEFENSE_COEF", "5"))}
    b = {"time_budget_s": None, "max_depth": depth,
         "gradient_coef": int(os.getenv("B_GRADIENT_COEF", "1")),
         "defense_coef": int(os.getenv("B_DEFENSE_COEF", "0"))}
    seed = os.getenv("EVALARENA_SEED")
    if seed is not None:
        random.seed(int(seed))
    res = play_ab(a, b, games, max_plies, opening)
    print(f"A(defense={a['defense_coef']}) vs B(defense={b['defense_coef']}): "
          f"a_wins={res['a_wins']} b_wins={res['b_wins']} draws={res['draws']}")
    print(f"score={res['score']:.4f} p={res['p_value']:.4g} keep={res['keep']}")
    print("EVAL_KEEP" if res["keep"] else "EVAL_NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the stats test to pass**

Run: `py tools/test_evalarena.py` → `EVALARENA_STATS_OK`, exit 0.

- [ ] **Step 5: Smoke arena (A==B → ≈0.5, no keep)**

Run: `EVALARENA_SEED=1 EVALARENA_GAMES=6 MAX_PLIES=60 EVAL_MAX_DEPTH=2 A_DEFENSE_COEF=0 B_DEFENSE_COEF=0 py tools/evalarena.py` → prints an `A(...) vs B(...)` line + `score=… p=… keep=…` + `EVAL_NO` (identical configs → no edge), exit 0.

- [ ] **Step 6: Lint + commit**

Run: `py -m ruff check tools/evalarena.py tools/test_evalarena.py` → clean.
```bash
git add tools/evalarena.py tools/test_evalarena.py
git commit -m "feat: add engine-vs-engine eval A/B arena (defense-coef tuning)"
```

---

### Task 3: Documentation + full verification

**Files:**
- Modify: `CLAUDE.md` (note the eval-tuning surface + arena)

**Interfaces:** none (docs + verification).

- [ ] **Step 1: Document in `CLAUDE.md`** — in the search/engine area, add:
```markdown
- **Eval tuning (Rung 2):** `search_eval` is coefficient-gated (`gradient_coef`, `defense_coef`; both threaded via `SearchEngine`). `defense_coef` rewards guarding your own den; **default 0** (off) until an A/B arena proves it. `tools/evalarena.py` pits two engine configs (reuse `one_sided_binom_p`); keep a coef iff score ≥ 0.55 & p < 0.05. `Bot.evaluate_position` stays untouched (the `value==minimax` equivalence reference).
```

- [ ] **Step 2: Full verification** — run each; all must pass:
- `py tools/test_search.py` → `SEARCH_OK`
- `py tools/test_evalarena.py` → `EVALARENA_STATS_OK`
- `py tools/test_perft.py` → `PERFT_OK`
- `py tools/smoke_test.py` → `SMOKE_OK`
- `py -m compileall -q main.py scripts tools` → clean
- `py -m ruff check main.py scripts tools` → clean

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document Rung 2 eval-tuning surface (defense_coef + evalarena)"
```

---

## Post-build tuning (controller-run, not a subagent task)

After Tasks 1-3, the machinery exists with `defense_coef=0` (engine unchanged). To decide the default, run the A/B sweep and act on the result — this needs judgment on the arena outcome, so the controller runs it directly:

1. Sweep candidate coefficients vs the baseline (background), e.g. for `D in 3 6 10`:
   `EVALARENA_SEED=11 EVALARENA_GAMES=200 EVAL_MAX_DEPTH=3 A_DEFENSE_COEF=$D B_DEFENSE_COEF=0 py tools/evalarena.py`
2. If a `D` prints `EVAL_KEEP` (score ≥ 0.55, p < 0.05) — pick the best-scoring one and set it as the default: change `defense_coef=0` → `defense_coef=<D>` in `SearchEngine.__init__` (only the default; the term already works), re-run the full verification, and commit `feat: enable den-defense (defense_coef=<D>) — arena-validated`.
3. If none clears the bar — leave `defense_coef=0` and commit a note (or the ledger records it): "den-defense did not measurably help; kept off, machinery retained for future terms."

Either outcome is a valid completion: the eval is now systematically tunable and the bot is never weakened by an unproven term.

---

## Self-Review

**Spec coverage:** §3.1 parametrized `search_eval` → Task 1. §3.2 den-defense term → Task 1 (exact formula from the spec). §3.3 `evalarena` → Task 2. §5 verification (equivalence/smoke/perft green + defense unit test + arena smoke) → Tasks 1/2 gates + Task 3. §2 default-off + keep-bar → Global Constraints + Task 2. The tuning run (§2/§5) → "Post-build tuning" (controller-run). No gaps.

**Placeholder scan:** No TBD/TODO. The sweep coefficients `3/6/10` are concrete candidates, not placeholders; the outcome branch (set default vs leave off) is fully specified. All commands have expected output.

**Type consistency:** `search_eval(board, side, gradient_coef=1, defense_coef=0)` and `SearchEngine(..., defense_coef=0)` defined in Task 1, consumed by Task 2's `play_ab` (`defense_coef` in the kwargs) and the tuning sweep. `_den_defense(board, side, coef)` internal. `one_sided_binom_p(wins, decisive)` re-exported through `tools.evalarena` (imported from `tools.arena`) — matches its Rung-3 definition. `play_ab(a_kwargs, b_kwargs, games, max_plies, opening_random_plies)` defined and used consistently.
