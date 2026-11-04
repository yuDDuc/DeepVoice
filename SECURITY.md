# Security checklist

- Password hash PBKDF2-HMAC-SHA256, không lưu plaintext.
- JWT có expiry và role claim.
- Upload có giới hạn kích thước.
- Payment reference idempotent ở database.
- Không commit `.env` thật.
- Trước production cần bật HTTPS, CORS allowlist, rate limit phân tán, webhook signature của ngân hàng/payment provider và secret manager.
