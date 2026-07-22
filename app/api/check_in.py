import uuid
from fastapi import APIRouter, Form, Depends
from sqlalchemy.orm import Session
from app.api.deps.db_deps import get_db
from app.services.check_in_service import process_user_check_in
from app.DTO.response import CheckInResponse, ErrorResponse
from app.core.exceptions import AppException


router = APIRouter(
    prefix="/check-in",
    tags=["Check-In Module"]
)

@router.post(
    "",
    response_model=CheckInResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Already checked in today or invalid request."},
        404: {"model": ErrorResponse, "description": "User not found."}
    },
    summary="Record daily attendance check-in for a user"
)
async def check_in_endpoint(
    user_id: uuid.UUID = Form(..., description="The User ID to check in."),
    db: Session = Depends(get_db)
):
    """
    Receives a user_id and records daily attendance check-in.
    If the user has already checked in today, returns ErrorResponse with ALREADY_CHECKIN.
    """
    check_in_record = process_user_check_in(db=db, user_id=user_id)
    return CheckInResponse(
        user_id=check_in_record.user_id,
        check_in_at=check_in_record.check_in_at.isoformat()
    )

from typing import List, Optional
from fastapi import Header, File, UploadFile, HTTPException
from app.services.face_model import face_model_instance, FaceModel
from app.services.anti_spoof_service import anti_spoof_service_instance, AntiSpoofService
from app.services.check_in_service import process_ekyc_check_in
from app.core.security import verify_hmac_signature, validate_client_timestamp

def get_face_model() -> FaceModel:
    return face_model_instance

def get_anti_spoof_service() -> AntiSpoofService:
    return anti_spoof_service_instance

from fastapi import Request

@router.post(
    "/ekyc",
    response_model=CheckInResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Time drift exceeded, unverified face, or duplicate check-in."},
        401: {"model": ErrorResponse, "description": "HMAC Request Signature or JWT Token mismatched."},
        403: {"model": ErrorResponse, "description": "Anti-Spoofing Rejected (Replay/Print attack)."}
    },
    summary="Automated eKYC Attendance Check-In (JWT Token / Form User ID / Zero-Input 1-N)"
)
async def check_in_ekyc_endpoint(
    request: Request,
    user_id: Optional[uuid.UUID] = Form(None, description="Optional User ID (If omitted, extracted from JWT Bearer token or 1-N FAISS Search)."),
    files: List[UploadFile] = File(..., description="Exactly 3 JPEG frames from Active Liveness."),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp", description="ISO 8601 UTC timestamp."),
    x_nonce: Optional[str] = Header(None, alias="X-Nonce", description="Random unique nonce string."),
    x_signature: Optional[str] = Header(None, alias="X-Signature", description="HMAC-SHA256 request signature."),
    model: FaceModel = Depends(get_face_model),
    anti_spoof_service: AntiSpoofService = Depends(get_anti_spoof_service),
    db: Session = Depends(get_db)
):
    """
    Automated eKYC Attendance Check-In Pipeline:
    1. Extracts target user_id from JWT Bearer token, Form data, or leaves None for 1-N FAISS search.
    2. Verifies HMAC-SHA256 signature (X-Signature Header) & client timestamp drift <= 60s (X-Timestamp Header).
    3. Enforces Anti-Spoofing First evaluation on 3 JPEG frames (HTTP 403 on fail).
    4. Performs 1-1 verification (if user_id known) or 1-N recognition (if zero-input).
    5. Saves CheckInLog with check_in_at = client_timestamp.
    """
    # Extract user_id from JWT Token if present & enforce Instant Revocation Checks (is_active & password change)
    from app.core.jwt_utils import get_optional_user_id
    jwt_user_id = get_optional_user_id(request, db=db)
    
    target_user_id = jwt_user_id or user_id

    # 1. Security Check: HMAC Signature Validation
    if x_signature:
        if not x_timestamp or not x_nonce:
            raise HTTPException(status_code=400, detail="Missing X-Timestamp or X-Nonce headers required for HMAC signature verification.")
        
        sig_uid = str(target_user_id) if target_user_id else ""
        is_valid_sig = verify_hmac_signature(
            timestamp_str=x_timestamp,
            nonce=x_nonce,
            user_id_str=sig_uid,
            signature=x_signature
        )
        if not is_valid_sig:
            raise HTTPException(status_code=401, detail="Invalid Request Signature (HMAC mismatched). Tampering detected.")

    # 2. Client Timestamp & Drift Validation (<= 60s)
    if x_timestamp:
        client_dt = validate_client_timestamp(x_timestamp, max_drift_seconds=60)
    else:
        import datetime
        client_dt = datetime.datetime.utcnow()

    # 3. Payload Files Validation (Exactly 3 frames required)
    if len(files) != 3:
        raise HTTPException(status_code=400, detail=f"eKYC Check-In requires exactly 3 JPEG frames. Received {len(files)}.")

    frames_bytes = []
    for f in files:
        if f.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(status_code=400, detail="Invalid frame file type. Must be JPG or PNG.")
        content = await f.read()
        frames_bytes.append(content)

    # 4. Delegate to process_ekyc_check_in
    try:
        check_in_record = process_ekyc_check_in(
            db=db,
            model=model,
            anti_spoof_service=anti_spoof_service,
            user_id=target_user_id,
            frames=frames_bytes,
            client_timestamp=client_dt
        )
        return CheckInResponse(
            user_id=check_in_record.user_id,
            check_in_at=check_in_record.check_in_at.isoformat()
        )
    except AppException:
        raise
    except Exception as e:
        import logging
        logging.error(f"An unexpected error occurred during eKYC check-in: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
