# Rung 3 — Outcome-Based Value Target (Design)

- **Date:** 2026-07-08
- **Status:** Approved (design), pending spec review
- **Branch:** `develop`
- **Context:** Follows the deep-research report (ROI ladder rung 3). The CNN currently learns by MSE regression to imitate a depth-0 heuristic (`score = evaluate_position(board, DARK)`), so it is bounded by that heuristic. This rung changes the value **target** to the actual game outcome, removing the ceiling. It is one policy-iteration step toward a full AlphaZero system (Rung 4), and its harnesses are built to be reused there.

## 1. Goal

Train a position evaluator whose target is **the game result `z`** (learned from outcomes) instead of a hand-crafted heuristic, and **prove** the new model plays stronger than the current one via a head-to-head arena — without touching the interactive game or the on-disk board/encoder formats.

## 2. Scope decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Data source | **Regenerate clean self-play** with a ply cap (existing logs are pathologically long — median 554, max 17,751 plies — so raw outcome labels on them are too noisy) |
| Self-play policy | **Randomized minimax (`computer_move`)** as the generator + opening randomization; NOT the deterministic-argmax model |
| Architecture | Separate harnesses (`tools/selfplay.py`, `tools/arena.py`); `train.ipynb` value-target change; model **versioned**, not overwritten until proven |
| Value perspective | **Dark-perspective `z`** so `ai_move`'s dark→argmax / light→argmin is unchanged |
| Formats | **No change** to board string / encoder / `PIECE_ENCODING`; new model is a separate `.h5` |

## 3. Components (4 units, one responsibility each)

### 3.1 `tools/selfplay.py` — clean self-play generator (headless)
- Plays `SELFPLAY_GAMES` (default **4000**) headless CvC games, reusing `Board`, `Bot`, `Log`, and `common`. Runs with `SDL_VIDEODRIVER=dummy` and image-free boards (no display/assets needed for logic).
- **Generator policy:** both sides move via the randomized **`GameManager.computer_move`** path (depth-2 minimax/alpha-beta with its existing randomness), which already yields diverse games and does not depend on the (weak, deterministic) model. Additionally, the **first `OPENING_RANDOM_PLIES` (default 6)** plies of each game are chosen uniformly at random among legal moves to diversify openings.
- **Ply cap:** a game exceeding `MAX_PLIES` (default **300**) is stopped and recorded as a **draw** (the terminal row gets `winner = 0`). `MAX_PLIES`, `SELFPLAY_GAMES`, `OPENING_RANDOM_PLIES` are env-var knobs.
- **Output:** appends to `data/selfplay_<timestamp>.csv` using the existing `Log` serializer — **identical schema** (`id, board, side, piece, atk, move, river, trap, den, score, winner`). `score` is still logged (harmless, unused by the new target).
- Reuses `Log.insert_chess_record` / `Log.save`; each game is one `id`.

### 3.2 Outcome relabeling (inside `train.ipynb`)
- New load path reads `data/selfplay_*.csv`, groups rows by `id`, and derives the game outcome `z` from the **terminal-row `winner`**: `+1` (dark won), `-1` (light won), `0` (draw / ply-capped).
- Assigns that single `z` to **every position of the game** (undiscounted — games are now bounded by the cap). This `z` (dark-perspective) is the training label, replacing the old `score` column.
- Games whose terminal row is missing / truncated at a chunk boundary are dropped (guard: a game must have exactly one nonzero terminal winner OR be an explicit cap-draw).

### 3.3 Retrain (modify `train.ipynb`)
- **Unchanged:** input encoder `(9,7,1)` from `scripts.encoding.encode_board`, the Conv trunk, KFold, GPU config.
- **Changed:** value head `Dense(1, activation='linear')` → `Dense(1, activation='tanh')`; label = `z`; loss = MSE (`z ∈ {-1,0,+1}`, output ∈ (-1,1)).
- **Output:** saves to a **new** file `models/best_model_outcome.h5`. Does **not** overwrite `models/best_model.h5`.
- Inference needs **no change**: `ai_move` picks argmax(dark)/argmin(light) of the scalar output, which is scale-invariant, so the tanh-scaled output works as-is.

