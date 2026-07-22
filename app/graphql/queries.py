import uuid
import datetime
from typing import List, Optional
import strawberry
from sqlalchemy.orm import Session
from app.models.check_in_log import CheckInLog
from app.models.user import User
from app.graphql.types import CheckInLogType, UserType, PaginatedUsersType
from app.core.exceptions import AppException
from app.core.error_codes import ErrorCode

def _map_user_to_type(user: Optional[User]) -> Optional[UserType]:
    """Helper to map a User ORM model to UserType."""
    if not user:
        return None
    return UserType(
        id=str(user.id),
        name=user.name,
        username=user.username,
        email=user.email,
        employee_code=user.employee_code,
        gender=user.gender,
        dob=user.dob,
        password=user.password,
        has_registered_face=(user.face is not None),
        face_id=str(user.face.face_id) if user.face else None,
        avatar_url="/api/mobile/personal-info/avatar" if user.face else None,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at
    )

def _map_log_to_type(log: CheckInLog) -> CheckInLogType:
    """Helper to map a CheckInLog ORM model to CheckInLogType."""
    return CheckInLogType(
        id=str(log.id),
        user_id=str(log.user_id),
        check_in_at=log.check_in_at,
        check_in_date=log.check_in_date,
        user=_map_user_to_type(log.user)
    )

@strawberry.type
class Query:
    @strawberry.field(description="Fetch profile of the current authenticated employee (Mobile App)")
    def me(self, info: strawberry.Info) -> Optional[UserType]:
        current_user: Optional[User] = info.context.get("current_user")
        if not current_user:
            raise AppException(
                status_code=401,
                error_code=ErrorCode.UNAUTHORIZED,
                error_message="Authentication required to view profile."
            )
        return _map_user_to_type(current_user)

    @strawberry.field(description="Fetch attendance check-in history of the current authenticated employee (Mobile App)")
    def my_check_in_history(
        self,
        info: strawberry.Info,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
    ) -> List[CheckInLogType]:
        db: Session = info.context["db"]
        current_user: Optional[User] = info.context.get("current_user")
        if not current_user:
            raise AppException(
                status_code=401,
                error_code=ErrorCode.UNAUTHORIZED,
                error_message="Authentication required: Please attach 'Authorization: Bearer <access_token>' header in your GraphQL request."
            )

        query = db.query(CheckInLog).filter(CheckInLog.user_id == current_user.id)
        if start_date:
            query = query.filter(CheckInLog.check_in_date >= start_date)
        if end_date:
            query = query.filter(CheckInLog.check_in_date <= end_date)

        logs = query.order_by(CheckInLog.check_in_at.desc()).all()
        return [_map_log_to_type(l) for l in logs if l]

    @strawberry.field(description="Search users by name or employee code for AutoComplete (Admin)")
    def search_users(
        self,
        info: strawberry.Info,
        keyword: str
    ) -> List[UserType]:
        db: Session = info.context["db"]
        if not keyword or keyword.strip() == "":
            return []

        search_pattern = f"%{keyword.strip()}%"
        users = db.query(User).filter(
            (User.name.ilike(search_pattern)) | 
            (User.employee_code.ilike(search_pattern))
        ).limit(10).all()

        return [_map_user_to_type(u) for u in users if u]

    @strawberry.field(description="Query paginated, sorted, and filtered employees (Admin)")
    def paginated_users(
        self,
        info: strawberry.Info,
        keyword: Optional[str] = None,
        date_filter: Optional[datetime.date] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        sort_by: str = "employee_code",
        sort_order: str = "ASC",
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedUsersType:
        from app.services.admin.employee_service import get_paginated_employees
        from app.graphql.types import PaginatedUsersType

        db: Session = info.context["db"]
        items, total_count, total_pages = get_paginated_employees(
            db=db,
            keyword=keyword,
            date_filter=date_filter,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )

        return PaginatedUsersType(
            total_count=total_count,
            total_pages=total_pages,
            page=page,
            page_size=page_size,
            items=[_map_user_to_type(u) for u in items if u]
        )

    @strawberry.field(description="Query all check-in history across all users or specific user (Admin)")
    def all_check_in_history(
        self,
        info: strawberry.Info,
        target_user_id: Optional[str] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
    ) -> List[CheckInLogType]:
        db: Session = info.context["db"]
        current_user: Optional[User] = info.context.get("current_user")

        # In dev mode, if current_user is None, allow query for easy dev testing
        if current_user and not current_user.is_admin:
            raise AppException(
                status_code=403,
                error_code=ErrorCode.FORBIDDEN,
                error_message="Admin privileges required to query all attendance records."
            )

        query = db.query(CheckInLog)

        if target_user_id:
            try:
                target_uuid = uuid.UUID(target_user_id)
                query = query.filter(CheckInLog.user_id == target_uuid)
            except ValueError:
                raise AppException(
                    status_code=400,
                    error_code=ErrorCode.USER_NOT_FOUND,
                    error_message=f"Invalid target_user_id UUID format: '{target_user_id}'"
                )

        if start_date:
            query = query.filter(CheckInLog.check_in_date >= start_date)
        if end_date:
            query = query.filter(CheckInLog.check_in_date <= end_date)

        logs = query.order_by(CheckInLog.check_in_at.desc()).all()
        return [_map_log_to_type(log) for log in logs]
