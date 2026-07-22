from fastapi import APIRouter
from . import auth, check_in, personal_info, check_in_history

mobile_router = APIRouter(
    prefix="/mobile",
    tags=["Mobile App Endpoints"]
)

mobile_router.include_router(auth.router)
mobile_router.include_router(check_in.router)
mobile_router.include_router(personal_info.router)
mobile_router.include_router(check_in_history.router)
