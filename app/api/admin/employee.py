import uuid
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps.db_deps import get_db
from app.DTO.admin_dto import (
    EmployeeCreateDTO,
    EmployeeUpdateDTO,
    EmployeeResponseDTO,
    BulkDeleteDTO,
    PaginatedEmployeeResponseDTO
)
from app.services.admin.employee_service import (
    create_employee,
    update_employee,
    delete_employee,
    bulk_delete_employees,
    get_paginated_employees
)

router = APIRouter(
    prefix="/admin/employees",
    tags=["Admin Employee Management"]
)

@router.post("/", response_model=EmployeeResponseDTO, status_code=status.HTTP_201_CREATED)
def create_employee_route(
    dto: EmployeeCreateDTO,
    db: Session = Depends(get_db)
):
    """Creates a new employee record. Auto-generates employee_code, username, and password if omitted."""
    user = create_employee(
        db=db,
        name=dto.name,
        employee_code=dto.employee_code,
        username=dto.username,
        password=dto.password,
        gender=dto.gender,
        dob=dto.dob,
        email=dto.email
    )
    return user

@router.get("/", response_model=PaginatedEmployeeResponseDTO)
def list_employees_route(
    keyword: Optional[str] = Query(None, description="Search keyword for name or employee code"),
    date_filter: Optional[datetime.date] = Query(None, description="Exact creation date filter"),
    start_date: Optional[datetime.date] = Query(None, description="Start date filter"),
    end_date: Optional[datetime.date] = Query(None, description="End date filter"),
    sort_by: str = Query("employee_code", description="Sort column (employee_code, name, gender, dob, created_at)"),
    sort_order: str = Query("ASC", description="Sort direction (ASC/DESC)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Lists employees with server-side pagination, sorting, and keyword/date filtering."""
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

    return PaginatedEmployeeResponseDTO(
        total_count=total_count,
        total_pages=total_pages,
        page=page,
        page_size=page_size,
        items=[EmployeeResponseDTO.model_validate(item) for item in items]
    )

@router.get("/{user_id}", response_model=EmployeeResponseDTO)
def get_employee_route(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Retrieves full details of a specific employee, including plain text password."""
    items, _, _ = get_paginated_employees(db=db, page=1, page_size=1)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from app.core.exceptions import AppException
        from app.core.error_codes import ErrorCode
        raise AppException(404, ErrorCode.USER_NOT_FOUND, f"User '{user_id}' not found.")
    return user

@router.put("/{user_id}", response_model=EmployeeResponseDTO)
def update_employee_route(
    user_id: uuid.UUID,
    dto: EmployeeUpdateDTO,
    db: Session = Depends(get_db)
):
    """Updates information of an existing employee."""
    user = update_employee(
        db=db,
        user_id=user_id,
        name=dto.name,
        employee_code=dto.employee_code,
        username=dto.username,
        password=dto.password,
        gender=dto.gender,
        dob=dto.dob,
        email=dto.email,
        is_active=dto.is_active
    )
    return user

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_employee_route(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Deletes a single employee by UUID."""
    delete_employee(db=db, user_id=user_id)
    return {"message": f"Successfully deleted employee '{user_id}'."}

@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
def bulk_delete_employees_route(
    dto: BulkDeleteDTO,
    db: Session = Depends(get_db)
):
    """Deletes multiple employees in bulk by UUID list."""
    count = bulk_delete_employees(db=db, user_ids=dto.user_ids)
    return {"message": f"Successfully deleted {count} employees.", "deleted_count": count}
