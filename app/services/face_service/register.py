import uuid
import logging
from sqlalchemy.orm import Session
from app.services.face_model import FaceModel
from app.models.user import User
from app.models.user_face import UserFace

def register_user_face(
    db: Session,
    model: FaceModel,
    user_id: uuid.UUID,
    image_bytes: bytes
) -> uuid.UUID:
    """Registers a face for an existing user account without HTTP dependencies.

    Args:
        db (Session): SQLAlchemy database session.
        model (FaceModel): FaceModel AI service instance.
        user_id (uuid.UUID): Target user ID.
        image_bytes (bytes): Raw byte stream of the face image.

    Returns:
        uuid.UUID: The generated FAISS face ID linked to the user.

    Raises:
        KeyError: If the user ID does not exist in the database.
        ValueError: If the user already has a registered face, or if the face is a duplicate,
                    or if feature extraction fails.
    """
    # 1. Check if user exists in DB
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise KeyError("User not found.")

    # 2. Check if user already has a registered face
    if db_user.face is not None:
        raise ValueError("User already has a registered face.")

    # 3. Check if physical face is already registered in FAISS/DB
    is_recognized, matched_face_id = model.recognize_face(image_bytes=image_bytes)
    if is_recognized and matched_face_id is not None:
        db_face = db.query(UserFace).filter(UserFace.face_id == matched_face_id).first()
        if db_face:
            raise ValueError("This face is already registered to another user.")

    # 4. Extract features & add to FAISS
    registered_face = model.register_new_face(image_bytes=image_bytes)
    if not registered_face.success or registered_face.face_id is None:
        raise ValueError(registered_face.error_message or "Failed to register face encoding.")

    # 5. Save cropped 4x6 face image file to CROPPED_FACES_DIR as {employee_code}_{user_id}.jpg
    if registered_face.cropped_jpeg_bytes:
        try:
            import os
            from app.core.config import config
            filename = f"{db_user.employee_code or 'NV'}_{user_id}.jpg"
            file_path = os.path.join(config.CROPPED_FACES_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(registered_face.cropped_jpeg_bytes)
            logging.info(f"Saved cropped 4x6 face image to '{file_path}'.")
        except Exception as e:
            logging.warning(f"Failed to save cropped face image file: {e}")

    # 6. Link user with face_id in UserFace table
    db_user_face = UserFace(user_id=user_id, face_id=registered_face.face_id)
    db.add(db_user_face)
    db.commit()
    db.refresh(db_user)

    logging.info(f"Successfully registered face for user {db_user.name} (ID: {user_id}) with face ID: {registered_face.face_id}")
    return registered_face.face_id
