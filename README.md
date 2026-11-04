# DeepVoice

ASR + Machine Translation app, chạy được theo 3 cách: local/native, Docker Compose, hoặc Linux native.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Frontend: http://localhost:5173 — API docs: http://localhost:8000/docs

## Local/native

Yêu cầu Python 3.11+ và Node.js 20+. MongoDB là tùy chọn.

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
```

Terminal khác: `cd frontend && npm install && npm run dev`

Khi không muốn chạy MongoDB, giữ `MONGODB_URL=disabled`. App sẽ dùng in-memory storage; dữ liệu mất khi backend restart. Khi cần persistence, đổi sang `mongodb://localhost:27017`.

## Linux

```bash
chmod +x scripts/run-linux.sh && ./scripts/run-linux.sh
```

ASR mặc định trỏ tới `duyhocfpt/wav2vec2-xlsr-vi-r3`. Model được dùng trực tiếp để inference, không fine-tune và không cắt nhỏ model. Lần chạy đầu sẽ tải khoảng 1.3 GB vào cache Hugging Face.

Nếu chỉ muốn test UI hoặc chưa cài được PyTorch/Transformers, đổi `ASR_PROVIDER=mock`.

API inference yêu cầu JWT: đăng ký/đăng nhập qua `/docs` trước khi upload. QR payment hiện tạo invoice và payload QR; cần cấu hình ngân hàng và webhook/reconciliation thật trước production.
