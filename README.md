# AVRT Studio

Ứng dụng dịch Anh ⇄ Việt full-stack, bản nền tảng 0.1. Next.js/TypeScript/Tailwind 4 + FastAPI + MongoDB Replica Set + Redis worker. Giao diện tiếng Việt, màu xanh ngọc, sáng/tối, bố cục responsive, Button theo cấu trúc shadcn/Radix.

## Pull về và chạy trên Windows

Cài **Python 3.12+**, **Node.js 22+** và Git. Sau đó mở PowerShell:

```powershell
git clone https://github.com/yuDDuc/DeepVoice.git
cd DeepVoice
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

Nếu đã clone, chạy `git pull` rồi chạy lại `scripts/start-local.ps1`. Script tạo môi trường Python, cài `backend/requirements-ai.txt`, cài frontend bằng `npm ci`, tải model ASR Việt và MT Việt → Anh vào `models/custom`, tạo `.env` local và chạy FE/BE tại **http://localhost:3000**. Lần đầu cần Internet để tải khoảng 670 MB trọng số; sau đó model chạy offline. Bấm Ctrl+C để dừng cả hai. Không cần Docker cho cách chạy này.

Script tạo tài khoản test local khi database mới. Email là `test@avrt.local`; mật khẩu ngẫu nhiên được in ra terminal và lưu ở `data/test-login.txt` trên **máy của bạn**, không đưa lên GitHub. Nếu mất file này, chạy lại script để đặt mật khẩu test mới. Tài khoản, phiên đăng nhập và lịch sử lưu trong `data/avrt.sqlite3`. Thư mục `data/`, `.env`, môi trường Python/Node và model weights không được commit. Trước khi copy bản cài sang máy khác, dừng app rồi copy cả `data/` nếu muốn giữ tài khoản/lịch sử. Chỉ `git pull` code trên máy mới sẽ tạo một tài khoản test mới ở lần chạy đầu.

Nguồn model tải lần đầu: [ASR Việt](https://huggingface.co/dragonSwing/wav2vec2-base-vietnamese) và [MT Việt → Anh](https://huggingface.co/Helsinki-NLP/opus-mt-vi-en). Nếu đã có model ASR local `duyhocfpt/wav2vec2-xlsr-vi-r3`, script giữ nguyên model đó.

## Chạy trên Windows bằng Docker

1. Giải nén thư mục `AVRT-Studio` vào một đường dẫn bất kỳ trên máy.
2. Mở Docker Desktop, bật Linux containers/WSL2.
3. Mở PowerShell tại thư mục dự án:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Script tạo `.env` từ `.env.example`, sinh JWT secret, rồi build và chạy Docker Compose. Nếu `.env` bật model thật, script tự dùng image worker có AI dependencies. Mở **http://localhost:3000**, đăng ký tài khoản mới. Không có tài khoản admin/mật khẩu mặc định.

Nếu chính sách máy không cho chạy script, thực hiện thủ công:

```powershell
Copy-Item .env.example .env
# Điền JWT_SECRET ngẫu nhiên >=32 ký tự trong .env trước khi chạy production.
docker compose up --build -d
```

Xem log/dừng, không xóa dữ liệu:

```powershell
docker compose logs -f api worker web
docker compose down
```

Mongo và HF cache giữ trong Docker volumes. Mongo/Redis không mở cổng ra máy ngoài. Chỉ bind FE/API lên localhost. Đây là cấu hình phát triển cục bộ; chưa dùng nguyên trạng làm production Internet.

## Copy bản cài offline sang máy khác

Nếu không muốn tải lại model trên máy mới, copy toàn bộ dự án cùng `models/custom/`. `models/cache`, `.venv` và `frontend/node_modules` không cần copy. File `.env` là cấu hình riêng của máy; script dưới đây tạo/cập nhật nó bằng đường dẫn tương đối. Nếu copy cả `data/`, tài khoản và lịch sử cũng được giữ.

Máy mới cần **Python 3.12+ và Node.js 22+**. Tại thư mục dự án, chạy PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-vi-en.ps1
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements-ai.txt
cd frontend
npm ci
cd ..
.\.venv\Scripts\python .\scripts\smoke-vi-en.py
```

`requirements-ai.txt` kéo cả requirements backend và thư viện inference. `npm ci` cài dependencies frontend từ lockfile. Không copy môi trường Python/Node đã cài ở máy cũ sang máy mới.

Chạy backend trong terminal thứ nhất:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Chạy frontend trong terminal thứ hai:

```powershell
cd frontend
npm run dev
```

