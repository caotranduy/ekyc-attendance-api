from typing import Optional, Tuple
import cv2
import dlib
import numpy as np
import faiss
import pickle
import uuid6 as uuid
import logging
import os
from app.core.config import config
from dataclasses import dataclass
from typing import Dict

@dataclass
class RegistrationResult:
    """Standardized response object for face registration operations.
    
    Attributes:
        success (bool): Indicates if the operation completed successfully.
        face_id (Optional[uuid.UUID]): The generated UUID if successful, None otherwise.
        error_message (Optional[str]): Detailed error message if success is False.
    """
    success: bool
    face_id: Optional[uuid.UUID] = None
    error_message: Optional[str] = None

class FaceModel:
    """Handles face detection, feature extraction, and recognition logic using FAISS.

    Attributes:
        detector: Dlib frontal face detector instance.
        sp: Dlib shape predictor instance.
        facerec: Dlib face recognition model instance.
        vector_dimension: The dimension size of face encodings.
        index: FAISS index for L2 distance vector search.
        uuid_mapping: List mapping sequential FAISS index IDs to user UUIDs.
    """
    
    def __init__(self) -> None:
        """Initializes Dlib models and loads the FAISS index mapping from storage."""
        self.vector_dimension = 128
        self.index = faiss.IndexFlatL2(self.vector_dimension)
        self.uuid_mapping = []
        self.uuid_to_index: Dict[uuid.UUID, int] = {}

        try:
            self.cuda_available = dlib.DLIB_USE_CUDA and dlib.cuda.get_num_devices() > 0 # type: ignore
            
            if self.cuda_available:
                logging.info(f"CUDA is available. Using GPU")
                # MÔ HÌNH GPU: Sử dụng CNN để phát hiện khuôn mặt chính xác và nhanh hơn trên GPU
                # Lưu ý: Cần file model mmod_human_face_detector.dat từ dlib
                self.detector = dlib.cnn_face_detection_model_v1(config.CNN_DETECTOR_PATH)
            else:
                logging.info("CUDA not available or dlib compiled without CUDA. Falling back to CPU.")
                # MÔ HÌNH CPU: Sử dụng HOG + Linear SVM truyền thống
                self.detector = dlib.get_frontal_face_detector()

            # Các mô hình này tự động chuyển hướng tính toán sang GPU nếu dlib.DLIB_USE_CUDA == True
            self.sp = dlib.shape_predictor(config.SHAPE_PREDICTOR_PATH)
            self.facerec = dlib.face_recognition_model_v1(config.FACE_REC_MODEL_PATH)
            self._load_index_and_mapping()
            logging.info("FaceModel initialized successfully.")
        except Exception as e:
            logging.critical(f"Fatal error initializing FaceModel: {e}")
            raise RuntimeError("Could not load required models.") from e

    def _load_index_and_mapping(self) -> None:
        """Loads the FAISS index and UUID mapping from physical storage."""
        if hasattr(config, 'FAISS_INDEX_PATH') and os.path.exists(config.FAISS_INDEX_PATH):
            self.index = faiss.read_index(config.FAISS_INDEX_PATH)
        
        if hasattr(config, 'MAPPING_DB_PATH') and os.path.exists(config.MAPPING_DB_PATH):
            with open(config.MAPPING_DB_PATH, 'rb') as f:
                self.uuid_mapping = pickle.load(f)

    def _save_index_and_mapping(self) -> None:
        """Persists the FAISS index and UUID mapping to physical storage."""
        faiss.write_index(self.index, getattr(config, 'FAISS_INDEX_PATH', 'faiss.index'))
        with open(getattr(config, 'MAPPING_DB_PATH', 'uuid_mapping.pkl'), 'wb') as f:
            pickle.dump(self.uuid_mapping, f)

    def _get_single_face_encoding(self, image_bytes: bytes, is_using_cnn: bool = False) -> Tuple[np.ndarray, np.ndarray, dlib.rectangle]:
        """Detects a single face in an image and extracts its 128D encoding.

        Args:
            image_bytes: Raw byte stream of the target image.

        Returns:
            A tuple containing the 128D encoding vector, the decoded image array,
            and the bounding box rectangle of the detected face.

        Raises:
            ValueError: If the image cannot be decoded, or if zero/multiple faces are detected.
        """
        image_np = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image.")

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        dets = self.detector(rgb_img, 1)

        if len(dets) == 0:
            raise ValueError("No face detected.")
        if len(dets) > 1:
            raise ValueError("Multiple faces detected.")

        if isinstance(self.detector, dlib.cnn_face_detection_model_v1):
            face_rect = dets[0].rect
        else:
            face_rect = dets[0]

        shape = self.sp(rgb_img, face_rect)
        face_encoding = np.array(self.facerec.compute_face_descriptor(rgb_img, shape), dtype=np.float32)
        
        return face_encoding, img, face_rect   

    def register_new_face(self, image_bytes: bytes) -> RegistrationResult:
        """Attempts to register a face and returns a structured success/fail result.

        Args:
            image_bytes (bytes): Raw byte stream of the target image.

        Returns:
            RegistrationResult: An object encapsulating the outcome (success/failure) 
            and the corresponding generated UUID or error message.
        """
        try:
            # 1. Trích xuất đặc trưng (Có thể bắn ra ValueError nếu không có mặt hoặc có nhiều mặt)
            face_encoding, original_image, face_rect = self._get_single_face_encoding(image_bytes)
            
            # 2. Thao tác với FAISS
            new_face_id = uuid.uuid7()
            vector = np.array([face_encoding], dtype=np.float32)
            
            current_index = self.index.ntotal
            self.index.add(vector) # type: ignore
            self.uuid_mapping.append(new_face_id)
            self.uuid_to_index[new_face_id] = current_index
            
            # 3. Lưu xuống đĩa cứng (Có thể bắn ra OSError/IOError)
            self._save_index_and_mapping()
            logging.info(f"Successfully registered new face with ID: {new_face_id}")

        except ValueError as ve:
            logging.warning(f"Face validation failed: {ve}")
            return RegistrationResult(success=False, error_message=str(ve))
        except Exception as e:
            logging.error(f"System error during face registration: {e}")
            # Có thể bổ sung logic xóa vector khỏi bộ nhớ FAISS tại đây nếu cần thiết
            return RegistrationResult(success=False, error_message="Internal system error during registration.")

        # 4. Lưu ảnh crop (Tác vụ phụ, nếu lỗi cũng không đánh rớt toàn bộ tiến trình)
        try:
            top, right, bottom, left = face_rect.top(), face_rect.right(), face_rect.bottom(), face_rect.left()
            padding = 20
            
            img_h, img_w = original_image.shape[:2]
            crop_top, crop_bottom = max(0, top - padding), min(img_h, bottom + padding)
            crop_left, crop_right = max(0, left - padding), min(img_w, right + padding)
            
            cropped_face = original_image[crop_top:crop_bottom, crop_left:crop_right]
            
            save_path = os.path.join(getattr(config, 'CROPPED_FACES_DIR', ''), f"{new_face_id}.jpg")
            cv2.imwrite(save_path, cropped_face)
        except Exception as e:
            logging.warning(f"Non-fatal error: Failed to save cropped face image: {e}")

        return RegistrationResult(success=True, face_id=new_face_id)


    def recognize_face(self, image_bytes: bytes) -> Tuple[bool, Optional[uuid.UUID]]:
        """Identifies the closest matching face encoding via FAISS search.

        Args:
            image_bytes: Raw byte stream of the target image.

        Returns:
            A boolean indicating match success, and the corresponding UUID if successful.
        """
        if self.index.ntotal == 0:
            logging.warning("Encodings database is empty. Cannot perform recognition.")
            return False, None

        unknown_encoding, _, _ = self._get_single_face_encoding(image_bytes)
        query_vector = np.array([unknown_encoding], dtype=np.float32)

        distances, indices = self.index.search(query_vector, 1)
        
        best_distance = np.sqrt(distances[0][0])
        best_index = indices[0][0]

        logging.info(f"Best match distance (L2 norm): {best_distance}")

        if best_distance <= config.FACE_RECOGNITION_TOLERANCE and best_index != -1:
            matched_id = self.uuid_mapping[best_index]
            logging.info(f"Match found for user ID: {matched_id}")
            return True, matched_id
        
        logging.info("No match found within tolerance.")
        return False, None
    
    def verify_face(self, image_bytes: bytes, face_id_to_verify: uuid.UUID) -> bool:
        """Verifies if the face in the image matches a specifically provided UUID.

        Args:
            image_bytes: Raw byte stream of the target image.
            face_id_to_verify: The target UUID to verify against.

        Returns:
            True if the distance is within the tolerance threshold, False otherwise.
        """
        try:
            target_idx = self.uuid_mapping.index(face_id_to_verify)
        except ValueError:
            logging.warning(f"Verification attempted for non-existent face_id: {face_id_to_verify}")
            return False

        known_encoding = self.index.reconstruct(target_idx)
        unknown_encoding, _, _ = self._get_single_face_encoding(image_bytes)
        
        distance = np.linalg.norm(known_encoding - unknown_encoding)
        
        return bool(distance <= config.FACE_RECOGNITION_TOLERANCE)

face_model_instance = FaceModel()