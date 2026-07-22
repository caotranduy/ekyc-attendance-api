import uuid
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.services.face_model import FaceModel
from app.models.user_face import UserFace
from app.services.anti_spoof_service import anti_spoof_service_instance, AntiSpoofService

def verify_user_face(
    db: Session,
    model: FaceModel,
    user_id: uuid.UUID,
    image_bytes: bytes
) -> bool:
    """Verifies an incoming face image against a specific user account's face ID.

    Args:
        db (Session): SQLAlchemy database session.
        model (FaceModel): FaceModel AI service instance.
        user_id (uuid.UUID): Target user ID to verify against.
        image_bytes (bytes): Raw byte stream of the face image.

    Returns:
        bool: True if the face matches within tolerance, False otherwise.

    Raises:
        KeyError: If no face record exists for the given user ID.
    """
    db_face = db.query(UserFace).filter(UserFace.user_id == user_id).first()
    if not db_face:
        raise KeyError("No face biometric record found for this user.")

    return model.verify_face(image_bytes=image_bytes, face_id_to_verify=db_face.face_id)


def verify_user_face_liveness(
    db: Session,
    model: FaceModel,
    user_id: uuid.UUID,
    frames: List[bytes],
    anti_spoof_service: AntiSpoofService = anti_spoof_service_instance
) -> Tuple[bool, float]:
    """Performs Anti-Spoofing First on 3 JPEG frames, then verifies face matching against user_id.

    Args:
        db (Session): SQLAlchemy database session.
        model (FaceModel): FaceModel AI service instance.
        user_id (uuid.UUID): Target user ID.
        frames (List[bytes]): Exactly 3 JPEG frames.
        anti_spoof_service (AntiSpoofService): AntiSpoofService instance.

    Returns:
        Tuple[bool, float]: (is_verified, avg_liveness_score).

    Raises:
        PermissionError: If liveness average score is below threshold (Spoofing attack).
        KeyError: If no face biometric record exists for user_id.
        ValueError: If frame validation fails.
    """
    # 1. Anti-Spoofing First
    is_real, avg_score = anti_spoof_service.evaluate_liveness_frames(frames)
    if not is_real:
        raise PermissionError(
            f"Anti-Spoofing failed: Replay or Print attack detected. "
            f"Average liveness score ({avg_score:.2f}) is below threshold."
        )

    # 2. Check DB for user's face_id
    db_face = db.query(UserFace).filter(UserFace.user_id == user_id).first()
    if not db_face:
        raise KeyError("No face biometric record found for this user.")

    # 3. Match best frame against FAISS
    is_verified = model.verify_face(image_bytes=frames[0], face_id_to_verify=db_face.face_id)
    return is_verified, avg_score

