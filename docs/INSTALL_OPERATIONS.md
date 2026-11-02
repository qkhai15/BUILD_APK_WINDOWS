# Cài đặt, vận hành, sao lưu, phục hồi

## 1. Yêu cầu môi trường sản xuất

- Máy Linux hoặc VM do trường quản lý, Docker Engine + Docker Compose plugin, ổ SSD có sao lưu ngoài máy.
- Truy cập chỉ qua VPN nội bộ/Wi-Fi trường đã kiểm soát; HTTPS hợp lệ trên domain được trường quản lý; máy điện thoại phải tin cậy CA của nhà trường.
- Quản lý bí mật trong `.env` với quyền `0600`, khóa bí mật ngẫu nhiên, có nhật ký quyền truy cập và nhân sự phụ trách.
- Cổng PostgreSQL 5432 **không được publish**. Compose chỉ publish API qua `127.0.0.1:8000` để reverse proxy TLS dùng cùng máy chủ.

## 2. Khởi chạy Docker Compose

```bash
cd deploy
cp .env.example .env
python3 - <<'PY'
import secrets
print('POSTGRES_PASSWORD=' + secrets.token_hex(24))
print('JWT_SECRET=' + secrets.token_hex(32))
PY
# Chép hai chuỗi được sinh vào deploy/.env (không đưa lên Git)
chmod 600 .env
docker compose up -d --build
docker compose run --rm api alembic upgrade head
docker compose exec api python -m app.cli seed --year 2026-2027
docker compose exec -it api python -m app.cli create-admin --username admin --display-name 'Quản trị viên'
```

Không dùng các giá trị `REPLACE_WITH...` ở `.env.example`. Chứng chỉ TLS và domain nội bộ phải được cấu hình bên reverse proxy, ví dụ `Caddyfile.example`. API chưa có TLS tự thân, **không mở cổng 8000 ra Internet hoặc mạng công cộng**. Trong lúc thử nghiệm máy đơn, có thể truy cập `http://127.0.0.1:8000/docs` từ chính máy đó.

**Chú ý:** `DATABASE_URL` chứa mật khẩu SQL; để tránh lỗi URL encoding, dùng mật khẩu `secrets.token_hex` (chỉ chữ/số 0–9a–f), không dùng ký tự URL đặc biệt.

## 3. Import dữ liệu gốc theo quy trình an toàn

```bash
mkdir -p private_data
chmod 700 private_data
# Sao chép file Excel gốc từ nơi lưu được phép vào deploy/private_data/roster.xlsx
# KHÔNG copy file vào kho mã nguồn và không tải lên dịch vụ đám mây ngoài trường

docker compose run --rm -v "$PWD/private_data:/private:ro" api \
  python -m app.excel_import /private/roster.xlsx --validate-only

docker compose run --rm -v "$PWD/private_data:/private:ro" api \
  python -m app.excel_import /private/roster.xlsx
```

Kết quả với Excel cung cấp: 2.260 học sinh, 48 lớp, 0 bản ghi vi phạm, 0 mã trùng/thiếu trường. Dữ liệu import là giao dịch toàn bộ: nếu xảy ra sai khác ở hồ sơ đã có, import dừng và rollback; **không dùng `--update-existing` khi chưa rà soát biến động học sinh**. Import lại workbook nguyên trạng trả 0 thêm, 2.260 không thay đổi.

Kiểm tra lại sau import (chỉ chạy trên máy chủ có quyền):

```bash
docker compose exec db psql -U thd_app -d thd -c 'SELECT COUNT(*) FROM students;'
docker compose exec db psql -U thd_app -d thd -c 'SELECT COUNT(*) FROM classes;'
docker compose exec db psql -U thd_app -d thd -c 'SELECT COUNT(*) FROM violations;'
```

## 4. Flutter Android và iOS

Môi trường hiện tại **không có Flutter SDK / Android SDK**, vì vậy chưa thể cấp APK trong bản bàn giao này. `mobile/` chứa mã nguồn Flutter và cấu hình dependency; tạo phần platform chuẩn bằng Flutter CLI trên máy có SDK:

```bash
cd mobile
flutter create --platforms=android,ios --project-name thd_student_discipline .
flutter pub get
flutter analyze
flutter run --dart-define=API_BASE_URL=https://thd.school.example
flutter build apk --release --dart-define=API_BASE_URL=https://thd.school.example
```

Thay `https://thd.school.example` bằng domain nội bộ có TLS hợp lệ. File sau khi build thành công: `mobile/build/app/outputs/flutter-apk/app-release.apk`. **Không phát hành nếu `flutter analyze`, đăng nhập, ghi vi phạm, phân quyền và export chưa được kiểm thử trên điện thoại thật.** Android trong môi trường phát triển có thể dùng HTTP debug qua adb/emulator nhưng bản release từ chối HTTP.

iOS cần **Mac có Xcode**, tài khoản và chứng chỉ ký ứng dụng, thiết bị đã được cho phép; dùng `flutter build ipa --release --dart-define=API_BASE_URL=https://...` sau khi thiết lập signing; không thể cài iOS theo cách phân phối APK Android.

## 5. Sao lưu

Khuyến nghị ít nhất một bản backup mã hóa mỗi ngày, kiểm tra thành công và giữ ở vị trí tách biệt máy chủ. **Script gợi ý**:

```bash
cd deploy
mkdir -p backups
chmod 700 backups
set -o pipefail
docker compose exec -T db pg_dump -U thd_app -d thd -Fc > "backups/thd_$(date +%F_%H%M).dump"
sha256sum backups/*.dump > backups/SHA256SUMS.txt
```

Tệp dump chứa toàn bộ dữ liệu học sinh, phải giới hạn người truy cập và mã hóa ở tầng lưu trữ/backup. Không đưa backup, JSON API, log có PII hoặc báo cáo lên email, Git, ổ đĩa dùng chung nếu chưa được phê duyệt. Đặt thời gian lưu giữ và quy trình xóa theo quy định của trường.

## 6. Khôi phục có kiểm chứng

Chỉ khôi phục khi đã kiểm tra bản backup đúng thời điểm, có sự đồng ý của quản trị và có một database **mới, rỗng, cách ly**. Không restore đè trực tiếp lên DB đang vận hành.

```bash
# Ví dụ trong môi trường khôi phục riêng, sau khi tạo DB rỗng:
cat /secure/backup/thd_YYYY-MM-DD_HHMM.dump | \
  docker compose exec -T db pg_restore -U thd_app -d thd --no-owner --no-acl
# Sau restore: kiểm tra SELECT COUNT(*), thử login, xem báo cáo, xác minh audit.
```

Quy trình thực tế cần chạy diễn tập trước; chưa thực hiện phục hồi trên server trường.

## 7. Vận hành và lỗi thường gặp

- 401: token hết hạn/tài khoản bị khóa, đăng nhập lại; 403: không được phân công lớp/quyền.
- 409: gửi lại cùng khóa nhưng nội dung đã thay đổi; không đổi khóa rồi gửi bừa vì có thể ghi trùng. Kiểm tra nhật ký.
- 422: dữ liệu thiếu hoặc cấu hình ngưỡng không hợp lệ.
- Mạng yếu: dừng thao tác và tải lại danh sách; app giữ nguyên `Idempotency-Key` khi thử lại một lần lưu chưa biết kết quả.
- Thay đổi cấu hình cảnh báo: phải ghi biên bản, kiểm tra tác động và cân nhắc lưu bản báo cáo trước/sau khi thay đổi.
- Chỉ số dashboard là truy vấn trực tiếp; làm mới khi cần xem số liệu người khác vừa nhập. Không có websocket.
