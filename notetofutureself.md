due to Python's faulty directory detection, setuptool cannot find the path to cuDNN library
best solution I did is pasting this block of cmake instruction
```cmake
set(DLIB_USE_CUDA ON CACHE BOOL "" FORCE)
set(CUDNN_INCLUDE_PATH "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.4/include" CACHE PATH "" FORCE)
set(CUDNN_LIBRARY_PATH "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.4/lib/x64/cudnn.lib" CACHE FILEPATH "" FORCE)
```

to line 11 under ``project(dlib_python_bindings)`` in 
``dlib/tools/python/CMakeLists.txt``, then run 
``python setup.py install``

---

# HƯỚNG DẪN THIẾT LẬP MÔI TRƯỜNG CONDA VÀ CÀI ĐẶT PHỤ THUỘC

Tài liệu này ghi chú lại kiến trúc, các phụ thuộc cốt lõi và hướng dẫn từng bước để tái tạo môi trường ảo Conda từ đầu khi kéo mã nguồn (clone) về máy mới hoặc khôi phục dự án sau khi dọn ổ đĩa.

---

## 1. Yêu cầu tiên quyết (Prerequisites)
1. **Hệ điều hành:** Windows 10/11 (hoặc Linux Ubuntu 20.04+).
2. **Quản lý môi trường:** Miniconda hoặc Anaconda đã cài đặt.
3. **Phiên bản Python bắt buộc:** **Python 3.10**
   > [!IMPORTANT]
   > Bắt buộc sử dụng Python 3.10. Các phiên bản Python mới hơn (3.11, 3.12, 3.13) hiện tại thường gặp xung đột biên dịch C++ với thư viện `dlib` và `faiss-cpu` trên Windows.
4. **Công cụ biên dịch C++ (Chỉ dành cho Windows khi build dlib):**
   - Cài đặt Visual Studio C++ Build Tools (với tuỳ chọn *Desktop development with C++*) hoặc cài đặt thông qua `conda-forge`.

---

## 2. Quy trình thiết lập môi trường Conda từ đầu (Step-by-Step Setup)

### Bước 1: Tạo và kích hoạt môi trường Conda
Mở terminal (Anaconda Prompt hoặc PowerShell) tại thư mục dự án:

```bash
# 1. Tạo môi trường ảo với Python 3.10
conda create -n face_checkin python=3.10 -y

# 2. Kích hoạt môi trường
conda activate face_checkin
```

### Bước 2: Cài đặt công cụ hỗ trợ biên dịch và dlib
Để tránh lỗi biên dịch `dlib` trên Windows, cách ổn định nhất là cài CMake và dlib thông qua kênh `conda-forge`:

```bash
# Cài đặt CMake từ conda-forge
conda install -c conda-forge cmake -y

# Cài đặt dlib biên dịch sẵn cho Python 3.10
conda install -c conda-forge dlib -y
```
*(Nếu muốn biên dịch dlib tận dụng GPU CUDA cuDNN, xem hướng dẫn cấu hình CMake ở đầu tệp này).*

### Bước 3: Cài đặt toàn bộ phụ thuộc từ `requirements.txt`
```bash
pip install -r requirements.txt
```

*(Lưu ý: Thư viện `uuid6>=2024.1.12` đã được cấu hình trong `requirements.txt` để hỗ trợ sinh mã UUIDv7 tuần tự theo thời gian cho các bảng dữ liệu).*

---

## 3. Cấu hình biến môi trường (`.env`)
Tạo tệp `.env` tại thư mục gốc của dự án (cùng cấp với `run.py`):

```env
# Khoá bí mật cho JWT và chữ ký số HMAC
SECRET_KEY=aiface_super_secret_ekyc_key_2026

# Tài khoản quản trị viên truy cập Portal /admin/
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin

# Đường dẫn dữ liệu
DATABASE_URL=sqlite:///./app/data/database.db
FAISS_INDEX_PATH=./app/data/faiss.index
MAPPING_DB_PATH=./app/data/uuid_mapping.pkl

# Ngưỡng nhận diện và kiểm tra liveness
FACE_RECOGNITION_TOLERANCE=0.45
LIVENESS_THRESHOLD=0.85
```

---

## 4. Khởi tạo cơ sở dữ liệu mẫu (Database Seeding)
Trước khi khởi chạy hệ thống lần đầu, chạy script tạo bảng và dữ liệu nhân viên mẫu:

```bash
python seed_db.py
```
Script này sẽ:
- Tự động tạo bảng SQLite `users`, `user_faces`, `check_in_logs`.
- Tạo sẵn 2 nhân viên mẫu:
  - `NV-1001`: Nguyễn Văn An (`an.nguyen`)
  - `NV-1002`: Trần Thị Bình (`binh.tran`)
- Sinh dữ liệu chấm công mẫu cho tháng 07/2026.

---

## 5. Khởi chạy ứng dụng (Run Application)

```bash
# Cách 1: Chạy trực tiếp qua run.py
python run.py

# Cách 2: Chạy qua uvicorn CLI với auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 10000 --reload
```

---

## 6. Các địa chỉ truy cập chính (Endpoints & Portals)
Khi ứng dụng khởi chạy thành công tại cổng `10000`:

| Dịch vụ / Giao diện | Đường dẫn URL | Ghi chú |
| :--- | :--- | :--- |
| **API Documentation (Swagger)** | `http://localhost:10000/docs` | Kiểm tra và gọi thử các REST API |
| **Admin Management Portal** | `http://localhost:10000/admin/` | Đăng nhập bằng HTTP Basic Auth (`admin` / `admin`) |
| **GraphQL Playground** | `http://localhost:10000/graphql` | Thực hiện truy vấn thông tin nhân viên & lịch sử |
| **Health Check API** | `http://localhost:10000/api/health` | Kiểm tra trạng thái Database và FAISS Index |

---

## 7. Chạy kiểm thử tự động (Unit Tests)
Để đảm bảo tất cả logic (xác thực HMAC, độ lệch múi giờ, CRUD nhân viên, kiểm tra orphan face) hoạt động chính xác:

```bash
pytest app/test/test.py
```