# Cài đúng ba logo cho PWA và Android APK

## Quy ước chính xác

- **Ảnh 1:** hiển thị **bên trong ứng dụng** (đăng nhập, thanh điều hướng, trang chủ) trên cả PWA và Android.
- **Ảnh 2:** hiển thị **bên trong ứng dụng** song song ảnh 1, giữ nguyên tỷ lệ ảnh gốc.
- **Ảnh 3:** chỉ dùng làm **biểu tượng bên ngoài ứng dụng**: màn hình chính Android (launcher icon), biểu tượng PWA trên Android và iPhone. Không đặt ảnh 3 vào màn hình nhập liệu.

Mỗi ảnh được chuẩn hóa kích cỡ PNG và **không thay đổi nội dung, hình khối hay màu sắc của logo**. Với biểu tượng điện thoại, công cụ thêm lề an toàn để hình không bị cắt khi điện thoại dùng icon tròn.

## Bước 1 – Đưa 3 ảnh thật vào máy

Ba ảnh gốc đã được đưa vào bộ source ở định dạng PNG. **Bản v0.6 đã nhận `Logo.zip` và đã gắn cả ba ảnh gốc vào dự án.** Không sử dụng logo tự tạo thay thế.

## Bước 2 – Cài vào project bằng một lệnh

Cài công cụ tạo ảnh:

```bash
python -m pip install Pillow
```

Chỉ khi cần thay logo trong tương lai: chạy tại thư mục gốc project (sửa đường dẫn 3 ảnh theo file mới):

```bash
python scripts/apply_branding.py \
  --logo-1 /duong-dan/logo1.png \
  --logo-2 /duong-dan/logo2.png \
  --app-icon /duong-dan/logo3.png
```

Lệnh này tạo:

```text
mobile/assets/branding/logo_1.png               # logo 1 bên trong Flutter
mobile/assets/branding/logo_2.png               # logo 2 bên trong Flutter
mobile/assets/branding/app_icon.png             # icon launcher (không vào UI)
mobile/assets/branding/app_icon_foreground.png  # Android adaptive icon
backend/app/pwa/branding/logo-1.png             # logo 1 bên trong PWA
backend/app/pwa/branding/logo-2.png             # logo 2 bên trong PWA
backend/app/pwa/icons/icon-192.png              # icon PWA Android
backend/app/pwa/icons/icon-512.png              # icon PWA Android
backend/app/pwa/icons/apple-touch-icon.png      # icon PWA iPhone
```

Nếu thiếu một trong ba file, script sẽ **không âm thầm dùng hình giả**.

## Bước 3 – Cập nhật ứng dụng

- **PWA:** Triển khai lại backend/website lên máy chủ chung, mở lại trang; có thể cần xóa biểu tượng cũ trên màn hình chính rồi thêm lại vì hệ điều hành cache icon.
- **Android:** Sau khi đã chuẩn bị Flutter/Android SDK, chạy `scripts/build_apk.sh https://TEN-MIEN-CUA-TRUONG` (hoặc `.ps1` trên Windows). Script tự chạy `dart run flutter_launcher_icons` khi có `app_icon.png`, tạo icon dựa theo ảnh 3.
- Các file ảnh thật đã được nhúng. Bản APK thực tế vẫn chỉ có icon mới sau khi đã build bằng Android SDK/Flutter; hiện chưa có APK đã biên dịch.

## Bảo mật

Chỉ gửi 3 file logo (không kèm Excel học sinh). Không upload dữ liệu riêng của trường lên kho mã nguồn công khai. Sửa logo không ảnh hưởng database và quy tắc cảnh báo.
