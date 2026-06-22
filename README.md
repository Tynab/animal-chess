# Animal Chess

Animal Chess là trò chơi chiến thuật hai người dựa trên Đấu Thú Kỳ, được xây dựng bằng Pygame. Repo gồm engine luật chơi, giao diện desktop, bot tìm kiếm, model CNN đánh giá thế cờ và pipeline notebook để thu thập, tăng cường, chia và huấn luyện dữ liệu.

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
- Tự chuyển sang minimax nếu model H5 thiếu hoặc không nạp được.
- Ghi dữ liệu từng ván vào CSV trong `data/` để tái huấn luyện.
- Notebook xử lý CSV theo chunk, tránh nạp toàn bộ tập dữ liệu nhiều GB vào RAM.

## Công nghệ

- Python 3.11
- Pygame 2.6
- NumPy, pandas, scikit-learn
- TensorFlow/Keras 2.19 và HDF5
- Jupyter Notebook
- Git LFS cho CSV, H5 và ảnh

## Cấu trúc repo

```text
animal-chess/
├── assets/                  # Ảnh bàn cờ, quân và artwork
├── data/                    # CSV gốc/CSV sinh trong quá trình chơi
│   ├── dark_1.csv
│   ├── dark_2.csv
│   └── dark_3.csv
├── models/
│   └── best_model.h5        # Model CNN tốt nhất
├── pic/                     # Ảnh minh họa README
├── scripts/
│   ├── pieces/              # Luật riêng của tám loại quân
│   ├── board.py             # State bàn cờ và make/undo
│   ├── bot.py               # Minimax, alpha-beta, BFS, A*
│   ├── cell.py              # Ô, địa hình và hiệu lực bẫy
│   ├── common.py            # Hằng số, tài nguyên, ánh xạ
│   ├── log.py               # Mã hóa và ghi dữ liệu ván đấu
│   ├── manager.py           # Điều phối UI, bot và model
│   ├── piece.py             # Luật quân cơ sở/nhảy sông
│   └── rendering.py         # Render Pygame
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

## Luồng dữ liệu và huấn luyện

Ba notebook mặc định chạy ở chế độ preview: đọc dữ liệu thật, kiểm tra schema và cập nhật output nhưng không tạo file nhiều GB hoặc huấn luyện dài. Bật từng tác vụ nặng một cách tường minh trong PowerShell.

### 1. Hợp nhất và tăng cường

```powershell
$env:RUN_DATA_PIPELINE='1'
py -m jupyter nbconvert --to notebook --execute --inplace merge.ipynb
Remove-Item Env:RUN_DATA_PIPELINE
```

Notebook đọc `data/dark_*.csv`, tạo ảnh đối xứng cho phe sáng và xuất:

- `data/dark.csv`
- `data/light.csv`
- `data/animal_chess.csv` (đã bỏ cột `id`)

### 2. Chia file lớn

```powershell
$env:RUN_DATA_SPLIT='1'
py -m jupyter nbconvert --to notebook --execute --inplace split.ipynb
Remove-Item Env:RUN_DATA_SPLIT
```

Các chunk được ghi nguyên tử vào `data/chunks/`. Muốn xóa ba file dẫn xuất sau khi chia thành công, đặt thêm `DELETE_DERIVED_SOURCES=1`.

### 3. Huấn luyện model

```powershell
$env:RUN_MODEL_TRAINING='1'
$env:MAX_TRAIN_ROWS='1000000'
py -m jupyter nbconvert --to notebook --execute --inplace train.ipynb --ExecutePreprocessor.timeout=-1
Remove-Item Env:RUN_MODEL_TRAINING
Remove-Item Env:MAX_TRAIN_ROWS
```

Model nhận tensor `(9, 7, 1)`, gồm hai khối Conv2D–BatchNorm–Activation–MaxPool, Dense 2048 có L2/Dropout và đầu ra tuyến tính một điểm. Mỗi fold tạo model/callback mới; fold có validation loss thấp nhất được lưu vào `models/best_model.h5`.

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
| `main.py` | Khởi tạo Pygame, xử lý sự kiện và vòng lặp game responsive. |
| `scripts/common.py` | Cấu hình bàn, trạng thái, tọa độ và đường dẫn asset tuyệt đối. |
| `scripts/cell.py` | Đồng bộ quân với ô và đặt sức mạnh về 0 trong bẫy đối phương. |
| `scripts/piece.py` | Luật bốn hướng, bắt quân, hang nhà và mixin nhảy sông. |
| `scripts/board.py` | Dựng bàn, sinh nước hợp lệ, thắng/thua và make/undo đối xứng. |
| `scripts/bot.py` | Đánh giá vật chất, minimax, alpha-beta, BFS và A*. |
| `scripts/log.py` | Mã hóa bàn/nước đi và ghi nhiều ván vào một CSV phiên. |
| `scripts/manager.py` | Điều phối lượt, click chuột, suy luận batch và fallback bot. |
| `scripts/rendering.py` | Nạp tài nguyên lười và vẽ màn hình/bàn/thẻ quân. |
| `scripts/pieces/rat.py` | Chuột đi sông và khắc chế Voi. |
| `scripts/pieces/cat.py` | Mèo cấp 2 theo luật cơ sở. |
| `scripts/pieces/dog.py` | Chó cấp 3 có quyền đi sông theo luật dự án. |
| `scripts/pieces/wolf.py` | Sói cấp 4 theo luật cơ sở. |
| `scripts/pieces/leopard.py` | Báo cấp 5 theo luật cơ sở. |
| `scripts/pieces/tiger.py` | Hổ cấp 6 nhảy qua sông. |
| `scripts/pieces/lion.py` | Sư tử cấp 7 nhảy qua sông. |
| `scripts/pieces/elephant.py` | Voi cấp 8 và ngoại lệ khi đối đầu Chuột. |
| `merge.ipynb` | Hợp nhất/tăng cường theo chunk, giữ dữ liệu gốc. |
| `split.ipynb` | Chia file qua file tạm, tùy chọn dọn dữ liệu dẫn xuất. |
| `train.ipynb` | Mã hóa, KFold độc lập và lưu model tốt nhất. |

## Kiểm tra chất lượng

```powershell
py -m compileall -q main.py scripts
py -m ruff check main.py scripts
py -m jupyter nbconvert --to notebook --execute --inplace merge.ipynb split.ipynb train.ipynb
```

Lệnh notebook cuối chạy preview an toàn khi không đặt các biến môi trường `RUN_*`.
