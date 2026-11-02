# Tài liệu API REST – bản triển khai ban đầu

Sau khi chạy backend, giao diện OpenAPI nội bộ: `/docs`; định dạng JSON OpenAPI: `/openapi.json`.

## Authentication

`POST /auth/login` nhận `{"username":"<tài khoản>","password":"<mật khẩu>"}`. Các API còn lại sử dụng header `Authorization: Bearer <access_token>`. `GET /auth/me` kiểm tra quyền và lớp được phân công.

## Danh sách đường dẫn

| Phương thức | Path | Phân quyền |
|---|---|---|
| GET | `/school-years`, `/classes`, `/violation-types` | Tài khoản đã đăng nhập, class scope |
| GET | `/students?q=&class_id=&grade=&offset=&limit=` | Tài khoản đã đăng nhập, class scope |
| GET | `/students/{code}` | Xem hồ sơ + lịch sử, class scope |
| POST | `/violations` | admin/recorder và lớp được phân công, header Idempotency-Key bắt buộc |
| GET | `/violations?student_code=&class_id=&type_id=&start=&end=` | Nhật ký, class scope |
| PATCH | `/violations/{id}` | admin hoặc đúng người nhập trong phạm vi lớp |
| POST | `/violations/{id}/void` | admin hoặc đúng người nhập; reason bắt buộc |
| GET | `/dashboard?start=&end=` | Phạm vi lớp được cấp |
| GET | `/classes/{id}/summary` | Phạm vi lớp được cấp |
| GET | `/warnings?only_flagged=&level=&offset=&limit=` | Phạm vi lớp được cấp |
| GET | `/reports/weekly?start=&end=` | Báo cáo theo khoảng ngày |
| GET | `/reports/weekly.pdf`, `/reports/weekly.xlsx` | Xuất file có Authorization |
| GET/PUT | `/admin/warning-rules` | admin |
| GET/POST | `/admin/users` | admin |
| PATCH | `/admin/users/{id}` | admin |
| GET | `/admin/audit-logs`, `/admin/import-jobs` | admin |
| POST | `/admin/school-years` | admin |
| POST | `/admin/school-years/{id}/activate` | admin |
| POST | `/admin/classes` | admin |

## Định dạng một lệnh ghi vi phạm

```http
POST /violations HTTP/1.1
Authorization: Bearer <JWT>
Idempotency-Key: <UUID v4 mới cho mỗi lần ghi nhận>
Content-Type: application/json

{
  "student_code": "<MÃ_HỌC_SINH_CÓ_THẬT_TRONG_DB>",
  "violation_type_id": 1,
  "happened_on": "2026-11-02",
  "note": ""
}
```

Trả HTTP 201 và JSON record nếu lưu thành công. Trường `recorded_at` được lấy từ đồng hồ server, không nằm trong body. Khi gửi lại cùng khóa và nội dung, backend trả lại record cũ. Khi nội dung thay đổi với cùng khóa, trả 409. Dùng khóa khác cho **một vi phạm mới**, không dùng khóa khác để thử lại một thao tác mạng chưa rõ kết quả.

Cách đánh giá quyền chỉ thực hiện tại backend: `get_db`, `current_user`, `require`, `assert_class`, `allowed_classes`. Các API báo cáo nhận diện phạm vi lớp trước khi chạy truy vấn dữ liệu.
