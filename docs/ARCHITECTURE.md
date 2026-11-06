# Kiến trúc triển khai 0.1

Next.js phục vụ UI, proxy HTTP `/api/v1/*` và WebSocket `/ws/v1` tới FastAPI. FastAPI xử lý auth/RBAC/ownership/session/billing; Redis hàng đợi inference; worker resident giữ model weights và chạy ASR/MT/TTS. MongoDB replica set lưu tài khoản, refresh session, vé WS, lịch sử, đơn, ledger, audit và outbox.

Đăng ký luôn role user. Cấp admin bằng CLI tại máy chủ. Password Argon2id; access JWT trong HttpOnly cookie, refresh ngẫu nhiên chỉ hash phía database; refresh rotation một lần; logout xóa refresh để thu hồi access tương ứng. CSRF double-submit và kiểm origin cho mutations; WS ticket dùng một lần, TTL ngắn, gửi ở frame đầu, không nằm URL/logs.

## WebSocket

1. POST `/api/v1/ws-ticket` có cookie + CSRF.
2. Kết nối `/ws/v1`, Origin phải khớp FRONTEND_ORIGIN.
3. Frame JSON đầu: `{ticket,direction:"en-vi"|"vi-en",tts:false}`.
4. Server trả ready: sample_rate/frame_ms/max_buffer_ms/mode/mock.
5. Mỗi binary frame: `seq uint32 LE` (4 byte), `timestamp_ms float64 LE` (8 byte), tiếp theo PCM int16 LE mono. Seq bắt đầu 0, tăng liên tục; server ACK từng frame, reject sai seq/size.
6. RMS VAD bỏ frame im lặng đầu, gom lời nói tới khoảng lặng hoặc giới hạn buffer. RMS là baseline, chưa phải Silero VAD.
7. Server gửi processing → segment (`source_text`, `target_text`, `state`, `verification`, `timings`, `mock`). Khi stop, flush phần còn lại → done → close.

Đây là **streaming audio + utterance inference**, chưa incremental ASR, Local Agreement, rollback phụ đề hoặc native streaming TTS. Khi quá nhiều frame chưa ACK, client dừng và báo inference chậm, không âm thầm bỏ tiếng. Partial frame cuối được flush từ AudioWorklet khi dừng.

TTS live xếp hàng và phát sau khi dừng mic nhằm giảm echo. TTS text có thể phát ngay. Semantic verification chưa có; quy tắc số/phủ định chỉ cảnh báo sơ bộ. Mock TTS trả null và không tạo âm thanh giả.

## Telemetry

Sampler psutil/NVML chạy định kỳ độc lập với inference. Worker gửi snapshot Redis; UI polling API hiển thị worker khi có, gateway khi không. GPU%/VRAM là toàn thiết bị, không phải VRAM của riêng model; remote GPU luôn null. Process metrics không đọc được trả null. P50/P95 tính inference elapsed time theo user trong cửa sổ gần nhất, không bao gồm queue/network/mic latency. Lịch sử latency tại API in-memory và không hợp nhất giữa nhiều API replicas.

## Sơ đồ

Các `.mmd` trong thư mục architecture là **tham chiếu kiến trúc đích**, giữ nguyên từ prompt pack đã đọc. ERD đầy đủ có các entity chưa triển khai (subscription, speaker profile, consent collection riêng). Bản hiện tại lưu consent/wallet balance trong user, segments trong session. Không dùng sơ đồ đích để tuyên bố schema đã hoàn tất.

OpenAPI JSON được xuất từ API thực tế bản 0.1. Swagger live mặc định `/docs` trên API port; khi mở localhost:8000/docs, đây là Swagger trên origin API riêng, dùng cookie/CSRF theo contract hoặc qua frontend cùng origin.

## Giới hạn và tiến trình tiếp

- Một API replica trong Compose; WS count/latency aggregation in-memory chưa phân tán.
- Token expiry trong phiên WS dài được giới hạn bởi session timeout, không tái xác thực từng frame; cải tiến reauth khi access hết hạn là việc tiếp theo.
- Hàng đợi Redis bounded; jobs có deadline, cancellation marker, TTL result. Không có retry tự động cho inference lỗi để tránh phát/dịch trùng.
- Rate limit Redis khi dùng Redis inference, in-memory chỉ dev. Cần rate limit ở reverse proxy cho ingress public, kiểm soát chunked-body upload trước parser.
- Mongo TTL xóa lịch sử, vé WS, refresh. Raw audio không lưu vào DB/đĩa, chỉ trong RAM và Redis job/result TTL. Redis queue không bật AOF; không coi audio là lưu dài hạn.

Sơ đồ code thực tế nằm ở `architecture/implemented_erd.mmd` và `architecture/implemented_flow.mmd`; dùng hai file này khi kiểm tra schema bản 0.1. Payload job Redis nằm trong key riêng có TTL bằng JOB_TIMEOUT_S; queue chỉ giữ ID và được dọn khi request hoàn tất/timeout. Result có TTL riêng.
