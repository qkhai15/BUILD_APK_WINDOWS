# THĐ Student Discipline — mã nguồn phát triển nội bộ

**Trường THPT Trần Hưng Đạo – Thanh Xuân · Năm học 2026–2027**

Đây là **bộ mã nguồn có backend đã chạy kiểm thử**, không phải dịch vụ đã được triển khai tại trường. Flutter đã có các màn hình gọi API thật, **chưa build APK và chưa kiểm thử trên điện thoại vật lý** vì môi trường phát triển hiện không có Flutter SDK, Android SDK hoặc Docker daemon. Xem `docs/STATUS.md` trước khi vận hành thật.

## Thành phần

| Đường dẫn | Chức năng |
|---|---|
| `backend/app/` | FastAPI, SQLAlchemy, JWT, Argon2, audit, báo cáo PDF/XLSX, import Excel |
| `backend/alembic/` | Database migration đầu tiên |
| `backend/tests/` | Kiểm thử nghiệp vụ, API, nhập dữ liệu, export |
| `mobile/lib/` | Flutter Material 3: đăng nhập, dashboard, nhập vi phạm, tra cứu, cảnh báo, báo cáo, quản trị |
| `mobile/pubspec.yaml` | Phụ thuộc Flutter, không chứa dữ liệu mẫu |
| `deploy/docker-compose.yml` | PostgreSQL và API trên máy chủ riêng |
| `docs/WORKBOOK_ANALYSIS.md` | Kiểm kê và đối chiếu logic Excel |
| `docs/INSTALL_OPERATIONS.md` | Cài đặt, khôi phục, build APK/iOS |
| `docs/SECURITY_ACCEPTANCE.md` | Kiểm thử, bảo mật và điều kiện nghiệm thu |

**Không có dữ liệu học sinh thật, mật khẩu, khóa hoặc tệp Excel gốc trong mã nguồn này.** Mọi dữ liệu được chuyển từ file gốc bằng `python -m app.excel_import ...` **trên thiết bị/máy chủ được trường phê duyệt**. Nhật ký gốc trống: không phát sinh bản ghi giả trong cơ sở dữ liệu.

## Khởi chạy backend nhanh (trên máy phát triển, chưa dùng cho sản xuất)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export DATABASE_URL=sqlite:///./dev_only.db
export JWT_SECRET="$(python -c 'import secrets;print(secrets.token_hex(32))')"
alembic upgrade head
python -m app.cli seed --year 2026-2027
python -m app.cli create-admin --username admin --display-name 'Quản trị viên'
python -m app.excel_import '/secure/path/PHÔI NHẬP LIỆU BẢN FULL MỚI 2026.xlsx' --validate-only
python -m app.excel_import '/secure/path/PHÔI NHẬP LIỆU BẢN FULL MỚI 2026.xlsx'
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Lưu ý:** `export` chỉ áp dụng Linux/macOS; Windows PowerShell dùng `$env:JWT_SECRET=...`, `$env:DATABASE_URL=...`. Tài khoản chỉ được tạo bằng CLI với mật khẩu nhập qua bàn phím. Dùng SQLite trong hướng dẫn trên **chỉ để phát triển**; sản xuất bắt buộc PostgreSQL qua Docker Compose, TLS và phân quyền mạng.

Tài liệu API: `http://127.0.0.1:8000/docs` trên máy phát triển. Tất cả endpoint dữ liệu bắt buộc token, riêng `/auth/login` và `/healthz` không yêu cầu đăng nhập. Kiểm thử bằng `PYTHONPATH=. pytest -q` trong thư mục `backend`.

## Luồng dữ liệu

```text
Flutter Android / iOS
        │ HTTPS + JWT + idempotency key
        ▼
    API FastAPI ───► kiểm tra vai trò + lớp được phân công
        │                  │
        └──────────────────┴────► PostgreSQL
                                          │
                                          ├─ Students / Classes / SchoolYears
                                          ├─ Violations (happened_on, recorded_at)
                                          ├─ UserClassAssignments / Roles / Users
                                          ├─ WarningRules / ViolationTypes
                                          └─ AuditLogs / ImportJobs
                                   ▲
          Excel gốc ──► Script import tại máy chủ được phê duyệt
```

**Không hỗ trợ offline.** Khi mất mạng, màn hình báo lỗi; không tự động lưu dữ liệu chưa xác nhận hoặc tuyên bố đồng bộ offline. Các màn hình lấy dữ liệu thật từ backend, không có dữ liệu giả trong bản phát hành.

## Các vấn đề cần xác nhận với nhà trường

