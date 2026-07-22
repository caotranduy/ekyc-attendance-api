from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

import hashlib
import uuid
from sqlalchemy.orm import Session

def create_access_token(
    subject: str,
    password_snippet: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generates a new JWT access token with revocation support.

    Args:
        subject (str): User ID.
        password_snippet (Optional[str]): Current password / hash for revocation tracking.
        expires_delta (Optional[timedelta]): Expiration delta.

    Returns:
        str: The encoded JWT token string.
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES))
    
    # Generate 8-char pwd fingerprint for token revocation on password change
    pwd_fingerprint = ""
    if password_snippet:
        pwd_fingerprint = hashlib.md5(password_snippet.encode('utf-8')).hexdigest()[:8]

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "pwd": pwd_fingerprint,
        "type": "access"
    }
    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)

def create_refresh_token(
    subject: str,
    password_snippet: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generates a new JWT refresh token with long lifespan (default 30 days)."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS))
    
    pwd_fingerprint = ""
    if password_snippet:
        pwd_fingerprint = hashlib.md5(password_snippet.encode('utf-8')).hexdigest()[:8]

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "pwd": pwd_fingerprint,
        "type": "refresh"
    }
    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """Validates incoming JWT token structure and expiration."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    except jwt.PyJWTError:
        raise credentials_exception

from fastapi import Request

def get_optional_user_id(request: Request, db: Optional[Session] = None) -> Optional[uuid.UUID]:
    """Extracts user_id from Authorization: Bearer <token>, enforcing account status & password revocation checks if DB session provided."""
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    
    parts = auth_header.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    token = parts[1]
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        uid_str = payload.get("sub")
        pwd_fingerprint = payload.get("pwd")
        if not uid_str:
            return None
        
        target_uid = uuid.UUID(uid_str)
        
        # If DB Session is provided, enforce Instant Revocation Checks (is_active & password change)
        if db:
            from app.models.user import User
            user = db.query(User).filter(User.id == target_uid).first()
            if not user or not user.is_active:
                raise HTTPException(status_code=401, detail="Account is inactive or deleted. Access revoked.")
            
            if pwd_fingerprint and user.password:
                current_fp = hashlib.md5(user.password.encode('utf-8')).hexdigest()[:8]
                if current_fp != pwd_fingerprint:
                    raise HTTPException(status_code=401, detail="Password was changed. Access token revoked. Please log in again.")
                    
        return target_uid
    except HTTPException:
        raise
    except Exception:
        pass
    return None