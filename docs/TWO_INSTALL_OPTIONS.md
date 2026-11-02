# THĐ Student Discipline – PWA và APK dùng chung dữ liệu

## Có gì trong phiên bản này?

**Một backend FastAPI/PostgreSQL** và hai kiểu giao diện:

- **PWA:** `https://TEN-MIEN-NOI-BO-DA-DUOC-PHE-DUYET/app/` (được chính backend phục vụ). Người dùng Android/iPhone mở liên kết qua trình duyệt và thêm vào màn hình chính. Không phải cài APK.
- **Android Flutter:** mã nguồn ở `mobile/`. Khi được build thành APK và cấu hình trỏ tới cùng **HTTPS API**, mọi thao tác nhập, sửa, tra cứu hoặc báo cáo sử dụng cùng dữ liệu. Không có dữ liệu thật đi kèm APK.

**Đồng bộ:** Backend ghi và đọc dữ liệu từ PostgreSQL. Cả PWA và Flutter tự tải lại các màn hình tổng quan/cảnh báo/báo cáo khoảng 30 giây một lần khi đang mở; tải lại thủ công ngay bằng nút làm mới. Một thao tác Lưu chỉ được thông báo thành công sau khi backend chấp nhận. **Chưa có WebSocket/push tức thời, chưa hỗ trợ nhập offline**.

## A. Thử PWA cục bộ ngay trên máy phát triển

Cài đặt Python 3.12+, vào `backend/`, cài dependencies và chạy migration:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_URL=sqlite:///./dev_only.db
python -m alembic upgrade head
python -m app.cli seed --year 2026-2027
python -m app.cli create-admin --username admin --display-name 'Quản trị viên'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Mở **http://127.0.0.1:8000/app/** để kiểm tra PWA. Đây là localhost chỉ dành cho môi trường phát triển; việc thêm biểu tượng PWA lên điện thoại từ xa cần **HTTPS, tên miền và mạng có thể truy cập máy chủ**.

## B. Triển khai chung cho giáo viên bằng PWA (cần sự phê duyệt của trường)

1. Triển khai `deploy/docker-compose.yml` trên **máy chủ đã được nhà trường phê duyệt**. Mật khẩu PostgreSQL, JWT bí mật khai báo ở `deploy/.env` (không commit). `docker compose --env-file .env up -d --build` từ thư mục `deploy`.
2. Chạy migration, seed và tạo admin bằng Docker CLI theo tài liệu `INSTALL_OPERATIONS.md`. Chỉ import file Excel gốc **trên server được trường phê duyệt**, không tải lên hosting công khai hoặc GitHub.
3. Trỏ tên miền trường và cấu hình TLS qua reverse proxy. `deploy/Caddyfile.example` là cấu hình tham khảo; chỉ đặt API sau mạng nội bộ / VPN khi chính sách yêu cầu. Chỉ public PWA nếu trường duyệt và có kiểm soát truy cập thích hợp.
4. Mở `https://TEN-MIEN-DA-DUOC-PHE-DUYET/app/`. Trên Android: Chrome → menu → Cài ứng dụng hoặc Thêm vào màn hình chính. iPhone: Safari → Chia sẻ → Thêm vào Màn hình chính.
5. Tạo tài khoản riêng cho từng giáo viên và giới hạn quyền xem lớp. Mỗi giáo viên dùng tài khoản của mình, không chia sẻ tài khoản quản trị.

**Không có link thực tế trong gói này** vì chưa được cấp tên miền, máy chủ và chứng chỉ TLS.

## C. Đóng gói bản Android APK

**Không có APK build sẵn**, vì môi trường tạo mã nguồn không có Flutter/Android SDK. Muốn tạo APK thử nghiệm (debug-signed) cần **Flutter, Android SDK** hoặc chạy GitHub Actions trên *repository riêng tư chỉ chứa mã nguồn, không có dữ liệu học sinh*. Bản mới cho phép cấu hình URL HTTPS trên màn hình đăng nhập nên không cần biết tên miền khi build.

Trên Windows PowerShell tại thư mục gốc dự án:

```powershell
.\scripts\build_apk.ps1
```

Trên Linux/macOS:

```bash
./scripts/build_apk.sh
```

APK thành công sẽ xuất hiện ở `mobile/build/app/outputs/flutter-apk/app-debug.apk`. Đây là **bản cài thử**, không phải bản phát hành sản xuất. Muốn phát hành cần cấu hình khóa ký chính thức, cập nhật và quản lý thiết bị; **không được dùng bản debug lâu dài cho dữ liệu thật**.

### Không muốn tự cài Flutter trên máy

Thư mục `.github/workflows/android-apk.yml` có cấu hình tự build APK bằng GitHub Actions. Đặt mã nguồn vào **repo riêng tư**, không upload danh sách học sinh hay `.env`. Có thể bỏ trống `THD_API_BASE_URL`: ứng dụng sẽ hỏi địa chỉ HTTPS của máy chủ ở màn hình đăng nhập. Chạy workflow `Build THD Android pilot APK` và lấy file từ mục Artifacts. Chưa chạy workflow này trong môi trường hiện tại. Kết quả phụ thuộc vào build CI thực tế.

## Những giới hạn khi chưa triển khai máy chủ

- Cả PWA và APK đều **không thể truy cập hay đồng bộ dữ liệu** nếu chưa có backend PostgreSQL có HTTPS mà các máy cùng truy cập được.
- PWA và Flutter **không phải** hai hệ thống độc lập: đây là thiết kế có chủ ý để thống nhất dữ liệu.
- PWA không lưu token hoặc dữ liệu học sinh vào localStorage/IndexedDB; reload trang sẽ yêu cầu đăng nhập lại. Service worker chỉ cache các tệp giao diện công khai; không có dữ liệu vi phạm hay học sinh.
- Không được diễn giải "đã có mã nguồn" thành "đã chạy trên điện thoại thật". Phải kiểm thử HTTPS, máy chủ, tải nhiều người và APK trước khi phát hành.

## Kiểm thử đồng bộ giữa hai bản trên hệ thống đã triển khai

1. Đăng nhập PWA bằng tài khoản A có quyền lớp thử nghiệm.
2. Cài APK build với `API_BASE_URL` cùng tên miền, đăng nhập tài khoản B có quyền xem lớp đó.
3. Trên PWA, nhập 1 lượt vi phạm cho học sinh thử nghiệm có thật theo quy trình được nhà trường duyệt; chờ backend xác nhận.
4. Trên APK, mở lại Dashboard/Tra cứu hoặc nhấn Làm mới: số liệu tăng 1.
5. Trên APK, chỉnh sửa/hủy bản ghi theo đúng phân quyền; trên PWA làm mới và xác minh số liệu tự tính lại.
6. Thử nhập sai lớp và thử hai giáo viên nhập song song, đối chiếu nhật ký, idempotency và audit.

Đây là **kịch bản kiểm thử cần thực hiện trên hạ tầng thật**, chưa phải kết quả chạy thiết bị thật.
