# Trạng thái AVRT Studio — 06/11/2026

Bản nền tảng 0.1 đã tạo code FE/BE và kiểm thử mock. Chiều Việt → Anh đã chạy ASR và MT local thật trên Windows qua API test; chưa đánh giá tiếng nói thực tế hay hoàn tất toàn bộ 8 stage AI→PCB.

| Phần | Trạng thái | Bằng chứng / giới hạn |
|---|---|---|
| Next.js, TypeScript, Tailwind, Radix/shadcn-style Button | Đã build | typecheck + production build pass |
| Login/register/logout/rotating refresh, RBAC, ownership | Đã test | API tests; chưa email verification/reset password |
| Dịch text / upload WAV / WS PCM hai chiều | Mock tests; text và WAV Việt → Anh đã chạy local models | Cụm audio/VAD RMS; chưa test micro thật hoặc độ chính xác ASR |
| Adapter HF Hub/local/remote | Local ASR Việt + MT Việt → Anh đã test | HF Remote chưa test; chưa benchmark model |
| Shape, model/source/device từ env | Có validation | Format chỉ Transformers; không universal loader |
| CPU/RAM/NVML, inference latency | Có sampler | Test xác nhận số thật/null, không giả GPU HF; chưa test NVIDIA |
| History/export/delete & consent | Đã test ownership | Raw audio không lưu lâu; speaker memory chưa làm |
| Wallet/orders/ledger/mock credit | Đã test | Concurrent idempotency; chưa metering/subscription |
| payOS signed checkout/webhook | Có implementation + unit tests | Chưa merchant integration test; Google Pay disabled |
| Mongo Replica Set + Redis worker + CPU/GPU Compose | Có cấu hình | Môi trường hiện không có Docker/Mongo/Redis daemon để chạy đầy đủ |
| SQLite local | Đã test | Tài khoản, refresh session, lịch sử và credit mock tồn tại qua restart; chỉ dùng cho chạy local một backend |
| Mermaid + OpenAPI | Có file | Mermaid là kiến trúc đích; OpenAPI từ code thực tế |
| Browser QA | Landing/login đã mở kiểm tra | Chưa browser E2E sau đăng nhập, mic thật hoặc mobile viewport |
| Predictive / accent adaptation / speaker memory | Chưa triển khai | Không mô phỏng như đã có |
| ONNX/CT2/quantization/ARM/PCB | Chưa triển khai | Cần các checkpoint AI và hardware sau |

## Kiểm tra đã chạy

- `PYTHONPATH=backend pytest backend/tests -q --basetemp .tmp/pytest-sqlite -p no:cacheprovider`: 18 tests pass trên Windows.
- `python scripts/smoke-vi-en.py`: ASR local chạy trên 1 giây im lặng; MT local dịch "Xin chào, tôi tên là An." → "Hello, my name is An." qua API; upload WAV và WebSocket audio qua ASR+MT trả `mock=false`.
- `npm run typecheck`: pass.
- `npm run build`: pass, Next.js 16.4.3.
- OpenAPI generation: pass.
- Trình duyệt: landing và form đăng nhập hiển thị; không yêu cầu tài khoản thật cho QA.
- Backend tests có cảnh báo deprecation Starlette/httpx trong bộ dependency hiện tại; không làm fail test.

## Bước tiếp theo trên máy Windows

1. Copy dự án kèm `models/custom`, chạy `scripts/setup-vi-en.ps1` và `scripts/start.ps1`; xác nhận cả 5 service healthy trên Docker.
2. Test Mongo transaction/rollback + Redis worker thật, WebSocket qua Next proxy, đăng nhập và upload/mic trên localhost.
3. Test ASR/MT Việt → Anh trên tập audio tiếng nói cố định; chọn model cho chiều Anh → Việt và đo WER/chrF/latency/RAM.
4. Thêm incremental ASR/Local Agreement; kiểm soát stable/confirmed/corrected và TTS verified. Dùng metric để quyết định model, không chốt theo tên/model size.
5. Tích hợp payOS sandbox/merchant đủ điều kiện, test signed webhook thật; thêm đối soát, refund, outbox dispatcher, metering trước khi thu tiền.
6. Speaker memory có consent, code-switch benchmark, predictive A/B test, hybrid routing có fallback. Sau đó ONNX/quantization/ARM validation → board → prototype → PCB.

## Prompt tiếp tục

```text
Đọc README.md, docs/IMPLEMENTATION_STATUS.md, docs/ARCHITECTURE.md,
docs/MODELS.md, .env.example và bộ yêu cầu ở docs/codex-plan/.
Kiểm tra git status và giữ nguyên thay đổi hiện có.
Chạy Docker Compose trên máy này, sửa lỗi thực tế để hoàn tất luồng:
đăng ký → chọn cấu hình model HF/local qua env → dịch mic/upload
→ xem tài nguyên worker → lưu/xuất lịch sử → mock credit idempotent.
Không đánh dấu tích hợp HF/GPU/payOS hoàn tất nếu chưa test thật.
Cập nhật trạng thái và báo bằng chứng chạy; sau đó tiếp tục incremental ASR.
```
