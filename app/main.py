import logging
from fastapi import FastAPI, APIRouter
from app.api import health
from app.api.face.master_router import face_master_router
from fastapi.middleware.cors import CORSMiddleware


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(
    title="Face Recognition API",
    description="A modular microservice for face recognition.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trên production, bắt buộc thay "*" bằng danh sách domain thực tế
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(
    prefix="/api"
)
api.include_router(health.router)
api.include_router(face_master_router)
#api.include_router(auth)


app.include_router(api)