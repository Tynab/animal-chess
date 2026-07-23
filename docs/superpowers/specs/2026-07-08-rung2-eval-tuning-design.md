# Rung 2 (eval) — Positional Eval Terms + Engine-vs-Engine Tuning (Design)

- **Date:** 2026-07-08
- **Status:** Approved (design), pending spec review
- **Branch:** `develop`
- **Context:** Rung 1 gave the bot a deep alpha-beta search (depth 6-8) that already **converts wins** (an engine self-play game finished in ~36 plies with a decisive winner, vs the old bot's 700-ply shuffling). The strength ceiling is now the coarse leaf eval. This rung adds a systematic, arena-gated way to improve that eval, starting with a **den-defense** term.

## 1. Goal

Add a small, coefficient-controlled positional term (**den defense**) to the search's leaf eval, plus an **engine-vs-engine arena** to measure eval changes empirically, so the bot can be tuned systematically. Expected gain is modest (polish); the durable value is the tuning machinery. `Bot.evaluate_position` and all formats stay untouched.

## 2. Scope decisions (from brainstorming)

| Decision | Choice |
|---|---|
| First term | **Den defense** (+ keep the existing offensive den-gradient). Mobility / PST / river-trap terms are deferred. |
| Where | Add terms in `scripts/search.py` `search_eval` only; **do NOT touch `Bot.evaluate_position`** (the reference/baseline for `bot_golden` + the `value==minimax` equivalence test). |
| Default | The den-defense term ships **default OFF** (`defense_coef=0`), so the engine's default play is unchanged and smoke/equivalence stay trivially green until the arena proves a coefficient. |
| Parametrization | Individual coefficients on `search_eval`/`SearchEngine` (`gradient_coef`, new `defense_coef`) — keeps the Rung 1 `SearchEngine(gradient_coef=0, …)` equivalence test unchanged (no weights-container refactor). |
| Measurement | New `tools/evalarena.py`: two `SearchEngine` configs (different coefficients, same depth/budget) play K games; reuse `one_sided_binom_p`. Keep a term/coef iff score ≥ 0.55 AND one-sided binomial p < 0.05. Default 200 games (quick sweep); 400 for a decisive keep/drop. |
| Enabling | After building the machinery, run `evalarena` to sweep candidate `defense_coef` values vs the baseline; set the winning value as the new default, or leave it 0 with a documented "no help" conclusion. |

## 3. Architecture — 3 units

### 3.1 Parametrized `search_eval` (`scripts/search.py`)
- Extend `search_eval(board, side, gradient_coef=1, defense_coef=0)`; `SearchEngine.__init__` gains `defense_coef=0` (kept alongside the existing `gradient_coef=1`), threaded to the three `search_eval` call sites.
- `search_eval = Bot.evaluate_position(board, side) + _den_gradient(board, side, gradient_coef) + _den_defense(board, side, defense_coef)`.
- Invariant: with `gradient_coef=0, defense_coef=0`, `search_eval == Bot.evaluate_position` exactly (each term returns 0 when its coef is 0). This keeps the Rung 1 equivalence test valid.

### 3.2 Den-defense term
Side-relative, cheap (arithmetic over `board.pieces`):
```python
def _den_defense(board, side, coef):
    if not coef:
        return 0
    mdx, mdy = PlayerSide.player_den_position(side)        # hang nhà (ta phòng thủ)
    odx, ody = PlayerSide.opponent_den_position(side)      # hang địch (địch phòng thủ)
    total = 0
    for piece in board.pieces:
        px, py = piece.position
        if piece.side == side:
            d = abs(px - mdx) + abs(py - mdy)
            if d <= 2:                                     # quân ta canh hang nhà: gần hơn = tốt hơn
                total += coef * (3 - d)
        else:
            d = abs(px - odx) + abs(py - ody)
            if d <= 2:                                     # địch canh hang địch: ta khó xâm nhập
                total -= coef * (3 - d)
    return total
```
(A friendly piece can never be ON its own den — the movement rule forbids it — so friendly `d ∈ {1,2}` → bonus `{2,1}×coef`; material is `rank×10`, so a small `defense_coef` keeps this a positional nudge, not a driver.)

### 3.3 `tools/evalarena.py` — engine-vs-engine A/B
- Pits engine config **A** (e.g. `defense_coef=D`) vs config **B** (`defense_coef=0`), K games, swapped colors, opening randomization, ply cap; both use the same search depth/budget. Reuses `one_sided_binom_p` from `tools/arena.py`.
- Reports A's wins/losses/draws, score = `(A_wins + 0.5·draws)/games`, one-sided binomial p, and `keep = (score ≥ 0.55 and p < 0.05)`.
- Env knobs: `EVALARENA_GAMES=200`, `MAX_PLIES=200`, `OPENING_RANDOM_PLIES=6`, `EVAL_MAX_DEPTH=3`, `A_DEFENSE_COEF`, `B_DEFENSE_COEF=0`, `A_GRADIENT_COEF=1`/`B_GRADIENT_COEF=1`, `EVALARENA_SEED`.

## 4. Reuse & invariants
- **Reused:** `Bot.evaluate_position`, `make_move`/`undo_move`, `board.pieces`, `PlayerSide.player_den_position`/`opponent_den_position`, `tools/arena.py`'s `one_sided_binom_p`, the `SearchEngine`.
- **Untouched (invariant):** `Bot.evaluate_position`/`Bot.minimax`, the 63-char board string, `scripts/encoding.py`, `PIECE_ENCODING`, CSV schema, the `.h5` models, and the existing `_den_gradient`. `tools/smoke_test.py` (`SMOKE_OK`), `tools/test_perft.py` (`PERFT_OK`), `tools/test_search.py` (`SEARCH_OK`, incl. `value==minimax` and search_eval(gradient=0)==evaluate_position) must all stay green (default `defense_coef=0` makes this automatic).
- Bot **behavior only changes if/when the default `defense_coef` is flipped** after an arena win.

## 5. Verification
- `tools/test_search.py` extended: `search_eval(board, side, 0, 0) == Bot.evaluate_position(board, side)`; a friendly piece placed adjacent to own den makes `_den_defense(board, side, 1) > 0`; the symmetric enemy case is `< 0`. The existing `value==minimax` equivalence + perft goldens unchanged.
- `tools/smoke_test.py` → `SMOKE_OK`; `tools/test_perft.py` → `PERFT_OK`.
- `evalarena` smoke: a tiny run with A==B (same coefs) reports ≈0.5 / `keep=False` and doesn't crash.
- `compileall` + `ruff` clean over `main.py scripts tools`.
- **Tuning run (the real signal):** `evalarena` over candidate `defense_coef` values (e.g. 3/6/10) vs baseline; pick the winner (score ≥ 0.55, p < 0.05) as the new default, else leave `defense_coef=0` and document that den-defense didn't help.

## 6. Out of scope (deferred)
- Other eval terms (mobility, piece-square tables, river/trap control, threat detection) — the parametrization makes them easy to add later, but YAGNI for now.
- NNUE / learned fast eval, AlphaZero (Rung 4), endgame tablebases (Rung 2-TB).
- Changing `Bot.evaluate_position`, formats, models, or the search algorithm itself.

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Eval gain is small / lost in noise | Arena reports a one-sided binomial p; use ≥400 games for the keep/drop decision. |
| A bad coefficient weakens play | Term ships default OFF; a coefficient becomes the default only after an arena win. |
| Eval slows the search (costs depth) | Term is O(pieces) arithmetic, no model calls; both A/B engines pay the same cost so the arena isolates the eval effect, and the coef=0 default is free. |
| Den-defense over-defends (passive play) | Small coefficient (positional nudge « material); arena catches over-passivity as a lower score. |

## 8. Success definition
The machinery succeeds when: `search_eval` is coefficient-parametrized with the den-defense term (default off, all Rung-0/1 gates still green), `tools/evalarena.py` runs engine-vs-engine and reports score + binomial p, and the tuning run yields a verdict — either a `defense_coef` that wins ≥ 0.55 (p < 0.05) and becomes the new default, or a documented conclusion that den-defense does not measurably help (left at 0). Either way the bot is not weakened and the eval is now systematically tunable.
