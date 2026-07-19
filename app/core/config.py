import os
import face_recognition_models as frm
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Get paths to models automatically from the installed library
    SHAPE_PREDICTOR_PATH : str = frm.pose_predictor_model_location()
    FACE_REC_MODEL_PATH : str = frm.face_recognition_model_location()
    CNN_DETECTOR_PATH :str = frm.cnn_face_detector_model_location()


    # Define base directory for data and temporary uploads
    BASE_DIR : str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR : str  = os.path.join(BASE_DIR, 'data')


    CROPPED_FACES_DIR : str = os.path.join(DATA_DIR, 'cropped_faces')
    ENCODINGS_DB_PATH :str = os.path.join(DATA_DIR, 'encodings.pkl')
    FAISS_INDEX_PATH : str = os.path.join(DATA_DIR, 'faiss.index')
    MAPPING_DB_PATH :str = os.path.join(DATA_DIR, 'uuid_mapping.pkl')

    DATABASE_URL: str = ""

    # Create necessary directories at startup
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CROPPED_FACES_DIR, exist_ok=True)

    from pydantic import model_validator

    @model_validator(mode="after")
    def validate_database_url(self) -> "Settings":
        if not self.DATABASE_URL or self.DATABASE_URL.strip() == "":
            self.DATABASE_URL = "sqlite:///" + os.path.join(self.DATA_DIR, "database.db")
        return self

    FACE_RECOGNITION_TOLERANCE : float = 0.6


    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
            env_file=".env",              # Chỉ định file cần đọc
            env_file_encoding="utf-8",    # Định dạng mã hóa tệp
            extra="ignore"                # Bỏ qua nếu trong .env có các biến thừa không khai báo ở Class này
        )

config = Settings()