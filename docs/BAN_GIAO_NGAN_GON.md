# THĐ Student Discipline — Bàn giao mã nguồn v0.6

## Tệp có trong gói

1. **PWA có giao diện và API thật**: `backend/app/pwa/`; điện thoại Android/iPhone truy cập qua URL HTTPS của nhà trường rồi thêm vào màn hình chính.
2. **Flutter Android source**: `mobile/lib/`; có trang đăng nhập, nhập vi phạm, tìm kiếm, cảnh báo, báo cáo, và cấu hình máy chủ trực tiếp trên điện thoại.
3. **Ba logo gốc từ Logo.zip**: logo 1 và 2 hiển thị trong app; logo 3 làm icon bên ngoài app, các tệp PNG đã có sẵn.
4. **Backend + DB**: FastAPI, PostgreSQL, migration, phân quyền, audit, import Excel, xuất báo cáo, API cho PWA và Flutter.
5. **Triển khai + build**: `deploy/docker-compose.yml`, `.github/workflows/android-apk.yml`, `scripts/build_apk.sh`, `scripts/build_apk.ps1`.
6. **Kiểm thử**: `backend/tests/`; chạy `cd backend && PYTHONPATH=. pytest -q` trên Linux/macOS hoặc `python -m pytest -q` khi đã cài `requirements-dev.txt`.

## Phải làm trước khi giáo viên dùng trên điện thoại

**Bước A — Máy chủ chung:** Bộ phận CNTT nhà trường xác nhận máy chủ riêng hoặc nhà cung cấp có hợp đồng, bật HTTPS và PostgreSQL. Triển khai Docker Compose theo `docs/INSTALL_OPERATIONS.md`. Tạo tài khoản quản trị bằng CLI, kiểm tra phân quyền. Chỉ import dữ liệu học sinh thật trên máy chủ được duyệt; KHÔNG đưa file Excel thật lên GitHub, hosting công khai hoặc ZIP phát cho giáo viên.

**Bước B — PWA:** Mở `https://TEN-MIEN-TRUONG/app/` trên điện thoại. Chọn 'Thêm vào màn hình chính'. Tất cả dùng chung backend. Không có URL sử dụng thật cho đến khi Bước A được triển khai.

**Bước C — APK:** Chạy workflow `Build THD Android pilot APK` trong GitHub Actions ở **repo riêng tư chỉ có mã nguồn**, hoặc trên máy đã cài Flutter/Android SDK chạy `scripts/build_apk.ps1` (Windows) hay `./scripts/build_apk.sh` (Linux/macOS). Nhận `app-debug.apk`. Sau khi cài, mở màn hình đăng nhập, bấm `Cấu hình máy chủ`, nhập HTTPS URL từ Bước A, rồi đăng nhập. APK build ở đây chỉ phù hợp để kiểm thử nội bộ; bản phát hành lâu dài phải có ký chính thức và quy trình cập nhật.

## Giới hạn đã xác nhận

- Hiện **chưa có file APK đã biên dịch** vì máy thực thi không có Flutter SDK/Android SDK, và không tải trực tiếp được các bộ công cụ.
- Hiện **chưa có link PWA hoạt động trên Internet** vì chưa có máy chủ, tên miền HTTPS và quyền triển khai từ nhà trường.
- Các máy chỉ tự đồng bộ khi dùng cùng một backend và có kết nối tới backend. Dữ liệu không được lưu offline để nhập tiếp khi mất mạng.
- Chưa chạy thử trên điện thoại Android thật hoặc xác nhận phần Flutter không có lỗi biên dịch; phải kiểm tra trước khi triển khai thật.
- Không được hiểu bản mã nguồn là dịch vụ đã triển khai hay APK sẵn sàng cài.

## Kết quả đã kiểm chứng

- `pytest -q` backend/PWA: **15 passed, 1 skipped** (môi trường test hiện tại).
- Đã kiểm tra tài sản logo nằm đúng đường dẫn PWA/Flutter.
- Đã kiểm tra cú pháp JavaScript của PWA với `node --check`.

**Câu hỏi duy nhất cần chốt trước khi triển khai online:** Ai/đơn vị nào quản lý server HTTPS và PostgreSQL được nhà trường phê duyệt? Không thể đồng bộ dữ liệu giữa các máy mà thiếu máy chủ chung.
