import uuid
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.services.face_model import FaceModel
from app.models.user_face import UserFace

def recognize_user_face(
    db: Session,
    model: FaceModel,
    image_bytes: bytes
) -> Tuple[bool, Optional[uuid.UUID]]:
    """Recognizes a face image and maps the FAISS match to the SQL user account ID.

    Args:
        db (Session): SQLAlchemy database session.
        model (FaceModel): FaceModel AI service instance.
        image_bytes (bytes): Raw byte stream of the face image.

    Returns:
        Tuple[bool, Optional[uuid.UUID]]: A tuple containing match success flag 
                                         and the matched user ID (or None if no match).
    """
    is_match, matched_face_id = model.recognize_face(image_bytes=image_bytes)

    if not is_match or matched_face_id is None:
        return False, None

    db_face = db.query(UserFace).filter(UserFace.face_id == matched_face_id).first()
    if not db_face:
        # If vector is in FAISS but deleted from DB, return no match
        return False, None

    return True, db_face.user_id
