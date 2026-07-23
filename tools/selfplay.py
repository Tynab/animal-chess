# tools/selfplay.py
"""Sinh dữ liệu self-play SẠCH cho Rung 3 (headless, không cần màn hình).

Chính sách sinh: các ply sau khai cuộc dùng engine tìm kiếm sâu
(SearchEngine.best_move ở max_depth thấp) + ngẫu nhiên hoá khai cuộc
(OPENING_RANDOM_PLIES ply đầu) để đa dạng ván. Ván vượt MAX_PLIES bị cắt và
tính hòa (dòng cuối winner=0). Ghi qua Log rồi đổi tên file thành
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
from scripts.search import SearchEngine


def _play_one_game(
    gm: GameManager, max_plies: int, opening_random_plies: int, engine: SearchEngine
) -> None:
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
            move, _ = engine.best_move(gm.board, gm.current_side)  # engine tìm kiếm sâu
            if move is None:
                break
        gm.board.make_move(move)
        gm.log.insert_chess_record(gm.board, move)
        if gm.board.is_game_over:                         # nước vừa đi kết thúc ván
            break
        gm.switch_player()
    gm.log.save()                                         # lưu ván (kể cả cap-draw)


def generate(
    games: int, max_plies: int, opening_random_plies: int, out_dir: Path, max_depth: int
) -> Path:
    """Sinh `games` ván, trả về đường dẫn CSV selfplay_<timestamp>.csv."""
    gm = GameManager(GameMode.CvC)
    gm.log = Log(output_dir=out_dir)
    engine = SearchEngine(time_budget_s=None, max_depth=max_depth)
    for i in range(games):
        _play_one_game(gm, max_plies, opening_random_plies, engine)
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
    max_depth = int(os.getenv("SELFPLAY_MAX_DEPTH", "4"))
    seed = os.getenv("SELFPLAY_SEED")
    if seed is not None:
        random.seed(int(seed))
    path = generate(games, max_plies, opening, DATA_DIR, max_depth)
    print(f"SELFPLAY_DONE {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
