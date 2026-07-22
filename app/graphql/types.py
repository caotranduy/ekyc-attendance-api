import datetime
from typing import Optional, List
import strawberry

@strawberry.type
class UserType:
    """GraphQL type representation of a User account."""
    id: str
    name: str
    username: Optional[str] = None
    email: Optional[str] = None
    employee_code: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[datetime.date] = None
    password: Optional[str] = None
    has_registered_face: bool = False
    face_id: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime.datetime] = None

@strawberry.type
class TokenPayloadType:
    """GraphQL type for login & refresh token responses."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserType] = None

@strawberry.input
class UserCreateInput:
    """GraphQL input for creating a new employee."""
    name: str
    employee_code: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[datetime.date] = None
    email: Optional[str] = None

@strawberry.input
class UserUpdateInput:
    """GraphQL input for updating an existing employee."""
    name: Optional[str] = None
    employee_code: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[datetime.date] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

@strawberry.type
class PaginatedUsersType:
    """GraphQL type for paginated user list responses."""
    total_count: int
    total_pages: int
    page: int
    page_size: int
    items: List[UserType]

@strawberry.type
class CheckInLogType:
    """GraphQL type representation of a CheckInLog record."""
    id: str
    user_id: str
    check_in_at: datetime.datetime
    check_in_date: datetime.date
    user: Optional[UserType] = None
