import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from app.api.deps.db_deps import get_db
from app.service.face_model import face_model_instance, FaceModel
from app.models.user_face import UserFace
from app.DTO.response import RecognizeResponse

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
    model: FaceModel = Depends(get_face_model),
    db: Session = Depends(get_db)
):
    """
    Receives an image, finds the best match in the FAISS database, 
    and queries SQL to return the actual user_id corresponding to that face.
    
    The API call is successful (HTTP 200) even if no match is found.
    Errors (e.g., no face detected) will result in an HTTP 400 error.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await file.read()
        is_match, matched_face_id = model.recognize_face(image_bytes=image_bytes)
        
        user_id = None
        if is_match and matched_face_id:
            # Map the FAISS face_id to the actual SQL user_id using the UserFace table
            db_face = db.query(UserFace).filter(UserFace.face_id == matched_face_id).first()
            if db_face:
                user_id = db_face.user_id
            else:
                # If face exists in FAISS but user_face was deleted from DB, treat as no match
                is_match = False

        return RecognizeResponse(match=is_match, user_id=user_id)
    except ValueError as e:
        logging.warning(f"Recognition validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred during recognition: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")