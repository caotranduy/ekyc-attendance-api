import uuid
import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

class EmployeeCreateDTO(BaseModel):
    """Pydantic DTO for creating a new employee."""
    name: str = Field(..., description="Full name of the employee")
    employee_code: Optional[str] = Field(None, description="Employee Code (e.g. NV-1001). Auto-generated if omitted.")
    username: Optional[str] = Field(None, description="Username. Defaults to employee_code if omitted.")
    password: Optional[str] = Field(None, description="Plain text password. Auto-generated if omitted.")
    gender: Optional[str] = Field(None, description="Gender (Nam/Nữ/Khác)")
    dob: Optional[datetime.date] = Field(None, description="Date of birth")
    email: Optional[str] = Field(None, description="Email address")

class EmployeeUpdateDTO(BaseModel):
    """Pydantic DTO for updating an existing employee."""
    name: Optional[str] = Field(None, description="Full name of the employee")
    employee_code: Optional[str] = Field(None, description="Employee Code")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Plain text password")
    gender: Optional[str] = Field(None, description="Gender")
    dob: Optional[datetime.date] = Field(None, description="Date of birth")
    email: Optional[str] = Field(None, description="Email address")
    is_active: Optional[bool] = Field(None, description="Account active status")

class EmployeeResponseDTO(BaseModel):
    """Pydantic DTO for employee response details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    username: Optional[str] = None
    email: Optional[str] = None
    employee_code: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[datetime.date] = None
    password: Optional[str] = None
    has_registered_face: bool = False
    face_id: Optional[uuid.UUID] = None
    is_active: bool
    is_admin: bool
    created_at: datetime.datetime

class BulkDeleteDTO(BaseModel):
    """Pydantic DTO for bulk deleting employees by IDs."""
    user_ids: List[uuid.UUID] = Field(..., description="List of user UUIDs to delete")

class PaginatedEmployeeResponseDTO(BaseModel):
    """Pydantic DTO for paginated employee responses."""
    total_count: int
    total_pages: int
    page: int
    page_size: int
    items: List[EmployeeResponseDTO]
