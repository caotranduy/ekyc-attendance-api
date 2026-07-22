import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps.db_deps import get_db
from app.models.user import User
from app.core.jwt_utils import create_access_token, create_refresh_token
from app.core.config import config
import jwt
import hashlib

router = APIRouter(
    prefix="/auth",
    tags=["Authentication Module"]
)

class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Access Token for API Authorization.")
    refresh_token: str = Field(..., description="JWT Refresh Token for refreshing expired access tokens.")
    token_type: str = "bearer"
    user_id: uuid.UUID
    name: str
    employee_code: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="The JWT refresh token to exchange.")

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login for Employee & Admin (Generates Access Token + Refresh Token)"
)
def login_route(
    username: str = Form(..., description="Username or Employee Code"),
    password: str = Form(..., description="Plain-text or hashed password"),
    db: Session = Depends(get_db)
):
    """
    Authenticates user by username or employee_code and plain-text password.
    Returns access_token and refresh_token.
    """
    clean_uname = username.strip()
    user = db.query(User).filter(
        (User.username == clean_uname) | 
        (User.employee_code == clean_uname)
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials. User not found.")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive or disabled.")

    # Match plain-text password or hashed_password
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
    summary="Exchange Refresh Token for a New Access Token & Refresh Token"
)
def refresh_token_route(
    dto: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Validates refresh token and issues a fresh pair of access_token and refresh_token.
    Enforces revocation checks on user status and password changes.
    """
    token_str = dto.refresh_token.strip()
    try:
        payload = jwt.decode(token_str, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        token_type = payload.get("type")
        uid_str = payload.get("sub")
        pwd_fp = payload.get("pwd")

        if token_type != "refresh" or not uid_str:
            raise HTTPException(status_code=401, detail="Invalid token type. Refresh token required.")

        target_uid = uuid.UUID(uid_str)
        user = db.query(User).filter(User.id == target_uid).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Account is inactive or deleted. Refresh denied.")

        if pwd_fp and user.password:
            curr_fp = hashlib.md5(user.password.encode('utf-8')).hexdigest()[:8]
            if curr_fp != pwd_fp:
                raise HTTPException(status_code=401, detail="Password was changed. Refresh token revoked. Please log in again.")

        new_acc_token = create_access_token(subject=str(user.id), password_snippet=user.password)
        new_ref_token = create_refresh_token(subject=str(user.id), password_snippet=user.password)

        return TokenResponse(
            access_token=new_acc_token,
            refresh_token=new_ref_token,
            user_id=user.id,
            name=user.name,
            employee_code=user.employee_code
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired. Please log in again.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")
