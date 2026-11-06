# Billing

Bản này có ví credit nguyên, order idempotent theo user + Idempotency-Key, sổ cái duy nhất theo order, outbox pending và MongoDB multi-document transaction khi xác nhận tiền. Chưa triển khai subscription, hoàn tiền, đối soát định kỳ, email outbox dispatcher hay trừ credit theo inference. Các mục đó không được coi hoàn thành.

## Mock

PAYMENT_PROVIDER=mock, PAYMENT_TEST_MODE=true, APP_ENV=development/test. Nút mô phỏng là thao tác test, không có QR chuyển khoản hoặc thông báo giả nhận tiền ngân hàng. Endpoint simulate bị chặn trong production và khi dùng payOS.

## payOS

Điền PAYOS_CLIENT_ID, PAYOS_API_KEY, PAYOS_CHECKSUM_KEY trong `.env` của máy chạy. Không gửi chúng vào chat hay frontend. Chọn PAYMENT_PROVIDER=payos. PAYMENT_TEST_MODE không phải sandbox payOS: đơn payOS dùng merchant thật; chỉ sử dụng khi chủ dự án cấu hình hợp lệ.

Tạo payment link qua API v2, ký HMAC 5 trường theo tài liệu, kiểm chữ ký response, trả checkout URL/QR payload từ provider. UI mở trang QR do payOS host; không tự dựng QR như bằng chứng đã nhận tiền. Nếu request tạo link thất bại, order chuyển provider_error để tránh tự động gọi lại tạo nhiều link; admin phải đối chiếu orderCode với payOS trước khi xử lý tiếp.

Đăng ký webhook HTTPS tại merchant:

```
POST /api/v1/billing/webhook/payos
```

Flow: kiểm HMAC toàn bộ `data` → kiểm signed `data.code` → đối chiếu orderCode, amount integer VND, currency, paymentLinkId, accountNumber, reference → short Mongo transaction (order paid, unique event, ledger, wallet increment, outbox). Không dùng outer success/redirect/screenshot làm bằng chứng. Giao dịch đến sau expiry chuyển manual_review và không tự cộng tiền. Trùng event/order không cộng lần hai. Không giữ DB transaction trong lúc gọi mạng.

Mongo standalone bị từ chối lúc boot. Production cần thêm TLS reverse proxy, Mongo authentication/network policy/secrets rotation, backup, audit retention, provider reconciliation và outbox dispatcher trước khi phục vụ khách thật. Compose hiện chỉ dành cho local.

Kiểm thử đã chạy: unit/mock chữ ký sai, amount mismatch, duplicate khi concurrent, late payment. Chưa chạy merchant sandbox hoặc xác nhận transaction trên replica set thật.

Tài liệu provider đối chiếu: https://payos.vn/docs/api/ ; https://payos.vn/docs/du-lieu-tra-ve/webhook/
