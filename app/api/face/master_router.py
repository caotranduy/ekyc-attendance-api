from fastapi import APIRouter, Depends
from . import register_face, verify #delete
from app.core.jwt_utils import get_current_user_id


face_master_router = APIRouter(
    prefix="/face",
    tags=["Face Module"],

    dependencies=[Depends(get_current_user_id)]
)

face_master_router.include_router(register_face.router, tags=["Face Registration"])
face_master_router.include_router(verify.router, tags=["Face Verification"])
#face_master_router.include_router(delete.router)