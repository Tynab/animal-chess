# Animal Chess

Animal Chess là trò chơi chiến thuật hai người dựa trên Đấu Thú Kỳ, xây dựng bằng Pygame. Repo gồm engine luật chơi, giao diện desktop, bot tìm kiếm, model CNN đánh giá thế cờ và pipeline notebook để thu thập, tăng cường, chia và huấn luyện dữ liệu.

<p align="center">
  <a href="https://tynab.github.io/Animal-Chess">Chơi bản demo</a>
</p>

<p align="center">
  <img src="pic/0.jpg" alt="Giao diện Animal Chess" width="900">
</p>

## Tính năng kỹ thuật

- Bàn cờ 7×9 với sông, bẫy, hang và tám loại quân cho mỗi phe.
- Ba chế độ: người-người (PvP), người-máy (PvC) và máy-máy (CvC).
- Bot hỗ trợ minimax, alpha-beta pruning, BFS và A*.
- Model CNN dự đoán điểm thế cờ; mọi nước hợp lệ được suy luận theo một batch.
- Tự chuyển sang minimax nếu model H5 thiếu hoặc không nạp được (cảnh báo đúng một lần).
- Ghi dữ liệu từng ván vào CSV trong `data/` để tái huấn luyện.
- Notebook xử lý CSV theo chunk, tránh nạp toàn bộ tập dữ liệu nhiều GB vào RAM.

## Công nghệ

- Python 3.11
- Pygame 2.6
- NumPy, pandas, scikit-learn
- TensorFlow/Keras 2.19 và HDF5
- Jupyter Notebook
- ruff (lint)
- Git LFS cho CSV, H5 và ảnh

## Cấu trúc repo

```text
animal-chess/
├── assets/                  # Ảnh bàn cờ, quân và artwork (Git LFS)
├── data/                    # CSV gốc + CSV sinh khi chơi (Git LFS)
│   ├── dark_1.csv
│   ├── dark_2.csv
│   └── dark_3.csv
├── docs/                    # Tài liệu thiết kế/kế hoạch
├── models/
│   └── best_model.h5        # Model CNN tốt nhất (Git LFS)
├── pic/                     # Ảnh minh họa README
├── scripts/
│   ├── pieces/              # Luật riêng của tám loại quân
│   ├── board.py             # State bàn cờ và make/undo đối xứng
│   ├── bot.py               # Minimax/alpha-beta (chung _search), BFS, A*
│   ├── cell.py              # Ô, địa hình và hiệu lực bẫy
│   ├── common.py            # Hằng số, bảng PIECES, tài nguyên, ánh xạ
│   ├── encoding.py          # Mã hóa bàn cờ -> tensor (dùng chung game + train)
│   ├── log.py               # Mã hóa và ghi dữ liệu ván đấu
│   ├── manager.py           # GameManager (điều phối) + ModelEvaluator (model AI)
│   ├── piece.py             # Luật quân cơ sở + RiverJumper (nhảy sông)
│   └── rendering.py         # Render Pygame
├── tools/
│   └── smoke_test.py        # Golden/smoke test headless (không cần asset/LFS)
├── main.py                  # Entry point
├── merge.ipynb              # Hợp nhất và tăng cường dữ liệu
├── split.ipynb              # Chia CSV lớn an toàn
├── train.ipynb              # Cross-validation và xuất model
└── requirements.txt
```

## Cài đặt

Repo chứa file lớn qua Git LFS. Cài Git LFS trước khi clone hoặc chạy `git lfs pull` nếu các file CSV/H5 mới chỉ là pointer.

