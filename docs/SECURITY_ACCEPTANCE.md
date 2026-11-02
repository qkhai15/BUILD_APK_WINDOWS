# Quyền, bảo mật, thử nghiệm và tiêu chí nghiệm thu

## Ma trận quyền đề xuất (để nhà trường phê duyệt)

| Hành động | Admin | Ban giám hiệu/Đức dục | GVCN | Giáo viên trực/nhập liệu |
|---|---|---|---|---|
| Xem toàn trường | Có | Có | Không | Không |
| Xem lớp được phân công | Có | Có | Có | Có |
| Thêm vi phạm | Có | Không | Không | Có, lớp được phân công |
| Sửa/hủy vi phạm | Có | Không | Không | Chỉ bản ghi do mình lập, lớp được phân công |
| Xem báo cáo và export | Có | Toàn trường | Lớp được phân công | Lớp được phân công |
| Quản lý user, lớp, năm học, cảnh báo | Có | Không | Không | Không |
| Xem AuditLog/API import jobs | Có | Không | Không | Không |

**Lưu ý:** Excel không cung cấp thông tin phân quyền. Ma trận này là **phương án kỹ thuật mặc định**, chưa được xác nhận là quy chế trường. Backend kiểm tra cấp API, không dựa vào việc ẩn nút.

## Cơ chế bảo mật đã được lập trình

- Đăng nhập bằng username/password, băm Argon2, JWT HS256 có hạn sử dụng 8 giờ; tài khoản khóa không thể sử dụng token cũ. Không có mật khẩu mặc định.
- API trường học bắt buộc token, kiểm tra lớp được phân công. Người dùng không thể tự chỉ định `recorded_by` hoặc `recorded_at`.
- `Idempotency-Key` unique cho mỗi thao tác nhập; thử lại cùng request không sinh lượt mới. Mỗi thay đổi được ghi AuditLogs gồm actor, trước/sau.
- Xóa mềm `status=void`, yêu cầu lý do; mọi thống kê lọc `status=active`.
- Khi lỗi import, rollback toàn bộ roster và ghi ImportJob thất bại; không ghi dữ liệu thiếu/trùng hoặc nhật ký giả.
- Các cột liên quan có FK/index; database không publish public trong Compose. App release từ chối HTTP; secrets không đặt trong mã nguồn.

## Điều kiện bắt buộc trước triển khai thật

- Cài reverse proxy TLS, domain/VPN và firewall. Compose hiện không tự cấu hình chứng chỉ; không được mở cổng 8000 ra Internet.
- Thêm rate limiting đăng nhập ở gateway/API, rà soát chính sách mật khẩu/MFA/đăng xuất cưỡng bức; hiện chưa có MFA và chưa có cơ chế thu hồi token trước 8 giờ ngoài vô hiệu hóa user.
- Chọn thời gian lưu audit, nhật ký, bản backup và báo cáo tạm; mã hóa backup, kiểm chứng restore; có thỏa thuận xử lý dữ liệu cá nhân theo chính sách được trường phê duyệt.
- Thiết bị Android có chính sách khóa màn hình, cấm chia sẻ bản xuất ra ngoài phạm vi cho phép và quy trình hủy quyền tài khoản nhân sự nghỉ việc.
- Rà soát tác động sửa cảnh báo với dữ liệu lịch sử; trước khi áp dụng nên xuất/ghi lại version cấu hình.
- Quy định chính thức về việc điều chỉnh sai sót, hủy bằng chứng, phụ trách phê duyệt và bảo quản minh chứng.

## Danh sách test và tình trạng

| Kiểm tra | Kết quả tự động | Bước cần thực hiện thêm |
|---|---|---|
| 2.260 HS / 48 lớp, không trùng | Đã đọc và import DB SQLite tạm | Nhập trên máy chủ trường, đối chiếu danh sách |
| Import lại nguyên file | 0 thêm, 2.260 không đổi | Diễn tập Postgres |
| Cảnh báo các ngưỡng 0–7 | Unit test đạt | Kiểm tra UI |
| Nghiêm trọng luôn cao nhất | Unit test đạt | Kiểm tra UI |
| Lưu, sửa, hủy → dashboard/hồ sơ/lớp | API test đạt | Android thật, mạng chập chờn |
| Khóa chống gửi trùng | API test đạt | Kiểm tra nhấn nhanh, mất mạng thực |
| Quyền ngoài lớp / vai trò | API test đạt | Kiểm tra nhiều lớp/giao năm học |
| Khoảng ngày tuần và PDF/XLSX | API test đạt (đúng file, đếm mẫu) | Duyệt bằng mắt, bản in tiếng Việt |
| Hai người nhập cùng lúc | API test bằng 2 luồng | Load test PostgreSQL nhiều thiết bị |
| Thời gian record bất biến khi chỉnh | API test đạt | Kiểm tra múi giờ & DST với DB thực |
| APK cài đặt được trên máy Android | **Chưa kiểm thử** | Flutter SDK + Android SDK + thiết bị |
| Sao lưu và phục hồi | **Chưa kiểm thử** | Khôi phục độc lập trên máy chủ dự phòng |

Không được coi toàn bộ ứng dụng là **đã nghiệm thu** cho đến khi kiểm thử trên hạ tầng và thiết bị được trường cho phép.
