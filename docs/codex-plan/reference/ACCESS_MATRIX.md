# Ma trận quyền truy cập tham chiếu (Codex phải hiện thực hóa bằng RBAC + kiểm tra ownership)

| Chức năng | Guest | User | Admin | Signed payment webhook |
|---|:---:|:---:|:---:|:---:|
| Landing + xem gói công khai | Có | Có | Có | Không |
| Đăng ký / đăng nhập | Có | Không cần | Không cần | Không |
| Live translate / upload | Không | Phiên của mình | Có | Không |
| Xem / xóa transcript | Không | Của mình | Được ủy quyền/audit | Không |
| Xem metrics | Không | Phiên của mình | Giám sát hệ thống | Không |
| Thêm/sửa cấu hình model | Không | Không | Có, cần preflight | Không |
| Xem sức khỏe model/nguồn chạy | Không | Bản public an toàn | Toàn bộ | Không |
| Đặt mua/nạp credit | Không | Tài khoản mình | Có | Không |
| Tự xác nhận paid | Không | KHÔNG | KHÔNG | Chỉ server sau verify |
| Nhận webhook thanh toán | Không | Không | Không | Có: signature hợp lệ |
| Đối soát, hoàn tiền | Không | Không | Có và audit | Không |
| Xem khoá API/HF/PSP | Không | Không | Không hiển thị plaintext | Không |

**Quy tắc:** mọi quyền được kiểm tra ở backend, frontend chỉ ẩn nút để cải thiện UX. WebSocket cần vé ngắn hạn. Không dùng client redirect, screenshot, QR hiển thị hoặc query string làm bằng chứng đã thanh toán.
