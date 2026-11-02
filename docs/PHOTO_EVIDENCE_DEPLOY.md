# Ảnh minh chứng, ghi chú và triển khai APK — THĐ v0.7

## Chức năng được bổ sung

- Flutter Android: hai nút **Chụp ảnh** (camera) và **Chọn ảnh** (thư viện), tối đa 3 ảnh cho một vi phạm; ảnh được xem trong Hồ sơ học sinh / Nhật ký và có thể bổ sung sau khi tạo bản ghi.
- PWA: nhập ảnh qua camera/tệp, bổ sung ảnh trong Nhật ký. Trình duyệt có thể khác nhau về hỗ trợ tùy chọn camera của `input[type=file]`.
- Trường **ghi chú** tối đa 2.000 ký tự đã có và tiếp tục hoạt động độc lập với ảnh.
- Vi phạm vẫn được tạo một lần theo `Idempotency-Key`. Ảnh được gửi từng tệp sau khi tạo bản ghi; ảnh trùng byte trong cùng bản ghi không được lưu hai lần. Nếu ảnh lỗi mạng, có thể thử lại hoặc thêm từ Nhật ký. **Không khẳng định giao dịch tạo vi phạm và upload ảnh là nguyên tử**.
- Ảnh chỉ được đọc sau khi đăng nhập và kiểm tra phạm vi lớp; việc thêm ảnh yêu cầu là quản trị hoặc người đã lập vi phạm, đúng lớp được cấp quyền.
- Server kiểm tra định dạng JPG/PNG/WEBP, kích thước tối đa 8 MB và 20 megapixel; chuyển ảnh sang JPEG để loại EXIF (bao gồm dữ liệu vị trí GPS nếu có). Ảnh không nằm trong URL tĩnh.
- Trong chế độ này, không hỗ trợ tạo bản ghi mới khi **hoàn toàn mất Internet**; cần bổ sung hàng đợi offline mã hóa và quy trình xung đột nếu nhà trường muốn dùng offline.

## Database & upgrade

Bản mới thêm bảng `violation_photos` với khóa ngoại đến `violations` và `users`, chỉ mục trên `violation_id` và ràng buộc `(violation_id, sha256)` không trùng. Migration `0002_violation_photos` hỗ trợ tạo mới hoặc nâng cấp database v0.6. Trước khi nâng cấp bản đang dùng thật **sao lưu và thử khôi phục**.

```bash
cd backend
python -m alembic upgrade head
```

## Triển khai để điện thoại dùng 4G/5G ở mọi nơi

Cần 1 máy chủ được nhà trường phê duyệt, dịch vụ PostgreSQL, tên miền HTTPS và chính sách truy cập phù hợp. Không cần mở máy tính cá nhân hay kết nối cùng Wi-Fi. Nếu trường chỉ cho phép VPN, mọi điện thoại phải cài VPN và được cấp quyền truy cập.

Docker Compose ở `deploy/docker-compose.yml` có 2 volume: `pg_data` (database) và `evidence_data` (tệp ảnh). Backend chạy bằng tài khoản không phải root và có thư mục `/service/private_evidence`. **Bắt buộc sao lưu đồng bộ cả 2 volume**: ảnh trong DB chỉ có đường dẫn và metadata, mất volume `evidence_data` thì không khôi phục được ảnh chỉ từ PostgreSQL.

Không đưa workbook học sinh, tệp ảnh hay cơ sở dữ liệu vào repository GitHub hay ZIP chuyển cho giáo viên; APK chỉ mang mã giao diện và cần cấu hình HTTPS của server trường trên màn hình đăng nhập.

## Thử API ảnh sau khi deploy

1. Đăng nhập tài khoản `admin` hoặc `recorder` có quyền với lớp thử nghiệm.
2. Tạo 1 vi phạm thử nghiệm, lấy ID được API trả về.
3. Gửi `POST /violations/{id}/photos` dạng `multipart/form-data` với trường `file` (JPG/PNG/WEBP).
4. Kiểm tra `/students/{student_code}` hoặc `/violations`: có `photo_count`, danh sách `photos`.
5. Gọi `GET /violations/{id}/photos/{photo_id}` với Bearer token; người không đăng nhập phải nhận 401 và người ngoài phạm vi lớp phải nhận 403.
6. Dùng tài khoản khác có quyền vào cùng lớp, kiểm tra ảnh và ghi chú; thử tải lên ảnh y hệt 2 lần để xác minh khử trùng.

## Tiêu chí an toàn trước khi đưa vào trường

- Nhà trường thông qua phương án quản lý và lưu trữ thông tin học sinh/ảnh, quy định thời hạn giữ và xử lý yêu cầu xóa theo pháp luật và nội quy.
- Có TLS/HTTPS, tài khoản cá nhân, phân quyền và sao lưu, kiểm thử khôi phục ảnh và DB.
- Kiểm thử Android thật: cấp quyền camera, chụp ảnh, chọn ảnh, mạng chập chờn, gửi lại, tải ảnh, mở trên nhiều tài khoản, chụp liên tiếp, khi số lượng người dùng tăng.
- Phát hành chính thức cần APK ký bằng khóa riêng của trường, lưu khóa ký an toàn và quản lý quy trình cập nhật. File `app-debug.apk` do workflow tạo ra chỉ là **bản thử nghiệm**.