```powershell
git lfs install
git lfs pull
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

TensorFlow 2.19 trên Windows chạy CPU theo gói chính thức. Nếu cần GPU, hãy dùng môi trường được TensorFlow hỗ trợ (ví dụ WSL2) và cấu hình driver tương ứng.

## Chạy game

```powershell
py main.py
```

Chế độ mặc định là PvC. Có thể đổi `DEFAULT_GAME_MODE` trong `main.py` thành `GameMode.PvP` hoặc `GameMode.CvC`. Phe sáng đi trước; trong PvC người chơi điều khiển phe sáng.

## Cách máy chọn nước đi

Mỗi lượt máy chạy `ai_move() or computer_move()`:

- **`ai_move`** (ModelEvaluator): nạp `best_model.h5` một lần, mã hóa mọi thế cờ-sau-nước-đi và suy luận theo một batch; phe tối chọn `argmax`, phe sáng chọn `argmin` (điểm luôn theo góc nhìn phe tối). Nếu model thiếu/không nạp được, trả `None` và cảnh báo một lần.
- **`computer_move`** (fallback minimax): tung đồng xu 50/50 giữa minimax và alpha-beta (đều depth 2), rồi định tuyến các nước đồng điểm qua BFS hoặc A*. Xác suất chọn BFS **tăng khi đối phương còn nhiều quân** (đầu ván) và nghiêng về A* ở tàn cuộc.

## Luồng dữ liệu và huấn luyện

Ba notebook mặc định chạy ở chế độ preview: đọc dữ liệu thật, kiểm tra schema và cập nhật output nhưng không tạo file nhiều GB hoặc huấn luyện dài. Bật từng tác vụ nặng một cách tường minh trong PowerShell.

> **Lưu ý:** ba notebook **không phải một chuỗi tuyến tính**. `train.ipynb` đọc thẳng `data/dark_*.csv` ở thư mục gốc (log ván thô + seed `dark_1..3.csv`), **không** dùng output của `merge`/`split`. `merge`/`split` là tiện ích tăng cường/chia dữ liệu, không bắt buộc để huấn luyện.

### 1. Hợp nhất và tăng cường

```powershell
$env:RUN_DATA_PIPELINE='1'
py -m jupyter nbconvert --to notebook --execute --inplace merge.ipynb
Remove-Item Env:RUN_DATA_PIPELINE
```

Notebook đọc `data/dark_*.csv`, tạo mẫu phe sáng bằng phép xoay 180° + đảo dấu và xuất:

- `data/dark.csv`
- `data/light.csv`
- `data/animal_chess.csv` (đã bỏ cột `id`)

Kích thước chunk đọc chỉnh qua `CSV_CHUNK_SIZE` (mặc định 250000).

### 2. Chia file lớn

```powershell
$env:RUN_DATA_SPLIT='1'
py -m jupyter nbconvert --to notebook --execute --inplace split.ipynb
Remove-Item Env:RUN_DATA_SPLIT
```

Đọc `data/dark.csv` và ghi nguyên tử các chunk (`.tmp` rồi đổi tên) vào `data/chunks/`. Số dòng mỗi chunk chỉnh qua `ROWS_PER_FILE` (mặc định 15000000). Muốn xóa ba file dẫn xuất sau khi chia thành công, đặt thêm `DELETE_DERIVED_SOURCES=1`.

### 3. Huấn luyện model

```powershell
$env:RUN_MODEL_TRAINING='1'
$env:MAX_TRAIN_ROWS='1000000'
py -m jupyter nbconvert --to notebook --execute --inplace train.ipynb --ExecutePreprocessor.timeout=-1
Remove-Item Env:RUN_MODEL_TRAINING
Remove-Item Env:MAX_TRAIN_ROWS
```

Notebook mã hóa bàn cờ bằng chính `scripts.encoding.encode_board` (giống hệt lúc chơi, để train/inference nhất quán), dựng tensor `(9, 7, 1)` gồm hai khối Conv2D–BatchNorm–LeakyReLU–MaxPool, Dense 2048 có L2/Dropout và đầu ra tuyến tính một điểm. KFold 5 fold; fold có validation loss thấp nhất được lưu vào `models/best_model.h5`. Các biến điều chỉnh khác: `MAX_TRAIN_ROWS`, `READ_CHUNK_SIZE` (100000), `GPU_LIMIT_MB` (10240); seed `RANDOM_STATE=42`.

## Schema dữ liệu

| Cột | Ý nghĩa |
|---|---|
| `id` | UUID của ván |
| `board` | Chuỗi 63 ký tự, chữ thường là phe tối và chữ hoa là phe sáng |
| `side` | `1` phe tối, `-1` phe sáng |
| `piece`, `atk` | Quân vừa đi và sức mạnh tại ô đích |
| `move` | Nước đi dạng `A1B2` |
| `river`, `trap`, `den` | Đặc trưng địa hình của ô đích |
| `score` | Điểm thế cờ từ góc nhìn phe tối |
| `winner` | `1`, `-1` hoặc `0` khi ván chưa kết thúc |

## Tóm tắt mã nguồn

| File | Trách nhiệm chính |
|---|---|
| `main.py` | Khởi tạo Pygame, xử lý sự kiện và vòng lặp game bất đồng bộ. |
| `scripts/common.py` | Bảng metadata `PIECES`, hằng số bàn/trạng thái/tọa độ và đường dẫn asset. |
| `scripts/encoding.py` | `PIECE_ENCODING`, `encode_board` — mã hóa bàn cờ thành tensor CNN, dùng chung bởi game và `train.ipynb`. |
| `scripts/cell.py` | Đồng bộ quân với ô và đặt sức mạnh về 0 trong bẫy đối phương. |
| `scripts/piece.py` | Luật bốn hướng, bắt quân, hang nhà, `RiverJumper` nhảy sông và helper dựng quân từ bảng. |
| `scripts/board.py` | Dựng bàn, sinh nước hợp lệ, thắng/thua và make/undo đối xứng. |
| `scripts/bot.py` | Đánh giá vật chất, minimax/alpha-beta (chung `_search`), BFS và A*. |
| `scripts/log.py` | Mã hóa bàn/nước đi và ghi nhiều ván vào một CSV phiên. |
| `scripts/manager.py` | `GameManager` điều phối lượt/click và `ModelEvaluator` nạp model + suy luận batch + fallback. |
| `scripts/rendering.py` | Nạp tài nguyên lười và vẽ màn hình/bàn/thẻ quân. |
| `scripts/pieces/*.py` | Tám quân: chỉ khai báo `KEY` metadata + luật đặc biệt (Chuột↔Voi, Chó/Chuột đi sông, Hổ/Sư nhảy sông). |
| `tools/smoke_test.py` | Golden/smoke test headless chốt các bất biến format/luật/bot. |
| `merge.ipynb` | Hợp nhất/tăng cường theo chunk, giữ dữ liệu gốc. |
| `split.ipynb` | Chia file qua file tạm, tùy chọn dọn dữ liệu dẫn xuất. |
| `train.ipynb` | Mã hóa (dùng `scripts.encoding`), KFold độc lập và lưu model tốt nhất. |

## Kiểm tra chất lượng

```powershell
py tools\smoke_test.py
py -m compileall -q main.py scripts
py -m ruff check main.py scripts
py -m jupyter nbconvert --to notebook --execute --inplace merge.ipynb split.ipynb train.ipynb
```

`tools/smoke_test.py` chạy headless (không cần asset/LFS) và chốt các bất biến quan trọng: chuỗi bàn cờ, tensor mã hóa, sinh nước hợp lệ, đối xứng make/undo và kết quả minimax. Lệnh notebook cuối chạy preview an toàn khi không đặt các biến môi trường `RUN_*`.
