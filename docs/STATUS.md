# Trạng thái bàn giao theo giai đoạn

| Giai đoạn | Hạng mục | Trạng thái có căn cứ |
|---|---|---|
| 1 | Kiểm kê 58 sheet, công thức, dữ liệu, quy tắc | Đã kiểm tra trực tiếp XML workbook (không thay đổi file gốc) |
| 2 | ERD, vai trò, REST, quy tắc nghiệp vụ | Có mã nguồn + tài liệu |
| 3 | Backend FastAPI, migration và API thật | Đã chạy các bài pytest với SQLite; chưa kiểm thử PostgreSQL/Docker trên máy chủ trường |
| 4 | Giao diện Flutter gọi REST thật | Đã viết mã nguồn; chưa chạy Flutter analyze, chưa chạy emulator hoặc điện thoại |
| 5 | Import Excel thật trong kiểm thử tạm | Đã import thực 2.260/48/0 vào DB tạm, import lại không trùng; file DB tạm đã xóa |
| 6 | Quy tắc cảnh báo, phân quyền, export, chống gửi trùng | Đã có kiểm thử Python. Chưa có tải thực 48 lớp/ngày hoặc kiểm thử mạng chập chờn trên thiết bị |
| 7 | Docker Compose, hướng dẫn, script build | Đã viết; chưa chạy Docker và chưa có APK/iOS binary |

## Không được coi là đã hoàn thiện sản phẩm triển khai

- Ứng dụng chưa được biên dịch/kiểm tra trên Android hoặc iOS.
- Backend chưa được triển khai trên PostgreSQL thực hoặc mạng nội bộ trường.
- Chưa được rà soát bảo mật bởi đội CNTT của trường; chưa thử restore từ backup thật.
- Chưa có cơ chế đẩy thông báo/thay đổi thời gian thực: màn hình cập nhật khi mở hoặc khi nhấn tải lại.
- **Không hỗ trợ lưu offline** và không có hàng đợi đồng bộ.
- Không có bằng chứng nhà trường đã chấp thuận phân quyền, quy trình sửa/hủy và chính sách lưu giữ dữ liệu.

## Hướng ưu tiên triển khai tiếp

1. Máy kiểm thử có Flutter/Dart, Android SDK: chạy `flutter create`, `flutter analyze`, kiểm thử trên máy Android thật; sửa cảnh báo biên dịch.
2. Máy chủ đã được phê duyệt: triển khai Compose PostgreSQL + TLS/VPN; chạy migration và import đúng file gốc.
3. Thử nghiệm nhóm nhỏ theo lớp/role với dữ liệu thật trong mạng nội bộ, sau khi phê duyệt quyền truy cập.
4. Kiểm thử đối chiếu báo cáo, backup/restore và kiểm thử tải; chỉ sau đó phát hành APK nội bộ.

## Bản cập nhật v0.3 – PWA cùng API với Flutter

- Đã bổ sung `backend/app/pwa/`: PWA có login, dashboard, nhập vi phạm, tìm HS, hồ sơ, nhật ký, cảnh báo, báo cáo PDF/Excel, quản trị tạo tài khoản cơ bản. API dữ liệu giữ cùng backend như Flutter.
- PWA có nút tải lại và polling 30 giây cho các màn hình chỉ đọc. Flutter có polling 30 giây cho các màn hình tổng quan/cảnh báo/báo cáo; **không có cơ chế đồng bộ offline**.
- Đã thêm smoke tests cho endpoint PWA, CSP, API cần JWT, tạo một vi phạm ở client A và xem số liệu từ client B.
- Chưa kiểm thử Flutter qua `flutter analyze` hoặc build APK bởi môi trường không cài Flutter/Android SDK. Cấu hình GitHub Actions chưa được chạy.
- Chưa triển khai lên tên miền/HTTPS thực; không có đường link PWA sử dụng công khai. Không có dữ liệu học sinh thật trong ZIP.

## Bổ sung nhận diện thương hiệu (bản mã nguồn 0.4)

- Đã nối hai vị trí logo bên trong Flutter (màn hình đăng nhập, thanh tiêu đề, dashboard) và PWA (đăng nhập, sidebar, thanh tiêu đề mobile/desktop).
- Đã thêm trình cài ảnh gốc cho ba ảnh và cấu hình tạo launcher icon Android + PWA (gồm Apple touch icon) từ **ảnh 3**.
- **Ba file ảnh gốc người dùng gửi trong tin nhắn chưa có bản nhị phân trong thư mục dự án**, nên logo thật chưa được nhúng. Hiện phần nhận diện dùng fallback; đọc `docs/THIET_LAP_3_LOGO.md`.
- Chưa build APK/đưa PWA lên tên miền trường; chưa kiểm tra giao diện với ba ảnh gốc trên điện thoại.


## Cập nhật 2026-11-02 – v0.6

- Đã có chính xác 3 logo thật từ `Logo.zip`. Đã nhúng vào Flutter và PWA và tạo các kích cỡ icon.
- Đã thêm cấu hình địa chỉ máy chủ HTTPS ngay trong bản Flutter, tránh phụ thuộc build-time URL. **Chưa kiểm tra biên dịch Flutter vì SDK không có trong môi trường này.**
- Đã cập nhật script và GitHub Actions cho APK cài thử dạng debug-signed có thể nhập URL sau khi cài.
- Không có APK biên dịch, không có PWA URL công khai và chưa vận hành với PostgreSQL production. Không phát hành chính thức trước khi có kiểm thử thực tế.
