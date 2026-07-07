# Animal Chess — Refactor, Commenting & Docs Overhaul (Design)

- **Date:** 2026-07-08
- **Status:** Approved (design), pending spec review
- **Branch:** `develop`

## 1. Goal

Two deliverables approved by the user:

1. **Aggressively clean up / refactor / optimize** the Python source, apply the changes, and add **maximum-density Vietnamese comments + summaries** to every hand-written source file (all `.py` + the *code cells* of the three notebooks). "Autogen" artifacts (notebook **output** cells, `models/best_model.h5`, `data/*.csv`, `assets/`) are left untouched.
2. **Rewrite** `README.md` and `requirements.txt`; **update** `.gitattributes` and `.gitignore` to fit the repo.

## 2. Scope decisions (from brainstorming)

| Question | Decision |
|---|---|
| Refactor aggressiveness | **Aggressive** (restructure freely) — bounded by the invariant in §3 |
| Comment coverage | `main.py` + `scripts/**/*.py` + notebook **code cells** |
| Comment density | **Maximum detail** (near line-by-line, but meaningful — no `i += 1 # tăng i` noise) |
| `requirements.txt` | Add `ruff` into the single existing file |

## 3. Hard invariant (non-negotiable)

`models/best_model.h5` is a trained artifact that **cannot be regenerated in this session** (needs multi-GB data + long training), and `data/dark_1..3.csv` are existing on-disk data. Therefore the refactor is **aggressive on internal structure but byte-identical on all load-bearing formats**:

- `Log.board_to_enum` output — the 63-char, column-major, case-encoded board string (matches every CSV).
- `encode_board` — the exact float tensor values (`reversed → reshape(7,9) → transpose → flip`), and `PIECE_ENCODING` (dark `+1..+8`, light `-1..-8`, `-`=0).
- Move notation `A1B2` (`move_to_enum` / `enum_to_position`).
- `make_move` / `undo_move` semantics and the `captured_pieces`↔`move_history` sync.
- CSV column set/order in `Log.COLUMNS`.

Any structural change that touches these must reproduce their output exactly (guarded by golden tests, §7). Breaking them is explicitly **out of scope** (would require retraining, which the user did not request).

## 4. Refactor items (all approved)

1. **`common.py` → table-driven piece metadata.** Replace the four parallel families of eight near-identical staticmethods (`CellPosition.{rat..elephant}`, `PieceName.*`, `PieceAvatar.*`, `PieceArtWork.*`) with a single `PIECES` metadata table (key → start positions per side, display names per side, atk, detail text, avatar/artwork path builders). Public accessors preserved (or thinly re-derived) so importers don't change. Kills ~150 lines of duplication.
2. **Slim the eight piece classes.** Keep one class per piece type (required for `isinstance` checks in Rat/Elephant rules) but source all metadata from the `PIECES` table via a small base helper; each subclass keeps only its genuine rule overrides (`can_defeat` / `is_valid_cell` / `weaker_pieces_positions` / river behavior). Removes repeated `__init__`/`copy` boilerplate.
3. **New `scripts/encoding.py`.** Extract the string→tensor encoder `encode_board` + `PIECE_ENCODING` (currently **duplicated between `manager.py` and `train.ipynb`**) into one module. `GameManager` imports it and `train.ipynb` imports it too, ending that duplication. `Log.board_to_enum` (Board→string) **stays in `log.py`** — it depends on `Board`/`Cell` and is `Log`'s own serializer — but the char↔int piece maps are unified so `log.map_piece_name`, `PIECE_ENCODING`, and train's old `PIECE_MAPPING` all derive from one source of truth. Output must stay byte-identical.
4. **`bot.py` — dedup minimax.** Factor the shared tree-walk of `minimax` and `minimax_alpha_beta_pruning` into one internal helper. **Both public functions stay** and keep their exact, *different* tie-set semantics (alpha-beta prunes tied branches, so they are NOT collapsed into one). Removes ~40 duplicated lines.
5. **`manager.py` — extract `ModelEvaluator`.** Move lazy model load + batch inference + "warn once / fall back" into its own class; `GameManager` keeps turn/UI orchestration and delegates ML. Preserves the `ai_move() or computer_move()` fallback behavior.
6. **`log.py` — tidy converters.** Group the small `enum_*` / `*_to_enum` converters consistently; keep the misspelled `enum_to_postion` back-compat alias.

