import logging
import uuid6 as uuid
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from app.api.deps.db_deps import get_db
from app.service.face_model import face_model_instance, FaceModel
from app.models.user import User
from app.models.user_face import UserFace
from app.DTO.response import RegisterSuccessResponse

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
    user_id: uuid.UUID = Form(..., description="The UUID of the pre-existing user."),
    file: UploadFile = File(..., description="An image file (JPG or PNG) containing one face."),
    model: FaceModel = Depends(get_face_model),
    db: Session = Depends(get_db)
):
    """
    Receives an image and a user's ID, verifies that the user exists and does not already 
    have a face registered. Checks if the face in the image is already registered to 
    prevent duplicates, then registers the new face and links it to the user.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    # 1. Check if the user exists in the database
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")

    # 2. Check if the user already has a face registered
    if db_user.face is not None:
        raise HTTPException(status_code=400, detail="User already has a registered face.")

    try:
        image_bytes = await file.read()

        # 3. Check if the physical face is already registered in the FAISS index to prevent duplication
        is_recognized, matched_face_id = model.recognize_face(image_bytes=image_bytes)
        if is_recognized:
            # Double check if this face_id is currently active in the database
            db_face = db.query(UserFace).filter(UserFace.face_id == matched_face_id).first()
            if db_face:
                raise HTTPException(status_code=400, detail="This face is already registered to another user.")

        # 4. Register the new face
        registered_face = model.register_new_face(image_bytes=image_bytes)
        if registered_face.success and registered_face.face_id is not None:
            # Create a new UserFace record linking the user to the registered face_id
            db_user_face = UserFace(user_id=user_id, face_id=registered_face.face_id)
            db.add(db_user_face)
            db.commit()
            db.refresh(db_user)
            
            logging.info(f"Successfully registered face for user {db_user.name} with ID {db_user.id} and face ID {registered_face.face_id}")
            return RegisterSuccessResponse(user_id=db_user.id)
        else:
            raise HTTPException(status_code=400, detail=registered_face.error_message)
    except HTTPException:
        raise
    except ValueError as e:
        logging.warning(f"Registration validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred during registration: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

