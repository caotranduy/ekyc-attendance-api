# Mô tả Dự án: Hệ thống eKYC Bảo mật Cao

Dự án này là một hệ thống **eKYC (Electronic Know Your Customer - Định danh Điện tử)** thu nhỏ ("pocket-size") nhưng sẵn sàng cho sản xuất (production-ready). Hệ thống kết hợp các công nghệ xử lý ảnh truyền thống, mô hình học sâu (Deep Learning) chạy bằng ONNX Runtime và cơ sở dữ liệu vector hiệu năng cao để xác thực danh tính người dùng một cách an toàn và tối ưu.

---

## 1. Kiến trúc luồng Edge-to-Cloud eKYC

Hệ thống hoạt động theo mô hình tối ưu băng thông và bảo mật:
1. **Phía Client (Frontend)**: Chụp lại luồng video hoạt động của người dùng (Active Liveness), lựa chọn ra chính xác **3 khung hình JPEG ngẫu nhiên** (chất lượng tốt nhất, độ phân giải tối đa 1080p) kèm theo mã định danh giao dịch `UUID` để gửi lên Backend.
2. **Phía Server (Backend)**: Nhận 3 khung hình này để xử lý. **Tuyệt đối không xử lý luồng video thô** để đảm bảo hiệu năng và giới hạn dung lượng tải trọng (payload limits).

---

## 2. Quy trình xử lý Anti-Spoofing & Nhận diện khuôn mặt

```mermaid
flowchart TD
    A[Nhận 3 khung hình JPEG từ Client] --> B[Trích xuất & Cắt khuôn mặt từ ảnh]
    B --> C[ONNX Anti-Spoofing Model (80x80)]
    C --> D{Tính điểm Liveness trung bình}
    D -- Dưới ngưỡng (< threshold) --> E[Từ chối ngay lập tức: 403 HTTP Error]
    D -- Đạt ngưỡng (>= threshold) --> F[Trích xuất Vector 128D bằng dlib]
    F --> G[Tìm kiếm & So khớp qua FAISS]
    G --> H{Cơ chế biểu quyết 2/3 hoặc khoảng cách L2}
    H -- Không khớp --> I[Xác thực Thất bại / Ghi log]
    H -- Khớp khuôn mặt --> J[Xác thực Thành công / Trả về kết quả]
    E & I & J --> K[Ghi lịch sử vào bảng AuditLog]
```

1. **Kiểm tra Giả mạo trước (Anti-Spoofing First)**:
   - Trước khi thực hiện bất kỳ bước nhận diện nào, các khuôn mặt sẽ được cắt và chuyển đổi về kích thước chuẩn `80x80` pixel.
   - Các ảnh này được đưa qua mô hình chống giả mạo thụ động (Passive Liveness) **MiniFASNet** chạy trên **ONNX Runtime (CPU execution)**.
   - Nếu điểm liveness trung bình của 3 khung hình thấp hơn ngưỡng an toàn, hệ thống sẽ trả về lỗi **HTTP 403 Forbidden** ngay lập tức để chặn các cuộc tấn công dạng Replay/Print attack.
2. **Trích xuất đặc trưng**:
   - Sử dụng thư viện **dlib** để trích xuất vector đặc trưng khuôn mặt 128 chiều (128D Vectors).
3. **So khớp khuôn mặt (Face Matching)**:
   - Sử dụng cơ sở dữ liệu vector **FAISS (faiss-cpu)** để tìm kiếm vector gần nhất dựa trên khoảng cách L2.
   - Áp dụng cơ chế **Biểu quyết 2/3 (2/3 Voting Mechanism)** hoặc so sánh khoảng cách L2 trung bình thay vì cơ chế cứng nhắc "chỉ cần 1 khung hình hỏng là đánh trượt" nhằm tăng độ chính xác trong điều kiện ánh sáng thực tế.

---

## 3. Công nghệ lõi (Tech Stack)

- **Ngôn ngữ**: Python 3.10+
- **Backend Web**: [FastAPI](https://fastapi.tiangolo.com/) (Modular, Dependency Injection thông qua `Depends`).
- **Cơ sở dữ liệu**:
  - ORM: **SQLAlchemy 2.0** (Sử dụng SQLite cho môi trường phát triển local và PostgreSQL cho môi trường production).
  - Khóa chính sử dụng định dạng **UUIDv7** giúp tối ưu hóa việc sắp xếp theo thời gian và hiệu năng đánh chỉ mục.
- **Cơ sở dữ liệu Vector**: **FAISS-CPU** phục vụ tìm kiếm vector tương đồng với tốc độ cực nhanh.
- **Thư viện AI/CV**:
  - Phát hiện và nhận diện khuôn mặt: **dlib** + **opencv-python**.
  - Mô hình Liveness: **onnxruntime** (Chạy trên CPU) + **numpy**.
- **Quản lý cấu hình**: **Pydantic V2** (`pydantic-settings`) hỗ trợ đọc cấu hình từ file `.env` một cách chặt chẽ.
- **Xác thực bảo mật**: OAuth2 chuẩn mã hóa JWT sử dụng thư viện `PyJWT` kết hợp mật khẩu được băm bằng `passlib` và `bcrypt`.

---

## 4. Thiết kế Database & Lưu trữ Lịch sử (Audit)

Hệ thống duy trì hai bảng chính trong SQLite/PostgreSQL:
- **`users`**: Lưu trữ thông tin người dùng được đăng ký gồm `id` (UUIDv7), `name` (tên người dùng), `face_id` (mã liên kết với chỉ mục trong FAISS) và `created_at`.
- **`audit_logs`**: Lưu vết tất cả các giao dịch eKYC, lưu trữ thời gian, loại giao dịch, trạng thái thành công/thất bại, điểm liveness trung bình thu được và lý do từ chối cụ thể. Đây là thành phần quan trọng phục vụ giao diện giám sát của Quản trị viên (Admin Interface).

---

## 5. Định hướng phát triển giao diện Admin

Giao diện Admin sẽ được tích hợp trực tiếp vào Backend FastAPI dưới dạng các tệp tĩnh (Static Files) tại đường dẫn `/admin`, bao gồm các tính năng chính:
- **Bảng điều khiển (Dashboard)**: Thống kê tổng quan số lượng người dùng, số lượt giao dịch, biểu đồ theo dõi tần suất tấn công giả mạo (Spoofing rejections).
- **Quản lý Người dùng**: Danh sách người dùng, chức năng thêm thủ công và xóa người dùng (kèm cơ chế tự đánh giá thời điểm thấp tải để rebuild lại chỉ mục FAISS an toàn).
- **Xem nhật ký giao dịch**: Bộ lọc nhật ký giao dịch chi tiết, hỗ trợ lọc nhanh các trường hợp bị hệ thống từ chối do phát hiện giả mạo để kiểm tra.
- **Cấu hình hệ thống**: Cho phép điều chỉnh ngưỡng Liveness và khoảng cách khớp L2 của FAISS ngay trên giao diện trực quan.
