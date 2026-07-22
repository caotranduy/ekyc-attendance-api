"""
Script dọn sạch (reset) toàn bộ dữ liệu khuôn mặt:
1. Xóa các tệp dữ liệu FAISS index (faiss.index, uuid_mapping.pkl, encodings.pkl).
2. Xóa toàn bộ ảnh chân dung crop trong thư mục app/data/cropped_faces/.
3. Xóa toàn bộ bản ghi trong bảng user_faces CSDL SQLite/PostgreSQL.
"""
import os
import glob
import logging
from sqlalchemy import text
from app.core.config import config
from app.db.session import engine
def reset_all_faces():
    print("🧹 Bắt đầu dọn sạch dữ liệu khuôn mặt...")
    
    # 1. Xóa file FAISS index và UUID mapping
    files_to_remove = [
        config.FAISS_INDEX_PATH,
        config.MAPPING_DB_PATH,
        config.ENCODINGS_DB_PATH
    ]
    for filepath in files_to_remove:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"  [✓] Đã xóa file: {filepath}")
            except Exception as e:
                print(f"  [x] Lỗi xóa file {filepath}: {e}")
    # 2. Xóa toàn bộ tệp ảnh trong thư mục cropped_faces/
    if os.path.exists(config.CROPPED_FACES_DIR):
        cropped_files = glob.glob(os.path.join(config.CROPPED_FACES_DIR, "*"))
        count = 0
        for f in cropped_files:
            try:
                os.remove(f)
                count += 1
            except Exception as e:
                print(f"  [x] Lỗi xóa ảnh {f}: {e}")
        print(f"  [✓] Đã dọn dẹp {count} ảnh chân dung trong '{config.CROPPED_FACES_DIR}'.")
    # 3. Xóa dữ liệu trong bảng user_faces của Database
    try:
        with engine.connect() as conn:
            result = conn.execute(text("DELETE FROM user_faces"))
            conn.commit()
            print(f"  [✓] Đã xóa toàn bộ bản ghi liên kết khuôn mặt trong CSDL (bảng `user_faces`).")
    except Exception as e:
        print(f"  [!] Lỗi dọn dẹp bảng user_faces (có thể do bảng chưa được tạo): {e}")
    print("\n✨ HOÀN TẤT RESET DỮ LIỆU KHUÔN MẶT! Bạn có thể khởi động lại server và test từ đầu.")
if __name__ == "__main__":
    reset_all_faces()