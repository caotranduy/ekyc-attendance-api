import uuid
from typing import List
import strawberry
from sqlalchemy.orm import Session
from app.graphql.types import UserType, UserCreateInput, UserUpdateInput, TokenPayloadType
from app.graphql.queries import _map_user_to_type
from app.services.admin.employee_service import (
    create_employee,
    update_employee,
    delete_employee,
    bulk_delete_employees
)
from app.core.exceptions import AppException
from app.core.error_codes import ErrorCode

@strawberry.type
class Mutation:
    @strawberry.mutation(description="Login with username/employee_code and password (returns access & refresh tokens)")
    def login(
        self,
        info: strawberry.Info,
        username: str,
        password: str
    ) -> TokenPayloadType:
        from app.models.user import User
        from app.core.jwt_utils import create_access_token, create_refresh_token

        db: Session = info.context["db"]
        clean_uname = username.strip()
        user = db.query(User).filter(
            (User.username == clean_uname) | 
            (User.employee_code == clean_uname)
        ).first()

        if not user or not user.is_active:
            raise AppException(status_code=401, error_code=ErrorCode.UNAUTHORIZED, error_message="Invalid credentials or inactive account.")

        pwd_matched = False
        if user.password and user.password == password:
            pwd_matched = True
        elif user.hashed_password and user.hashed_password == password:
            pwd_matched = True

        if not pwd_matched:
            raise AppException(status_code=401, error_code=ErrorCode.UNAUTHORIZED, error_message="Invalid credentials. Incorrect password.")

        acc_token = create_access_token(subject=str(user.id), password_snippet=user.password)
        ref_token = create_refresh_token(subject=str(user.id), password_snippet=user.password)

        return TokenPayloadType(
            access_token=acc_token,
            refresh_token=ref_token,
            token_type="bearer",
            user=_map_user_to_type(user)
        )

    @strawberry.mutation(description="Exchange refresh token for a new access token & refresh token pair")
    def refresh_token(
        self,
        info: strawberry.Info,
        refresh_token: str
    ) -> TokenPayloadType:
        import jwt
        import hashlib
        from app.core.config import config
        from app.models.user import User
        from app.core.jwt_utils import create_access_token, create_refresh_token

        db: Session = info.context["db"]
        try:
            payload = jwt.decode(refresh_token.strip(), config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
            if payload.get("type") != "refresh" or not payload.get("sub"):
                raise AppException(status_code=401, error_code=ErrorCode.UNAUTHORIZED, error_message="Invalid refresh token.")

            uid = uuid.UUID(payload.get("sub"))
            user = db.query(User).filter(User.id == uid).first()
            if not user or not user.is_active:
                raise AppException(status_code=401, error_code=ErrorCode.UNAUTHORIZED, error_message="Account is inactive or deleted.")

            pwd_fp = payload.get("pwd")
            if pwd_fp and user.password:
                curr_fp = hashlib.md5(user.password.encode('utf-8')).hexdigest()[:8]
                if curr_fp != pwd_fp:
                    raise AppException(status_code=401, error_code=ErrorCode.UNAUTHORIZED, error_message="Password was changed. Refresh token revoked.")

            acc_token = create_access_token(subject=str(user.id), password_snippet=user.password)
            ref_token = create_refresh_token(subject=str(user.id), password_snippet=user.password)

            return TokenPayloadType(
                access_token=acc_token,
                refresh_token=ref_token,
                token_type="bearer",
                user=_map_user_to_type(user)
            )
        except AppException:
            raise
        except Exception:
            raise AppException(status_code=401, error_code=ErrorCode.UNAUTHORIZED, error_message="Invalid or expired refresh token.")

    @strawberry.mutation(description="Create a new employee with auto-generated code/username/password if omitted")
    def create_user(
        self,
        info: strawberry.Info,
        input: UserCreateInput
    ) -> UserType:
        db: Session = info.context["db"]
        user = create_employee(
            db=db,
            name=input.name,
            employee_code=input.employee_code,
            username=input.username,
            password=input.password,
            gender=input.gender,
            dob=input.dob,
            email=input.email
        )
        return _map_user_to_type(user)

# if you read this, i hope you a good day and please don't notice a big "oopsie" i did

    @strawberry.mutation(description="Update an existing employee by ID")
    def update_user(
        self,
        info: strawberry.Info,
        id: str,
        input: UserUpdateInput
    ) -> UserType:
        db: Session = info.context["db"]
        try:
            user_uuid = uuid.UUID(id)
        except ValueError:
            raise AppException(400, ErrorCode.USER_NOT_FOUND, f"Invalid UUID format: '{id}'")

        user = update_employee(
            db=db,
            user_id=user_uuid,
            name=input.name,
            employee_code=input.employee_code,
            username=input.username,
            password=input.password,
            gender=input.gender,
            dob=input.dob,
            email=input.email,
            is_active=input.is_active
        )
        return _map_user_to_type(user)

    @strawberry.mutation(description="Delete a single employee by ID")
    def delete_user(
        self,
        info: strawberry.Info,
        id: str
    ) -> bool:
        db: Session = info.context["db"]
        try:
            user_uuid = uuid.UUID(id)
        except ValueError:
            raise AppException(400, ErrorCode.USER_NOT_FOUND, f"Invalid UUID format: '{id}'")

        return delete_employee(db=db, user_id=user_uuid)

    @strawberry.mutation(description="Delete multiple employees in bulk by IDs")
    def bulk_delete_users(
        self,
        info: strawberry.Info,
        ids: List[str]
    ) -> int:
        db: Session = info.context["db"]
        user_uuids = []
        for id_str in ids:
            try:
                user_uuids.append(uuid.UUID(id_str))
            except ValueError:
                pass

        return bulk_delete_employees(db=db, user_ids=user_uuids)

