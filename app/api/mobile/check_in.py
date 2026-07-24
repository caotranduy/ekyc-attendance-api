import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, Form, Header, HTTPException, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps.db_deps import get_db
from app.services.face_model import face_model_instance, FaceModel
from app.services.anti_spoof_service import anti_spoof_service_instance, AntiSpoofService
from app.services.check_in_service import process_ekyc_check_in
from app.DTO.response import CheckInResponse, ErrorResponse
from app.core.security import verify_hmac_signature, validate_client_timestamp
from app.core.jwt_utils import get_optional_user_id

router = APIRouter(
    prefix="/check-in",
    tags=["Mobile eKYC Check-In"]
)

def get_face_model() -> FaceModel:
    return face_model_instance

def get_anti_spoof_service() -> AntiSpoofService:
    return anti_spoof_service_instance

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
async def check_in_ekyc_mobile(
    request: Request,
    user_id: Optional[str] = Form(None, description="Optional User ID (UUID string)."),
    files: List[UploadFile] = File(..., description="Exactly 3 JPEG frames from Active Liveness."),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp", description="ISO 8601 UTC timestamp."),
    x_nonce: Optional[str] = Header(None, alias="X-Nonce", description="Random unique nonce string."),
    x_signature: Optional[str] = Header(None, alias="X-Signature", description="HMAC-SHA256 request signature."),
    model: FaceModel = Depends(get_face_model),
    anti_spoof_service: AntiSpoofService = Depends(get_anti_spoof_service),
    db: Session = Depends(get_db)
):
    parsed_user_id = None
    if user_id and user_id.strip() and user_id.strip().lower() != "null":
        try:
            parsed_user_id = uuid.UUID(user_id.strip())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format. Must be a valid UUID.")

    jwt_user_id = get_optional_user_id(request, db=db)
    target_user_id = jwt_user_id or parsed_user_id

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

    frame_bytes_list: List[bytes] = []
    for f in files:
        if f.content_type not in ["image/jpeg", "image/jpg"]:
            raise HTTPException(status_code=400, detail=f"Invalid file format for {f.filename}. Only JPEG images are accepted.")
        content = await f.read()
        frame_bytes_list.append(content)

    # 4. Execute Service Pipeline
    log_record = process_ekyc_check_in(
        db=db,
        model=model,
        anti_spoof_service=anti_spoof_service,
        user_id=target_user_id,
        frames=frame_bytes_list,
        client_timestamp=client_dt
    )

    return CheckInResponse(
        user_id=log_record.user_id,
        check_in_at=log_record.check_in_at.isoformat()
    )
