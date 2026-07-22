import os
import uuid
import logging
from sqlalchemy.orm import Session
from app.services.face_model import FaceModel
from app.models.user import User
from app.models.user_face import UserFace
from app.core.config import config

def delete_user_face(
    db: Session,
    model: FaceModel,
    user_id: uuid.UUID
) -> bool:
    """Deletes a registered face for a user account (removes FAISS vector, cropped image file, and DB record).

    Args:
        db (Session): SQLAlchemy database session.
        model (FaceModel): FaceModel AI service instance.
        user_id (uuid.UUID): Target user ID.

    Returns:
        bool: True if deletion succeeded.

    Raises:
        KeyError: If the user ID or user's registered face record does not exist.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise KeyError("User not found.")

    if db_user.face is None:
        raise KeyError("User does not have a registered face to delete.")

    face_id = db_user.face.face_id

    # 1. Delete FAISS vector index & mapping
    model.delete_face(face_id)

    # 2. Delete cropped face image file from disk ({employee_code}_{user_id}.jpg & legacy fallback filenames)
    filenames = [
        f"{db_user.employee_code or 'NV'}_{user_id}.jpg",
        f"{user_id}.jpg",
        f"{face_id}.jpg"
    ]
    for fn in filenames:
        fp = os.path.join(config.CROPPED_FACES_DIR, fn)
        if os.path.exists(fp):
            try:
                os.remove(fp)
                logging.info(f"Deleted cropped face image file: {fp}")
            except Exception as e:
                logging.warning(f"Could not remove cropped image file '{fp}': {e}")

    # 3. Delete UserFace database record
    db.delete(db_user.face)
    db.commit()
    db.refresh(db_user)

    logging.info(f"Successfully deleted face record for user '{db_user.name}' ({user_id}).")
    return True
