import os
import uuid
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps.db_deps import get_db
from app.models.user import User
from app.core.jwt_utils import get_optional_user_id
from app.core.config import config

router = APIRouter(
    prefix="/personal-info",
    tags=["Mobile Personal Profile"]
)

class PersonalInfoResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    employee_code: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[datetime.date] = None
    has_registered_face: bool = False
    avatar_url: Optional[str] = None
    is_active: bool

@router.get(
    "",
    response_model=PersonalInfoResponse,
    summary="Get Personal Profile of Logged-in Employee (JWT Bearer Token)"
)
def get_personal_info_mobile(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = get_optional_user_id(request, db=db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required. Please provide a valid Bearer token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee record not found.")

    has_face = user.face is not None
    avatar_link = "/api/mobile/personal-info/avatar" if has_face else None

    return PersonalInfoResponse(
        user_id=user.id,
        name=user.name,
        employee_code=user.employee_code,
        username=user.username,
        email=user.email,
        gender=user.gender,
        dob=user.dob,
        has_registered_face=has_face,
        avatar_url=avatar_link,
        is_active=user.is_active
    )

@router.get(
    "/avatar",
    summary="Download/Stream 4x6 Cropped Avatar Image of Logged-in Employee"
)
def get_personal_avatar_mobile(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = get_optional_user_id(request, db=db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required. Please provide a valid Bearer token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.face:
        raise HTTPException(status_code=404, detail="No registered face avatar found for this employee.")

    face_id = user.face.face_id
    possible_filenames = [
        f"{user.employee_code or 'NV'}_{user.id}.jpg",
        f"{user.id}.jpg",
        f"{face_id}.jpg"
    ]

    image_path = None
    for fn in possible_filenames:
        fp = os.path.join(config.CROPPED_FACES_DIR, fn)
        if os.path.exists(fp):
            image_path = fp
            break

    if not image_path:
        raise HTTPException(status_code=404, detail="Cropped face avatar file not found on disk.")

    return FileResponse(image_path, media_type="image/jpeg", filename=f"avatar_{user.employee_code}.jpg")
