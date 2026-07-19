from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import config

# 1. Khởi tạo Engine (Lõi giao tiếp vật lý với DB)
# Lưu ý: 'check_same_thread' chỉ dành riêng cho SQLite để tránh lỗi khi FastAPI chạy đa luồng (multi-threading).
# Nếu là PostgreSQL/MySQL, ta tự động bỏ tham số này đi.
connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    config.DATABASE_URL,
    connect_args=connect_args,
    # pool_pre_ping=True  # (Bật lên nếu dùng DB thật để tự động kiểm tra rớt mạng)
)

# 2. Tạo nhà máy sản xuất Session
# Mỗi khi có 1 request gọi tới API, nhà máy này sẽ đẻ ra 1 kết nối (Session) riêng biệt
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Lớp nền tảng để sau này các bảng (Models) kế thừa
Base = declarative_base()