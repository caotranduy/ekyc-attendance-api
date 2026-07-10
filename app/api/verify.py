import uuid
import logging
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from app.models.face_model import face_model_instance, FaceModel
from app.schemas.response import VerifyResponse

router = APIRouter()

def get_face_model() -> FaceModel:
    """Dependency injection for the FaceModel instance."""
    return face_model_instance

@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify a Face against a specific ID"
)
async def verify_face_endpoint(
    face_image: UploadFile = File(..., description="An image file to verify."),
    face_id_to_verify: uuid.UUID = Form(..., description="The face ID to compare against."),
    model: FaceModel = Depends(get_face_model)
):
    """
    Receives an image and a specific face_id, and verifies if they are a match.
    This is a 1-to-1 comparison.
    """
    if face_image.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await face_image.read()
        is_verified = model.verify_face(
            image_bytes=image_bytes, 
            face_id_to_verify=face_id_to_verify
        )
        return VerifyResponse(verified=is_verified)
    except ValueError as e:
        logging.warning(f"Verification validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred during verification: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")