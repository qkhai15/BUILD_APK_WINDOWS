THĐ STUDENT DISCIPLINE v0.7 – HƯỚNG DẪN LẤY FILE APK
====================================================

1. BẢN NÀY ĐÃ CÓ MÃ NGUỒN ẢNH MINH CHỨNG
   - Chụp ảnh bằng camera / chọn ảnh trong máy (tối đa 3 ảnh, tối đa 8 MB/ảnh).
   - Ghi chú khi nhập vi phạm; xem lại ảnh đã lưu trong hồ sơ và nhật ký.
   - Máy chủ lưu ảnh trong thư mục PRIVATE, chỉ truy cập sau khi đăng nhập đúng quyền.
   - Các máy đồng bộ qua Internet bằng MỘT backend chung.
   - Không nhập và đồng bộ được khi hoàn toàn không có Internet.

2. VÌ SAO FILE ĐANG LÀ ZIP MÃ NGUỒN, CHƯA PHẢI APK?
   Môi trường làm project không có Flutter SDK và Android SDK, cũng không tải
   được bộ công cụ do kết nối mạng bị chặn. Vì vậy CHƯA tạo được APK thật.
   TUYỆT ĐỐI không đổi tên .zip thành .apk.

3. CÁCH TẠO FILE APK KHI MÁY CÓ FLUTTER + ANDROID SDK (WINDOWS)
   Mở PowerShell tại thư mục THD_Student_Discipline, chạy:
      .\scripts\build_apk.ps1
   Hoặc nhấp BUILD_APK_WINDOWS.cmd (kiểm tra Flutter trước khi chạy).
   Nếu chạy thành công, file cài thử ở:
      mobile\build\app\outputs\flutter-apk\app-debug.apk
   Đây là bản ký debug để kiểm tra, chưa phải bản phát hành production.

4. CÁCH TẠO APK KHÔNG CẦN CÀI FLUTTER TRÊN MÁY CỦA BẠN
   - Tạo repository GitHub RIÊNG TƯ (Private) chỉ gồm mã nguồn trong ZIP này.
   - Không tải file Excel học sinh, .env, mật khẩu hay ảnh vi phạm lên GitHub.
   - Mở tab Actions, chọn workflow: Build THD Android pilot APK.
   - Chọn Run workflow, đợi build hoàn tất rồi tải artifact.
   - Giải nén artifact và lấy app-debug.apk, chuyển file qua điện thoại Android để cài.
   Lưu ý: workflow này mới là cấu hình build; chưa chạy xác minh trên GitHub.

5. QUAN TRỌNG – APK KHÔNG PHẢI MÁY CHỦ ĐỒNG BỘ
   - Để giáo viên dùng ở BẤT CỨ ĐÂU, cần backend PostgreSQL + thư mục ảnh
     chạy trên máy chủ HTTPS với tên miền / VPN được nhà trường phê duyệt.
   - Không cần chung Wi-Fi, chỉ cần mỗi máy có Internet (4G/5G/Wi-Fi).
   - Vào ứng dụng → Cấu hình máy chủ → nhập URL HTTPS của trường → đăng nhập.
   - Ảnh và ghi chú chỉ được báo hoàn tất khi máy chủ phản hồi thành công.
   - Máy chủ phải sao lưu CẢ PostgreSQL và volume evidence_data chứa ảnh.
   - Không dùng localhost HTTP hoặc dữ liệu học sinh thật để thử nghiệm từ xa.

6. KẾT QUẢ KIỂM THỬ
   - Backend/PWA: 18 passed, 1 skipped, có kiểm tra quyền ảnh và dedup.
   - Migration DB mới và nâng cấp từ bản cũ: đã chạy thử bằng SQLite.
   - JavaScript PWA: node --check đạt.
   - Flutter/Android: CHƯA build, CHƯA kiểm thử trên điện thoại thật.

Xem thêm: docs/PHOTO_EVIDENCE_DEPLOY.md
