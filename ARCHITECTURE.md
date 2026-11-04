# DeepVoice architecture

Frontend React/Vite gọi Backend FastAPI qua REST. Backend giữ model registry, inference pipeline, telemetry, auth, payment provider và MongoDB repository. Model adapter tách khỏi business logic: mock chạy mặc định; Hugging Face/local adapter là điểm mở rộng.

Runtime hỗ trợ native Windows/macOS/Linux, Docker Compose và Linux script. Docker MongoDB chạy replica set để transaction có thể dùng được.
