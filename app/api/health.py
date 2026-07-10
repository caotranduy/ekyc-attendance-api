import logging
import os
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from typing import List, Dict

from app.models.face_model import face_model_instance
from app.core import config

router = APIRouter()

class ComponentStatus(BaseModel):
    name: str = Field(..., description="Name of the component being checked.")
    status: str = Field(..., description="Operational status, e.g., 'ok' or 'error'.")

class HealthCheckResponse(BaseModel):
    """Defines the health check response schema."""
    overall_status: str = Field(..., description="Overall status of the service.")
    components: List[ComponentStatus] = Field(..., description="Status of individual components.")


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Perform a Health Check",
    tags=["Monitoring"]
)
def perform_health_check(response: Response):
    """
    Checks the operational status of the service and its critical dependencies.
    
    Returns HTTP 200 if the service is healthy, otherwise HTTP 503.
    """
    is_healthy = True
    component_statuses = []

    # 1. Check Dlib Models
    # This is the most critical check for this service.
    if face_model_instance:
        component_statuses.append(ComponentStatus(name="dlib_models", status="ok"))
    else:
        component_statuses.append(ComponentStatus(name="dlib_models", status="error"))
        is_healthy = False
        logging.error("Health check failed: Dlib models are not loaded.")

    # 2. Check Data Directory Permissions (a simple deep check)
    try:
        test_file_path = os.path.join(config.DATA_DIR, 'health_check_test.tmp')
        with open(test_file_path, 'w') as f:
            f.write('ok')
        os.remove(test_file_path)
        component_statuses.append(ComponentStatus(name="data_directory_writable", status="ok"))
    except Exception as e:
        component_statuses.append(ComponentStatus(name="data_directory_writable", status="error"))
        is_healthy = False
        logging.error(f"Health check failed: Data directory is not writable. Error: {e}")

    # Set overall status and HTTP response code
    if is_healthy:
        overall_status = "ok"
        response.status_code = status.HTTP_200_OK
    else:
        overall_status = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthCheckResponse(
        overall_status=overall_status,
        components=component_statuses
    )