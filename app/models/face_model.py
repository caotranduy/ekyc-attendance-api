from typing import Optional, Tuple
import cv2
import dlib
import numpy as np
import pickle
import uuid
import logging
import os
from app.core import config

class FaceModel:
    """Handles all face detection and recognition business logic."""
    
    def __init__(self):
        """Initializes Dlib models."""
        try:
            self.detector = dlib.get_frontal_face_detector()
            self.sp = dlib.shape_predictor(config.SHAPE_PREDICTOR_PATH)
            self.facerec = dlib.face_recognition_model_v1(config.FACE_REC_MODEL_PATH)
            logging.info("FaceModel initialized successfully.")
        except Exception as e:
            logging.critical(f"Fatal error initializing FaceModel: {e}")
            raise RuntimeError("Could not load dlib models.") from e

    def _load_encodings(self) -> dict:
        """Loads face encodings from the pickle file."""
        try:
            with open(config.ENCODINGS_DB_PATH, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return {}

    def _save_encodings(self, encodings_data: dict) -> None:
        """Saves face encodings to the pickle file."""
        with open(config.ENCODINGS_DB_PATH, 'wb') as f:
            pickle.dump(encodings_data, f)

    def _get_single_face_encoding(self, image_bytes: bytes) -> tuple:
        """
        A helper function to find exactly one face and return its details:
        the encoding, the original image array, and the face rectangle.

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
        
        face_rect = dets[0]
        shape = self.sp(rgb_img, face_rect)
        face_encoding = np.array(self.facerec.compute_face_descriptor(rgb_img, shape))
        
        return face_encoding, img, face_rect   


    def register_new_face(self, image_bytes: bytes) -> uuid.UUID:
        """
        Processes an image, extracts encoding, saves it, and returns a new user ID.

        Args:
            image_bytes: The image file in bytes.

        Returns:
            A new unique UUID for the registered user.
        
        Raises:
            ValueError: If no face or multiple faces are detected.
        """

        face_encoding, original_image, face_rect = self._get_single_face_encoding(image_bytes)
        
        known_encodings = self._load_encodings()
        new_face_id = uuid.uuid4()
        known_encodings[new_face_id] = face_encoding
        self._save_encodings(known_encodings)
        
        logging.info(f"Successfully registered new face with ID: {new_face_id}")

        try:
            face_encoding, original_image, face_rect = self._get_single_face_encoding(image_bytes)      
            # Get coordinates and add some padding
            top, right, bottom, left = face_rect.top(), face_rect.right(), face_rect.bottom(), face_rect.left()
            padding = 20
            # Crop the original image (use BGR image from cv2.imdecode)
            cropped_face = original_image[max(0, top-padding):bottom+padding, max(0, left-padding):right+padding]
            
            # Create filename and save path
            filename = f"{new_face_id}.jpg"
            save_path = os.path.join(config.CROPPED_FACES_DIR, filename)
            
            cv2.imwrite(save_path, cropped_face)
            logging.info(f"Successfully saved cropped face image to: {save_path}")
        except Exception as e:
            logging.error(f"Failed to save cropped face image: {e}")

        return new_face_id
    
    def recognize_face(self, image_bytes: bytes) -> Tuple[bool, Optional[uuid.UUID]]:
        """
        Finds the closest match for a face in the database from an image.

        Args:
            image_bytes: The image file in bytes.

        Returns:
            A tuple containing (True, user_id) if a match is found,
            otherwise (False, None).

        Raises:
            ValueError: If no face or multiple faces are detected in the input image.
        """
        known_encodings_data = self._load_encodings()
        if not known_encodings_data:
            logging.warning("Encodings database is empty. Cannot perform recognition.")
            return (False, None)

        # Separate known encodings into lists of UUIDs and vectors
        known_ids = list(known_encodings_data.keys())
        known_vectors = np.array(list(known_encodings_data.values()))

        # Process the input image
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

        # Get encoding for the unknown face
        shape = self.sp(rgb_img, dets[0])
        unknown_encoding = np.array(self.facerec.compute_face_descriptor(rgb_img, shape))

        # Compare with known faces
        # This computes the distance between the unknown face and all known faces
        distances = np.linalg.norm(known_vectors - unknown_encoding, axis=1)
        
        best_match_index = np.argmin(distances)
        best_distance = distances[best_match_index]

        logging.info(f"Best match distance: {best_distance}")

        if best_distance <= config.FACE_RECOGNITION_TOLERANCE:
            matched_id = known_ids[best_match_index]
            logging.info(f"Match found for user ID: {matched_id}")
            return (True, matched_id)
        
        logging.info("No match found within tolerance.")
        return (False, None)
    
    def verify_face(self, image_bytes: bytes, face_id_to_verify: uuid.UUID) -> bool:
        """Verifies if a face matches a specific known face ID (1-to-1 comparison)."""
        known_encodings_data = self._load_encodings()
        known_encoding = known_encodings_data.get(face_id_to_verify)

        if known_encoding is None:
            logging.warning(f"Verification attempted for non-existent face_id: {face_id_to_verify}")
            return False

        unknown_encoding, original_image, face_rect = self._get_single_face_encoding(image_bytes)
        
        distance = np.linalg.norm(known_encoding - unknown_encoding)
        
        return distance <= config.FACE_RECOGNITION_TOLERANCE

# Instantiate the model once to be reused across the application
face_model_instance = FaceModel()