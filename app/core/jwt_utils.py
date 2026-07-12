from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a new JWT access token for a given subject.

    Args:
        subject (str): The primary identifier for the user (e.g., user ID or username).
        expires_delta (Optional[timedelta]): Custom expiration time.

    Returns:
        str: The encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"exp": expire, "sub": str(subject)}
    
    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """Validates the incoming JWT and extracts the subject claim.

    Args:
        token (str): The raw JWT string automatically extracted from the Authorization header.

    Returns:
        str: The decoded subject identifier (user ID).

    Raises:
        HTTPException: 401 Unauthorized if the token is missing, expired, or structurally invalid.
    """
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