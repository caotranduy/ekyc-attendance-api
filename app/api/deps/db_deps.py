from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

def get_db() -> Generator[Session, None, None]:
    """
    Dependency quản lý vòng đời của Database.
    Nguyên lý:
    1. Yêu cầu (Request) đến -> Mở kết nối (yield db)
    2. Xử lý logic xong -> Dù thành công hay lỗi sập server (try/finally) -> Vẫn bắt buộc phải đóng kết nối (db.close())
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()