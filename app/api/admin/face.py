import uuid
import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.api.deps.db_deps import get_db
from app.services.face_model import face_model_instance, FaceModel
from app.services.face_service import (
    register_user_face,
    verify_user_face,
    recognize_user_face
)
from app.models.user import User
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/admin/face",
    tags=["Admin Face Management"]
)

def get_face_model() -> FaceModel:
    """Dependency injection for the FaceModel instance."""
    return face_model_instance

class AdminRegisterFaceResponse(BaseModel):
    user_id: uuid.UUID
    face_id: uuid.UUID
    name: str
    employee_code: Optional[str] = None
    message: str = "Face registered successfully for user."

class AdminVerifyFaceResponse(BaseModel):
    verified: bool
    user_id: uuid.UUID
    name: Optional[str] = None
    employee_code: Optional[str] = None
    message: str

class AdminRecognizeFaceResponse(BaseModel):
    match: bool
    user_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    employee_code: Optional[str] = None
    message: str

@router.post(
    "/register",
    response_model=AdminRegisterFaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register face for a User (Admin)"
)
async def admin_register_face_route(
    user_id: uuid.UUID = Form(..., description="The User UUID to register face for."),
    file: UploadFile = File(..., description="JPEG/PNG image file containing one face."),
    model: FaceModel = Depends(get_face_model),
    db: Session = Depends(get_db)
):
    """
    Registers a face image for a specific user ID into database and FAISS index.
    Assumes Admin has manually inspected/verified image authenticity beforehand.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await file.read()
        registered_face = register_user_face(db=db, model=model, user_id=user_id, image_bytes=image_bytes)
        
        user = db.query(User).filter(User.id == user_id).first()
        return AdminRegisterFaceResponse(
            user_id=user_id,
            face_id=registered_face,
            name=user.name if user else "",
            employee_code=user.employee_code if user else None,
            message=f"Successfully registered face for employee '{user.name if user else user_id}'."
        )
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke).strip("'"))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"An unexpected error occurred during admin face registration: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post(
    "/verify",
    response_model=AdminVerifyFaceResponse,
    summary="Verify 1-to-1 face against User ID (Admin)"
)
async def admin_verify_face_route(
    user_id: uuid.UUID = Form(..., description="User ID to verify face against."),
    file: UploadFile = File(..., description="JPEG/PNG image file to verify."),
    model: FaceModel = Depends(get_face_model),
    db: Session = Depends(get_db)
):
    """
    Performs 1-to-1 face verification between uploaded image and user's registered face vector.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await file.read()
        is_verified = verify_user_face(db=db, model=model, user_id=user_id, image_bytes=image_bytes)
        user = db.query(User).filter(User.id == user_id).first()
        
        msg = f"Face VERIFIED for employee '{user.name if user else user_id}'." if is_verified else "Face DOES NOT MATCH registered user face."
        
        return AdminVerifyFaceResponse(
            verified=is_verified,
            user_id=user_id,
            name=user.name if user else None,
            employee_code=user.employee_code if user else None,
            message=msg
        )
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke).strip("'"))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"An unexpected error occurred during admin face verification: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post(
    "/recognize",
    response_model=AdminRecognizeFaceResponse,
    summary="Recognize 1-to-N face against FAISS Database (Admin)"
)
async def admin_recognize_face_route(
    file: UploadFile = File(..., description="JPEG/PNG image file to search."),
    model: FaceModel = Depends(get_face_model),
    db: Session = Depends(get_db)
):
    """
    Searches uploaded face image against FAISS index (1-to-N search) and returns matching employee details.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await file.read()
        is_match, matched_user_id = recognize_user_face(db=db, model=model, image_bytes=image_bytes)
        
        if is_match and matched_user_id:
            user = db.query(User).filter(User.id == matched_user_id).first()
            return AdminRecognizeFaceResponse(
                match=True,
                user_id=matched_user_id,
                name=user.name if user else None,
                employee_code=user.employee_code if user else None,
                message=f"Matched employee: '{user.name if user else matched_user_id}'."
            )
        else:
            return AdminRecognizeFaceResponse(
                match=False,
                user_id=None,
                name=None,
                employee_code=None,
                message="No matching employee face found in database."
            )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"An unexpected error occurred during admin face recognition: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete registered face for a User (Admin)"
)
async def admin_delete_face_route(
    user_id: uuid.UUID,
    model: FaceModel = Depends(get_face_model),
    db: Session = Depends(get_db)
):
    """
    Deletes the registered face vector, cropped image file, and DB record for a user ID.
    """
    from app.services.face_service import delete_user_face
    try:
        delete_user_face(db=db, model=model, user_id=user_id)
        return {"message": f"Successfully deleted face for user '{user_id}'."}
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke).strip("'"))
    except Exception as e:
        logging.error(f"An unexpected error occurred during admin face deletion: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.get(
    "/cropped-image/{user_id}",
    summary="Get 4x6 cropped face portrait image of an employee (Admin)"
)
async def admin_get_cropped_face_route(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Serves the 4x6 cropped portrait face image of an employee for display on Admin Web SPA.
    """
    import os
    from fastapi.responses import FileResponse
    from app.core.config import config
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    filenames = [
        f"{user.employee_code or 'NV'}_{user_id}.jpg",
        f"{user_id}.jpg"
    ]
    if user.face:
        filenames.append(f"{user.face.face_id}.jpg")

    for fn in filenames:
        fp = os.path.join(config.CROPPED_FACES_DIR, fn)
        if os.path.exists(fp):
            return FileResponse(fp, media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Cropped face image not found for this user.")
