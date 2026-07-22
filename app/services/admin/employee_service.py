import uuid
import re
import random
import string
import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.user import User
from app.core.exceptions import AppException
from app.core.error_codes import ErrorCode

def generate_next_employee_code(db: Session) -> str:
    """Finds highest NV-xxxx employee code in database and increments by 1.
    Defaults to 'NV-1001' if no employee codes exist yet.
    """
    users = db.query(User.employee_code).filter(User.employee_code.isnot(None)).all()
    max_num = 1000

    for (code,) in users:
        if code and code.startswith("NV-"):
            try:
                num = int(code.split("NV-")[1])
                if num > max_num:
                    max_num = num
            except (ValueError, IndexError):
                pass

    return f"NV-{max_num + 1}"

def generate_random_password(length: int = 6) -> str:
    """Generates a simple random alphanumeric password (e.g. 'pass123')."""
    letters = string.ascii_lowercase
    digits = string.digits
    chars = random.choices(letters, k=3) + random.choices(digits, k=3)
    random.shuffle(chars)
    return "".join(chars)

def create_employee(
    db: Session,
    name: str,
    employee_code: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    gender: Optional[str] = None,
    dob: Optional[datetime.date] = None,
    email: Optional[str] = None
) -> User:
    """Creates a new employee record with automatic fallbacks for code, username, and plain password."""
    # 1. Fallback for Employee Code
    final_code = employee_code.strip() if employee_code and employee_code.strip() else generate_next_employee_code(db)

    # Check duplicate code
    existing_code = db.query(User).filter(User.employee_code == final_code).first()
    if existing_code:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.FACE_ALREADY_REGISTERED,
            error_message=f"Employee code '{final_code}' already exists."
        )

    # 2. Fallback for Username
    final_username = username.strip() if username and username.strip() else final_code

    # Check duplicate username
    existing_user = db.query(User).filter(User.username == final_username).first()
    if existing_user:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.FACE_ALREADY_REGISTERED,
            error_message=f"Username '{final_username}' already exists."
        )

    # 3. Fallback for Plain Text Password
    final_password = password.strip() if password and password.strip() else generate_random_password()

    # Create User ORM instance
    user = User(
        name=name.strip(),
        employee_code=final_code,
        username=final_username,
        password=final_password,
        hashed_password=final_password, # Mirror plain text password
        gender=gender,
        dob=dob,
        email=email.strip() if email else None,
        is_active=True,
        is_admin=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_employee(
    db: Session,
    user_id: uuid.UUID,
    name: Optional[str] = None,
    employee_code: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    gender: Optional[str] = None,
    dob: Optional[datetime.date] = None,
    email: Optional[str] = None,
    is_active: Optional[bool] = None
) -> User:
    """Updates an existing employee's information."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            status_code=44,
            error_code=ErrorCode.USER_NOT_FOUND,
            error_message=f"User with ID '{user_id}' not found."
        )

    if name is not None and name.strip():
        user.name = name.strip()
    if employee_code is not None and employee_code.strip():
        user.employee_code = employee_code.strip()
    if username is not None and username.strip():
        user.username = username.strip()
    if password is not None and password.strip():
        user.password = password.strip()
        user.hashed_password = password.strip()
    if gender is not None:
        user.gender = gender
    if dob is not None:
        user.dob = dob
    if email is not None:
        user.email = email.strip() if email else None
    if is_active is not None:
        user.is_active = is_active

    db.commit()
    db.refresh(user)
    return user

def delete_employee(db: Session, user_id: uuid.UUID) -> bool:
    """Deletes a single employee record by UUID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.USER_NOT_FOUND,
            error_message=f"User with ID '{user_id}' not found."
        )

    db.delete(user)
    db.commit()
    return True

def bulk_delete_employees(db: Session, user_ids: List[uuid.UUID]) -> int:
    """Deletes multiple employees in bulk by UUID list. Returns count of deleted records."""
    if not user_ids:
        return 0

    count = db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()
    return count

def get_paginated_employees(
    db: Session,
    keyword: Optional[str] = None,
    date_filter: Optional[datetime.date] = None,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    sort_by: str = "employee_code",
    sort_order: str = "ASC",
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[User], int, int]:
    """Retrieves paginated, filtered, and sorted employee records from database.
    Returns (items, total_count, total_pages).
    """
    query = db.query(User)

    # Keyword filter
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(User.name.ilike(pattern), User.employee_code.ilike(pattern))
        )

    # Date filters
    if date_filter:
        query = query.filter(User.created_at >= date_filter)
    if start_date:
        query = query.filter(User.created_at >= start_date)
    if end_date:
        query = query.filter(User.created_at <= end_date)

    total_count = query.count()
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    # Sorting
    sort_column = getattr(User, sort_by, User.employee_code)
    if sort_order.upper() == "DESC":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Pagination OFFSET & LIMIT
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return items, total_count, total_pages