Bot **move-selection behavior is preserved** (the minimax/alpha-beta coin flip, depth 2, BFS/A* routing, and `algorithm_random` weighting all unchanged) — refactor is internal only.

## 5. Comments & summaries

- Max-density Vietnamese comments across `main.py`, `scripts/**/*.py`, and the **code cells** of `merge.ipynb` / `split.ipynb` / `train.ipynb`.
- Every module keeps/gets a module-level summary docstring; every class/function a Vietnamese docstring; non-obvious blocks get inline comments (encoders, make/undo, minimax, trap/river/den rules, repetition rule, argmax/argmin rationale).
- Comments must stay **accurate to the code** — carry over the audit corrections (pipeline is not a linear chain; BFS favored when the opponent has *more* pieces; etc.). No output cells or binary artifacts are edited.

## 6. Meta-file rewrites

- **`README.md`** — rewritten in Vietnamese, corrected to audited facts: non-linear pipeline (`train.ipynb` reads `data/dark_*.csv`, not merge/split output), `ruff` now in requirements, hidden env vars (`CSV_CHUNK_SIZE`/`ROWS_PER_FILE`/`READ_CHUNK_SIZE`/`GPU_LIMIT_MB`/`RANDOM_STATE`), BFS/A* weighting direction, and the **post-refactor module layout** (incl. `scripts/encoding.py`).
- **`requirements.txt`** — add a pinned `ruff`; keep existing pins; keep the notebook dev deps.
- **`.gitattributes`** — keep `text=auto` + LFS rules for `*.csv/*.h5/*.jpg/*.png`; add `*.ipynb text eol=lf` (avoid CRLF churn) and `docs/** linguist-documentation`. Do **not** mark notebooks `linguist-generated` — their code cells are hand-maintained.
- **`.gitignore`** — add `.ruff_cache/` and `.vscode/`; keep the "large derived datasets" block (`data/dark.csv`, `data/light.csv`, `data/animal_chess.csv`, `data/chunks/`, `models/fold_*.keras`).

## 7. Verification (there is no test suite — we build one)

A headless smoke/golden harness, `tools/smoke_test.py`, run with `SDL_VIDEODRIVER=dummy` so Pygame needs no display.

- **Step 0 (before refactor):** run the harness against the *current* code, capture golden values, and embed them as literals in the committed test:
  - `board_to_enum` for the initial board and for 3 scripted positions;
  - `encode_board` tensor (exact values / stable hash) for those positions;
  - `get_valid_moves` counts for both sides at the start;
  - a scripted `make_move`→`undo_move` round-trip restoring identical board string;
  - `Bot.minimax(board, side, 2, True)` best_score + best_moves on the initial board (deterministic).
- **After refactor:** the same harness must reproduce every golden exactly.
- **Model check (optional/skipped gracefully):** if TensorFlow imports and `best_model.h5` is a real file (LFS pulled), assert it loads and `ai_move` returns a legal move; otherwise skip without failing.
- Plus: `py -m compileall -q main.py scripts`, `py -m ruff check main.py scripts`, `nbconvert --execute` preview of all three notebooks, and **one real game launch** to confirm the UI still runs.

## 8. Execution

Ultracode is on. After spec approval → `writing-plans` produces the implementation plan; execution runs as a multi-agent **workflow**: capture goldens first, then per-module refactor+comment agents each re-running the golden test, then the meta-file rewrites, then full verification. Work happens on `develop`.

## 9. Out of scope

- Changing any on-disk format or retraining the model.
- Altering bot move-selection *behavior* (only its internal code shape).
- Adding a full unit-test framework (only the smoke/golden harness).
- Touching assets, CSV data, the `.h5`, or notebook output cells.

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Encoder/format drift silently breaks the model | Golden tests assert byte-identical `board_to_enum`/`encode_board`; §3 invariant |
| Table-driven pieces break `isinstance` rules (Rat/Elephant) | Keep one real class per type; only metadata is table-sourced |
| Aggressive edits break a headless-invisible path | Smoke test exercises board/rules/bot; real game launch for UI |
| `ruff` reformats/complains with no config | Add ruff pinned; fix lints; no behavior change |
| Notebook↔package import coupling (`train.ipynb` → `scripts.encoding`) | Notebooks already run from repo root; import is safe |
