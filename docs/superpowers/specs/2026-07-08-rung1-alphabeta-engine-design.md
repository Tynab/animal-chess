# Rung 1 — Deep Alpha-Beta Search Engine (Design)

- **Date:** 2026-07-08
- **Status:** Approved (design), pending spec review
- **Branch:** `develop`
- **Context:** Deep-research ROI ladder rung 1 — the highest strength-per-effort upgrade, proven on this exact game (van Rijn & Vis: 7→14 plies with alpha-beta + a Zobrist transposition table). Replaces the current fixed-depth-2 minimax / CNN-1-ply play with a real iterative-deepening alpha-beta engine.

## 1. Goal

Make the playing bot **much stronger** by giving it a proper depth-6-to-8 alpha-beta search (iterative deepening, transposition table, move ordering, quiescence) with a fast heuristic leaf eval, and make that engine the **primary** move selector — proven stronger via a head-to-head strength arena. Also feeds Rung 3 with shorter, more decisive self-play data.

## 2. Key decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Primary move selector | **Deep alpha-beta with the fast heuristic eval** replaces the CNN-1-ply `ai_move` as the default. CNN (`ModelEvaluator`) kept for the Rung 3 arena; old `computer_move` kept as a baseline opponent. |
| Search bound | **Iterative deepening + configurable time budget** (≈1.0 s/move interactive; low budget / shallow `max_depth` for bulk self-play & the arena). |
| Leaf eval | `Bot.evaluate_position` (material + den ±900) **plus a small positional gradient** (advance toward the enemy den) so the bot pushes to win, not shuffle. `evaluate_position` itself is NOT modified. |
| BFS/A* routing | **Dropped** from the primary path (subsumed by deep search + eval gradient). The old code stays in `computer_move` (the baseline). |
| Isolation | New engine in **`scripts/search.py`**; `Bot.minimax`/`minimax_alpha_beta_pruning`/`evaluate_position` are **not touched** (so `smoke_test` + `bot_golden` stay valid and the old bot remains a baseline). |