1. Ai được quyền sửa/hủy vi phạm ngoài người nhập và quản trị? Hiện áp dụng **admin hoặc đúng người đã tạo**, và lý do hủy là bắt buộc.
2. GVCN chỉ xem lớp được phân công; giáo viên trực nhập lớp được phân công; ban giám hiệu đọc toàn trường. Chính sách này là **đề xuất cấp quyền mới**, không phải quy định xác định được từ Excel.
3. Dữ liệu báo cáo có được phép giữ bản PDF trên thiết bị trong bao lâu? Hiện mobile lưu báo cáo vào thư mục tạm riêng của ứng dụng.
4. Có cần chụp ảnh minh chứng, quy trình phê duyệt/kháng nghị hoặc đồng bộ offline hay không? Chưa có trong workbook và chưa triển khai.
5. Tên miền nội bộ, cấp chứng chỉ TLS và thiết bị cài APK do nhà trường quyết định.

Đọc `docs/STATUS.md` để biết **đã kiểm thử** và **chưa kiểm thử** trước khi triển khai thật.

## Hai cách cài cho giáo viên (bản thử nghiệm đa nền tảng)

- **PWA dùng đường link:** Backend giờ cũng phục vụ giao diện tại `/app/`, có manifest và service worker lưu **chỉ giao diện tĩnh**. PWA hỗ trợ Android và iPhone khi có HTTPS và server được phê duyệt.
- **Android APK:** Mã nguồn Flutter dùng chung API; scripts `scripts/build_apk.ps1`, `scripts/build_apk.sh` và `.github/workflows/android-apk.yml` chuẩn bị/build APK khi có Flutter/Android SDK hoặc CI.

Hướng dẫn chi tiết và giới hạn nghiệm thu: `docs/TWO_INSTALL_OPTIONS.md`. **APK chưa được build**, PWA chưa được đặt lên máy chủ công khai. Hai bản đều dùng PostgreSQL để đồng bộ, không có dữ liệu thật trong kho mã nguồn.

## Nhận diện thương hiệu bằng ba logo (bản mã nguồn 0.4)

Đã **nhúng ba logo thật từ `Logo.zip`**: ảnh 1 + 2 nằm trong PWA/Flutter, ảnh 3 dùng làm biểu tượng ngoài màn hình điện thoại (PWA và Android). Các file PNG cần thiết đã có sẵn trong `mobile/assets/branding/` và `backend/app/pwa/`. Xem `docs/THIET_LAP_3_LOGO.md`.

Bản này vẫn **chưa có APK biên dịch** hay URL máy chủ đã chạy. Kết quả kiểm thử Python/PWA không đồng nghĩa đã kiểm thử giao diện trên điện thoại.


## Bản v0.6 – nhận diện hoàn chỉnh và một APK dùng chung

- **Đã nhúng 3 logo thật** vào mã nguồn PWA + Flutter.
- Flutter có mục **Cấu hình máy chủ** ngay trên màn hình đăng nhập để nhập URL HTTPS do trường cấp. Vì vậy có thể tạo một APK cài thử duy nhất, không buộc gắn cứng tên miền vào lúc build. Token đăng nhập cũ sẽ bị xóa khi đổi URL.
- `scripts/build_apk.sh` và `.ps1` nhận địa chỉ HTTPS *tùy chọn*; GitHub Actions có thể build **debug-signed pilot APK** dù chưa có URL, nhưng người dùng phải nhập URL trước khi đăng nhập.
- **Chưa có APK thật:** môi trường hiện tại thiếu Flutter và Android SDK, không thể chạy build hoặc kiểm thử trên Android. **Chưa có đường link PWA thực tế:** trường cần duyệt hạ tầng HTTPS và máy chủ tập trung.
- Kết quả kiểm thử hiện tại chỉ chứng minh backend/PWA trên môi trường kiểm thử; chưa chứng minh ứng dụng Flutter chạy trên thiết bị thật.

**Xem ngay:** `docs/BAN_GIAO_NGAN_GON.md` để biết cần làm gì tiếp theo.

## Phiên bản 0.7: lưu ảnh minh chứng

Đã thêm mã nguồn Flutter/PWA để chụp/chọn ảnh minh chứng, ghi chú và xem ảnh trong lịch sử; thêm API kiểm soát truy cập ảnh, PostgreSQL migration và Docker volume riêng cho ảnh. Xem **README_CAI_APK_TRUOC.txt** và `docs/PHOTO_EVIDENCE_DEPLOY.md`.

**Chưa có APK đã build hoặc dịch vụ HTTPS triển khai trong gói mã nguồn.** Những phần này cần công cụ Flutter/Android SDK và máy chủ được trường cho phép. Không dùng tên miền giả hoặc kiểm thử trên dữ liệu thật khi chưa bảo đảm an toàn.