Mở **http://localhost:3000**, chọn **Việt → Anh**. Dịch văn bản dùng MT thật; micro hoặc upload WAV/MP3 dùng ASR Việt rồi MT thật. Test `smoke-vi-en.py` kiểm tra ASR trên 1 giây im lặng, dịch text, upload WAV và WebSocket audio qua API; chưa đo độ chính xác tiếng nói. Hai file trọng số safetensors chiếm khoảng 1.8 GB; RAM lúc chạy sẽ cao hơn. Cấu hình native dùng `DATABASE_MODE=sqlite` và `INFERENCE_MODE=inline`: tài khoản, phiên đăng nhập và lịch sử được lưu ở `data/avrt.sqlite3` qua các lần chạy lại. Dừng backend trước khi copy dự án sang máy khác để file database nhất quán; copy cả `data/` nếu muốn giữ tài khoản/lịch sử. Docker Compose vẫn dùng Mongo/Redis cho cấu hình nhiều service; `scripts/start.ps1` tự chọn image AI.

## Luồng thử đầu tiên

- Đăng ký → nhập `hello` trong Không gian dịch → bấm Dịch văn bản → nhận `Xin chào` gắn nhãn MOCK.
- Thử câu khác: mock giữ câu gốc trong nhãn minh họa, không giả là dịch AI.
- Xem CPU/RAM/GPU thực tế trong bảng tài nguyên. GPU không có NVML trả N/A. Chỉ số Docker phản ánh môi trường container, có thể khác tổng tài nguyên Windows.
- Xem/xuất/xóa lịch sử của chính tài khoản đó. Tắt lưu lịch sử ở Cài đặt để các bản dịch sau không lưu.
- Nạp credit mock → Tạo đơn thử nghiệm → Mô phỏng đã nhận tiền. Không chuyển tiền thật; không có QR giả. Ví chưa trừ credit theo thời lượng dịch.
- Nhấn micro: trình duyệt lấy PCM16 mono, gửi theo frame có seq/timestamp qua WebSocket; backend gom cụm theo khoảng lặng rồi gọi ASR. ASR mặc định là mock nên **không nhận dạng được lời nói thật** đến khi cấu hình model AI.

## Bật AI thật từ Hugging Face/local

Xem [docs/MODELS.md](docs/MODELS.md). Mặc định không tải trọng số khi mở UI. Chỉ adapter được dùng mới lazy-load model. Image mặc định chỉ cài backend nhẹ; bật image có AI:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml up --build -d
```

Sửa `.env` phía server để chọn `hf_hub`, `hf_remote` hoặc `local` cho từng role; `restart worker api` sau thay đổi, hoặc `up -d --force-recreate worker api` khi Docker env_file thay đổi. Các `NEXT_PUBLIC_*` là public và cần rebuild web. Không đưa token HF vào chúng.

Để cấp admin sau khi đã đăng ký:

```powershell
docker compose exec api python -m app.cli promote your-email@example.com
```

Admin có warmup và audit API. Cấu hình model hiện đổi qua `.env`, UI hiển thị nguồn/model/health; chưa có chức năng tự ghi `.env` từ trình duyệt.

## Dev không có Docker

Python 3.12+, Node 22+. Để test UI/API độc lập với Mongo/Redis:

```powershell
Copy-Item .env.example .env
# Sửa DATABASE_MODE=memory và INFERENCE_MODE=inline trong .env
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements-dev.txt
$env:PYTHONPATH = 'backend'
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Terminal khác:

```powershell
cd frontend
npm ci
npm run dev
```

`DATABASE_MODE=memory` chỉ phù hợp test/tạm thời và mất tài khoản, cookie JWT cùng lịch sử sau khi khởi động lại. Muốn lưu bền khi chạy native, dùng `scripts/setup-vi-en.ps1` để chọn SQLite. Next proxy `/api/v1` và `/ws/v1` tới `127.0.0.1:8000`; ở Docker build tới `api:8000`.

## Kiểm tra

```powershell
$env:PYTHONPATH = 'backend'
.\.venv\Scripts\python -m pytest backend/tests -q
cd frontend
npm run typecheck
npm run build
```

Các test dùng MemoryStore và mock inference, gồm CSRF, refresh rotation/replay, ownership hai tài khoản, consent cloud, upload WAV, one-time WS ticket/origin/PCM, cấu hình shape/path, GPU fallback, chữ ký webhook, amount mismatch, late payment và credit idempotency khi nhiều thread.

Trạng thái kiểm chứng, phần chưa làm và bước tiếp theo nằm tại [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md). Chưa kiểm thử Docker/real Mongo transaction/GPU/HF inference/payOS merchant trên môi trường thực. Không coi unit test là bằng chứng các tích hợp đó đã chạy.

## Tài liệu

- [Kiến trúc và contract WebSocket](docs/ARCHITECTURE.md)
- [Cấu hình model](docs/MODELS.md)
- [Thanh toán](docs/BILLING.md)
- [Trạng thái triển khai](docs/IMPLEMENTATION_STATUS.md)
- `docs/architecture/`: ERD, access, streaming, payment, model lifecycle, OpenAPI JSON.
- `docs/codex-plan/`: bộ yêu cầu/prompts gốc. Catalog 303 biến trong đó là **kế hoạch đích**; chỉ `.env.example` ở **gốc dự án** là catalog runtime bản này.
