import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from app.models.face_model import face_model_instance, FaceModel
from app.schemas.response import RecognizeResponse

router = APIRouter()

def get_face_model() -> FaceModel:
    """Dependency injection for the FaceModel instance."""
    return face_model_instance

@router.post(
    "/recognize",
    response_model=RecognizeResponse,
    summary="Recognize a Face"
)
async def recognize_face_endpoint(
    file: UploadFile = File(..., description="An image file to check against the database."),
    model: FaceModel = Depends(get_face_model)
):
    """
    Receives an image, finds the best match in the database, and returns the result.
    
    The API call is successful (HTTP 200) even if no match is found.
    Errors (e.g., no face detected) will result in an HTTP 400 error.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await file.read()
        is_match, user_id = model.recognize_face(image_bytes=image_bytes)
        return RecognizeResponse(match=is_match, user_id=user_id)
    except ValueError as e:
        logging.warning(f"Recognition validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred during recognition: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")