import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from app.models.face_model import face_model_instance, FaceModel
from app.schemas.response import RegisterSuccessResponse

router = APIRouter()

def get_face_model() -> FaceModel:
    """Dependency injection for the FaceModel instance."""
    return face_model_instance

@router.post(
    "/register",
    response_model=RegisterSuccessResponse,
    summary="Register a New Face"
)
async def register_face_endpoint(
    file: UploadFile = File(..., description="An image file (JPG or PNG) containing one face."),
    model: FaceModel = Depends(get_face_model)
):
    """
    Receives an image, registers the face, and returns the assigned user ID.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await file.read()
        user_id = model.register_new_face(image_bytes=image_bytes)
        return RegisterSuccessResponse(user_id=user_id)
    except ValueError as e:
        logging.warning(f"Registration validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred during registration: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")