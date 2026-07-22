import uuid
import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps.db_deps import get_db
from app.models.user import User
from app.core.jwt_utils import create_access_token, create_refresh_token
from app.core.config import config
import jwt

router = APIRouter(
    prefix="/auth",
    tags=["Mobile Authentication"]
)

class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Access Token for Authorization.")
    refresh_token: str = Field(..., description="JWT Refresh Token for renewing expired access tokens.")
    token_type: str = "bearer"
    user_id: uuid.UUID
    name: str
    employee_code: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="The JWT refresh token.")

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login for Mobile App (Returns Access & Refresh Tokens)"
)
def login_mobile(
    username: str = Form(..., description="Username or Employee Code"),
    password: str = Form(..., description="Password"),
    db: Session = Depends(get_db)
):
    clean_uname = username.strip()
    user = db.query(User).filter(
        (User.username == clean_uname) | 
        (User.employee_code == clean_uname)
    ).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials or inactive account.")

    pwd_matched = False
    if user.password and user.password == password:
        pwd_matched = True
    elif user.hashed_password and user.hashed_password == password:
        pwd_matched = True

    if not pwd_matched:
        raise HTTPException(status_code=401, detail="Invalid credentials. Incorrect password.")

    acc_token = create_access_token(subject=str(user.id), password_snippet=user.password)
    ref_token = create_refresh_token(subject=str(user.id), password_snippet=user.password)

    return TokenResponse(
        access_token=acc_token,
        refresh_token=ref_token,
        user_id=user.id,
        name=user.name,
        employee_code=user.employee_code
    )

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange Refresh Token for a fresh Access & Refresh Token pair"
)
def refresh_mobile(
    dto: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    token_str = dto.refresh_token.strip()
    try:
        payload = jwt.decode(token_str, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        if payload.get("type") != "refresh" or not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid token type. Refresh token required.")

        target_uid = uuid.UUID(payload.get("sub"))
        user = db.query(User).filter(User.id == target_uid).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Account is inactive or deleted. Access revoked.")

        pwd_fp = payload.get("pwd")
        if pwd_fp and user.password:
            curr_fp = hashlib.md5(user.password.encode('utf-8')).hexdigest()[:8]
            if curr_fp != pwd_fp:
                raise HTTPException(status_code=401, detail="Password was changed. Access token revoked. Please log in again.")

        new_acc = create_access_token(subject=str(user.id), password_snippet=user.password)
        new_ref = create_refresh_token(subject=str(user.id), password_snippet=user.password)

        return TokenResponse(
            access_token=new_acc,
            refresh_token=new_ref,
            user_id=user.id,
            name=user.name,
            employee_code=user.employee_code
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired. Please log in again.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")