### 3.4 `tools/arena.py` — success metric (headless)
- Pits the **new** model (`models/best_model_outcome.h5`) against the **old** model (`models/best_model.h5`) over `ARENA_GAMES` (default **400** — chosen so a 55% edge is statistically resolvable; 200 games leaves 55% inside coin-flip noise), swapping colors halfway (half each color).
- Each side plays by **its own model only** — `ModelEvaluator(path).best_move(board, side)` (argmax/argmin), no minimax fallback — so the comparison isolates the models. The first `OPENING_RANDOM_PLIES` (default 6) plies are random so games differ (otherwise deterministic argmax makes every game identical). Games are capped at `MAX_PLIES` (draw).
- **Reports:** new-model wins / losses / draws, and the tournament **score = (wins + 0.5·draws) / games**, plus a one-sided binomial p-value against the null "score ≤ 0.5".
- **Promotion criterion:** score **≥ 55%** AND the one-sided binomial test rejects "≤ 50%" at **p < 0.05** (at 400 games, ≥55% clears this). Only if it passes do we promote `best_model_outcome.h5` → `best_model.h5` (a separate, manual, explicit step — never automatic).

## 4. Data flow

```
selfplay.py (randomized minimax + opening random, ply cap)
   → data/selfplay_*.csv  (existing schema)
train.ipynb: group by id → z (dark-perspective, {-1,0,+1}) → label every position
   → retrain CNN (tanh value head, MSE on z)
   → models/best_model_outcome.h5   (NEW file; best_model.h5 untouched)
arena.py: best_model_outcome.h5  vs  best_model.h5  (200 games, opening random, cap)
   → win rate → promote only if ≥55% & significant
```

## 5. Reuse & isolation
- **Reused as-is:** `scripts/encoding.py` encoder, `Log` serializer, `Board`/`Bot`/`ModelEvaluator`, `make_move`/`undo_move` simulator.
- **Untouched:** `main.py` interactive game, board/encoder/`PIECE_ENCODING` formats, `best_model.h5`, `tools/smoke_test.py` + snapshots (must stay green — no engine behavior changes).
- **Forward-reusable for Rung 4 (AlphaZero):** `selfplay.py` (swap generator for MCTS-guided policy, add temperature) and `arena.py` (the evaluation gate) are exactly the harnesses AlphaZero's self-play → train → evaluate loop needs.

## 6. Verification
- `tools/smoke_test.py` + the 4 snapshots stay green (this rung changes no engine logic).
- `py -m compileall` + `py -m ruff check` clean for new `tools/*.py`.
- `selfplay.py` smoke: generate a tiny batch (e.g. 5 games, MAX_PLIES=40) and assert a valid CSV with the right schema + per-game single outcome.
- `arena.py` smoke: run a tiny arena (e.g. 4 games) and assert it reports a win/loss/draw tally without crashing.
- The **real success metric is the arena win rate** on a full run (≥55% to claim Rung 3 worked).

## 7. Out of scope (explicitly deferred)
- MCTS / PUCT, a policy head, and the iterative self-play loop → **Rung 4 (AlphaZero)**.
- NNUE and endgame tablebases → other rungs.
- Alpha-beta search upgrades (iterative deepening / TT) → **Rung 1** (independent).
- Auto-promotion of the model (promotion stays a manual, explicit human step).
- Changing the interactive game, the logging schema, or the board/encoder formats.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Ply cap too low → draws dominate → weak signal | `MAX_PLIES` is a knob; arena reveals it; raise cap or strengthen generator if draw rate is excessive |
| Bootstrapped from a weak generator (depth-2 minimax) → value ceiling is that policy's quality | Accepted — this is one policy-iteration step; it still removes the *heuristic-imitation* ceiling by learning real win-correlation. Further gains need Rung 4's loop |
| Deterministic argmax → identical self-play / arena games | Opening randomization (first `OPENING_RANDOM_PLIES` plies) in both harnesses |
| New model looks better by noise | 400-game arena + one-sided binomial significance + ≥55% threshold before promotion |
| Accidentally regress the shipped bot | New model is a separate file; `best_model.h5` only replaced by an explicit manual promotion after the arena passes |

## 9. Success definition
Rung 3 succeeds when a model trained on outcome labels beats the current heuristic-imitation model with a tournament **score ≥ 55% over a 400-game arena** and a one-sided binomial test rejecting "≤ 50%" at p < 0.05, at which point it is promoted to `best_model.h5`.
