import uuid6 as uuid
import logging
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from app.api.deps.db_deps import get_db
from app.service.face_model import face_model_instance, FaceModel
from app.models.user_face import UserFace
from app.DTO.response import VerifyResponse

router = APIRouter()

def get_face_model() -> FaceModel:
    """Dependency injection for the FaceModel instance."""
    return face_model_instance

@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify a Face against a specific User ID"
)
async def verify_face_endpoint(
    face_image: UploadFile = File(..., description="An image file to verify."),
    user_id: uuid.UUID = Form(..., description="The User ID to compare against."),
    model: FaceModel = Depends(get_face_model),
    db: Session = Depends(get_db)
):
    """
    Receives an image and a user_id, retrieves the registered face_id from the database,
    and verifies if they are a match. This is a 1-to-1 comparison.
    """
    if face_image.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    # Query database to find the face_id registered for this user
    db_face = db.query(UserFace).filter(UserFace.user_id == user_id).first()
    if not db_face:
        raise HTTPException(status_code=404, detail="No face biometric record found for this user.")

    try:
        image_bytes = await face_image.read()
        is_verified = model.verify_face(
            image_bytes=image_bytes, 
            face_id_to_verify=db_face.face_id
        )
        return VerifyResponse(verified=is_verified)
    except ValueError as e:
        logging.warning(f"Verification validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred during verification: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
