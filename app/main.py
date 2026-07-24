import logging
from fastapi import FastAPI, APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from app.api import health
#from app.api.face import router as face_router
from app.api.test_face import router as test_face_router
from app.api.check_in import router as check_in_router
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import Base, engine
from app.core.exceptions import AppException
from app.core.error_codes import ErrorCode
import app.models.user  # Register User model
import app.models.user_face  # Register UserFace model
import app.models.check_in_log  # Register CheckInLog model

from sqlalchemy import text

# Create SQLite tables on startup & auto-migrate missing columns
Base.metadata.create_all(bind=engine)

def auto_upgrade_sqlite_schema():
    with engine.connect() as conn:
        for col_def in [
            "ALTER TABLE users ADD COLUMN employee_code VARCHAR(20)",
            "ALTER TABLE users ADD COLUMN gender VARCHAR(10)",
            "ALTER TABLE users ADD COLUMN dob DATETIME",
            "ALTER TABLE users ADD COLUMN password VARCHAR(255)"
        ]:
            try:
                conn.execute(text(col_def))
                conn.commit()
            except Exception:
                pass

auto_upgrade_sqlite_schema()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(
    title="Face Recognition API",
    description="A modular microservice for face recognition and eKYC check-in.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trên production, bắt buộc thay "*" bằng danh sách domain thực tế
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Custom Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "error_message": exc.error_message
        }
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.exception(f"Unhandled Exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error_code": ErrorCode.INTERNAL_SYSTEM_ERROR.value,
            "error_message": f"An internal server error occurred: {str(exc)}"
        }
    )

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.graphql.router import graphql_app
from app.api.admin.employee import router as admin_employee_router
from app.api.admin.face import router as admin_face_router
from app.api.auth_router import router as auth_router
from app.api.mobile.router import mobile_router
from app.api.deps.admin_deps import verify_admin

api = APIRouter(
    prefix="/api"
)
api.include_router(health.router)
#api.include_router(face_router)
api.include_router(check_in_router)
api.include_router(test_face_router)
api.include_router(admin_employee_router, dependencies=[Depends(verify_admin)])
api.include_router(admin_face_router, dependencies=[Depends(verify_admin)])
api.include_router(auth_router)
api.include_router(mobile_router)

app.include_router(api)
app.include_router(graphql_app, prefix="/graphql")

admin_static_dir = os.path.join(os.path.dirname(__file__), "static", "admin")
os.makedirs(admin_static_dir, exist_ok=True)

from fastapi.responses import RedirectResponse

@app.get("/admin", dependencies=[Depends(verify_admin)])
async def redirect_admin():
    return RedirectResponse(url="/admin/")

@app.get("/admin/", dependencies=[Depends(verify_admin)])
@app.get("/admin/index.html", dependencies=[Depends(verify_admin)])
async def get_admin_index():
    return FileResponse(os.path.join(admin_static_dir, "index.html"))

app.mount("/admin", StaticFiles(directory=admin_static_dir, html=True), name="admin")