Timing baseline (measured): current plain minimax on the opening — depth 2 = 0.007 s, 3 = 0.16 s, 4 = 3.4 s, 5 = 70 s (effective branching ≈ 22/ply). Alpha-beta + ordering cuts this toward ≈ √22 ≈ 5/ply, plus a TT, so **≈ depth 6-8 in ≈1 s in Python** is the realistic target (not the paper's C-code 14).

## 3. Architecture — 3 units

### 3.1 `scripts/search.py` — the engine
- `SearchEngine(time_budget_s=1.0, max_depth=None, tt_size=2**20)` with `best_move(board, side) -> (move, info)` where `info = {depth, score, nodes, pv}`. Stops at whichever of `time_budget_s` / `max_depth` is hit first. The TT is a dict keyed by Zobrist hash, bounded to `tt_size` entries with replace-by-depth eviction.
- **Iterative deepening:** search depth 1, 2, 3 … reusing the previous iteration's best move for ordering; return the best move from the deepest completed (or the in-progress best if time runs out mid-iteration, only using a fully-searched root move).
- **Alpha-beta (negamax)** over the existing `make_move`/`undo_move` simulator. Fail-soft.
- **Transposition table (Zobrist):** key = XOR of per-(cell-index, piece-kind) random 64-bit constants over occupied cells, XOR a side-to-move constant. (Trap-zeroed `atk` is a pure function of position, so it need not enter the key.) Each TT entry stores `(depth, value, flag ∈ {EXACT, LOWER, UPPER}, best_move)`; used for cutoffs and move ordering. Fixed-size, replace-by-depth.
- **Move ordering:** TT best move first → captures by MVV-LVA (victim rank − attacker rank, using `base_atk`) → two killer moves per ply → history heuristic. This is what realizes the √b branching reduction.
- **Quiescence search:** at frontier nodes, extend on captures only until a "quiet" position (no captures), to blunt the horizon effect.
- **Leaf eval:** `search_eval(board, side) = Bot.evaluate_position(board, side) + gradient(board, side)`, evaluated **from `side`'s perspective** (like `evaluate_position(board, side)`, so it drops straight into negamax). `gradient` adds a small bonus for each of `side`'s pieces as it nears the OPPONENT's den (Manhattan distance to `PlayerSide.opponent_den_position(side)`) and subtracts the symmetric term for the opponent's pieces nearing `side`'s own den — starting coefficient `+1 per cell closer` (material is rank×10, so the gradient is a tie-breaker, not a driver). Coefficient is an arena-tuned knob; `0` disables it.

### 3.2 `scripts/manager.py` — primary policy swap
- `GameManager` holds a `SearchEngine`; `autoplay` selects the move via `engine.best_move(self.board, self.current_side)` as the **primary** path.
- `ai_move`/`ModelEvaluator` and `computer_move` are **kept** (for the Rung 3 arena and as the strength baseline) but are no longer the default.

### 3.3 `scripts/selfplay.py` — better data via the engine
- The self-play generator uses the `SearchEngine` at a **low budget** (a small `max_depth`, e.g. 3-4, for speed + reproducibility) instead of `computer_move`, yielding shorter, more decisive games → higher-quality Rung 3 outcome data.

## 4. Reuse & invariants
- **Reused:** `make_move`/`undo_move`, `Bot.evaluate_position`, `get_valid_moves`, `PlayerSide.opponent_den_position`, `tools/arena.py`'s `one_sided_binom_p`.
- **Untouched (invariant):** `Bot.minimax`/`minimax_alpha_beta_pruning`/`evaluate_position`/BFS/A*; the 63-char board string, `scripts/encoding.py`, `PIECE_ENCODING`, CSV schema, and both `.h5` models. `tools/smoke_test.py` must stay `SMOKE_OK`.
- Bot **behavior intentionally changes** (stronger, deeper) — so `bot_golden` (depth-2 results) is NOT a Rung-1 gate; the new engine is verified by §6 instead. `bot_golden` still applies to the untouched `Bot.minimax` and must stay OK.

## 5. Config (env knobs, defaults)
`SEARCH_TIME_S=1.0` (interactive), `SEARCH_MAX_DEPTH` (optional hard cap), `TT_SIZE` (entries), `SELFPLAY_MAX_DEPTH=4` (self-play generator), `STRENGTH_GAMES=200`, `STRENGTH_SEARCH_TIME` (engine budget in the arena).

## 6. Verification (behavior changed → new approach)
- **Perft golden (`tools/perft.py`):** `perft(board, depth)` counts leaf nodes via `make_move`/`undo_move` + `get_valid_moves`. Capture a golden count for the initial board at a fixed small depth (e.g. 3-4); the harness asserts reproducibility. Catches make/undo corruption and move-gen drift the engine relies on. Also assert the board string is identical before/after a full perft (undo symmetry).
- **Strength arena (`tools/strength.py`):** the `SearchEngine` vs the **current bot** (CNN `ModelEvaluator.best_move`, the present primary), K games (default 200), swapped colors, ply-capped, reusing `one_sided_binom_p`. **Success = engine tournament score ≥ 0.80** and binomial p < 0.05. (Also runnable vs `computer_move` depth-2.)
- **Smoke + snapshots:** `SMOKE_OK`; `bot_golden` (untouched `Bot.minimax`) still OK; `meta`/`rules` unaffected.
- **Interactive check:** launch the game (or a headless CvC with the engine) and confirm each move returns within the time budget with no crash.

## 7. Out of scope
- NNUE / a learned fast eval, and improving `evaluate_position` itself (later rung; Rung 1 uses the existing heuristic + small gradient).
- MCTS / AlphaZero (Rung 4). Endgame tablebases (Rung 2). Multi-threaded / parallel search.
- Changing formats, the CNN, `ai_move`'s argmax/argmin, or the interactive input handling.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Python is slow → far from 14 plies | Target depth 6-8/1 s; still 3-4× the current depth-2. Iterative deepening returns the best move found within budget. |
| TT + repetition (graph-history interaction): same board, different `forbidden_move` state → slightly wrong TT value | Accepted initially (minor); documented. TT stores best-move for ordering even when the value is not used for a cutoff. |
| Eval gradient could weaken play | Coefficient is a knob (0 = off); the strength arena gates it — drop/tune if it doesn't help. |
| Time-budget nondeterminism pollutes self-play reproducibility | Self-play uses a fixed `max_depth`, not wall-clock, so games are reproducible given a seed. |
| Engine make/undo bug corrupts the live board | Perft golden + a before/after board-string equality assert; the engine searches the live board and must restore it exactly. |

## 9. Success definition
Rung 1 succeeds when the `SearchEngine` beats the current CNN-1-ply bot with a tournament **score ≥ 0.80 over a 200-game strength arena** (one-sided binomial p < 0.05), the perft golden is reproducible with an intact board-string round-trip, `SMOKE_OK` holds, and interactive moves return within the time budget. The engine then becomes the default in `autoplay` and the self-play generator.
