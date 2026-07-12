import os
import face_recognition_models as frm
from pydantic_settings import BaseSettings


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

    # Create necessary directories at startup
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CROPPED_FACES_DIR, exist_ok=True)

    FACE_RECOGNITION_TOLERANCE : float = 0.6


    SECRET_KEY: str = "mot-chuoi-bi-mat-cuc-ky-dai-va-kho-doan-danh-cho-moi-truong-dev"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

config = Settings()