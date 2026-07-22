import uuid
import datetime
import logging
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.check_in_log import CheckInLog
from app.core.exceptions import AppException
from app.core.error_codes import ErrorCode

def process_user_check_in(db: Session, user_id: uuid.UUID) -> CheckInLog:
    """Processes a daily check-in request for a user.

    1. Checks if the user exists in DB.
    2. Fetches the current timestamp and date.
    3. Checks if the user has already checked in on the current date.
    4. If already checked in, raises AppException with ALREADY_CHECKIN error code.
    5. If not checked in, creates a new CheckInLog record in DB.

    Args:
        db (Session): SQLAlchemy database session.
        user_id (uuid.UUID): Target user ID.

    Returns:
        CheckInLog: The newly created check-in log record.

    Raises:
        AppException: With error_code USER_NOT_FOUND (404) or ALREADY_CHECKIN (400).
    """
    # 1. Check if user exists
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.USER_NOT_FOUND,
            error_message="User account not found."
        )

    # 2. Get current datetime and current date
    now = datetime.datetime.utcnow()
    today = now.date()

    # 3. Check if user already checked in today
    existing_log = db.query(CheckInLog).filter(
        CheckInLog.user_id == user_id,
        CheckInLog.check_in_date == today
    ).first()

    if existing_log:
        logging.info(f"Check-in rejected: User {db_user.name} (ID: {user_id}) already checked in today on {today}.")
        raise AppException(
            status_code=400,
            error_code=ErrorCode.ALREADY_CHECKIN,
            error_message=f"User '{db_user.name}' has already checked in today ({today})."
        )

    # 4. Create new check-in record
    check_in_record = CheckInLog(
        user_id=user_id,
        check_in_at=now,
        check_in_date=today
    )
    db.add(check_in_record)
    db.commit()
    db.refresh(check_in_record)

    logging.info(f"Check-in successful: User {db_user.name} (ID: {user_id}) checked in at {now}.")
    return check_in_record

from typing import List, Optional
from app.services.face_model import FaceModel
from app.services.anti_spoof_service import AntiSpoofService
from app.services.face_service import verify_user_face, recognize_user_face
from app.core.config import config

def process_ekyc_check_in(
    db: Session,
    model: FaceModel,
    anti_spoof_service: AntiSpoofService,
    user_id: Optional[uuid.UUID],
    frames: List[bytes],
    client_timestamp: datetime.datetime
) -> CheckInLog:
    """Processes an automated eKYC attendance check-in request.

    - If user_id is provided (via JWT or Form), performs 1-to-1 face verification against that user.
    - If user_id is None, performs 1-to-N FAISS face recognition to identify employee automatically.
    """
    # 1. Anti-Spoofing First (Passive Liveness Check on 3 frames)
    try:
        is_real, avg_score = anti_spoof_service.evaluate_liveness_frames(frames)
    except ValueError as ve:
        err_msg = str(ve)
        err_code = ErrorCode.NO_FACE_DETECTED if "No face detected" in err_msg else ErrorCode.INVALID_REQUEST
        raise AppException(
            status_code=400,
            error_code=err_code,
            error_message=err_msg
        )

    if not is_real:
        logging.warning(f"eKYC Anti-Spoofing REJECTED: Avg Score {avg_score:.4f} < {config.LIVENESS_THRESHOLD}")
        raise AppException(
            status_code=403,
            error_code=ErrorCode.SPOOFING_ATTACK_DETECTED,
            error_message=f"eKYC Anti-Spoofing Rejected: Average liveness score {avg_score:.4f} is below threshold {config.LIVENESS_THRESHOLD} (Replay/Print attack detected)."
        )

    target_user_id = user_id

    # 2. Perform Face Recognition / Verification across all 3 frames (Best-Match resiliency)
    if target_user_id is None:
        # 1-to-N Recognition across all frames
        matched_id = None
        for frame in frames:
            try:
                is_match, found_id = recognize_user_face(db=db, model=model, image_bytes=frame)
                if is_match and found_id:
                    matched_id = found_id
                    break
            except Exception:
                continue

        if matched_id is None:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.INVALID_REQUEST,
                error_message="eKYC Recognition Failed: No matching registered employee face found in database."
            )
        target_user_id = matched_id
    else:
        # 1-to-1 Verification across all frames
        is_verified = False
        for frame in frames:
            try:
                if verify_user_face(db=db, model=model, user_id=target_user_id, image_bytes=frame):
                    is_verified = True
                    break
            except Exception:
                continue

        if not is_verified:
            db_user = db.query(User).filter(User.id == target_user_id).first()
            raise AppException(
                status_code=400,
                error_code=ErrorCode.INVALID_REQUEST,
                error_message=f"eKYC Verification Failed: Uploaded face does not match registered employee '{db_user.name if db_user else target_user_id}'."
            )

    # 3. Check if user exists
    db_user = db.query(User).filter(User.id == target_user_id).first()
    if not db_user:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.USER_NOT_FOUND,
            error_message="User account not found."
        )

    # 4. Check if user already checked in today (based on client_timestamp.date())
    target_date = client_timestamp.date()
    existing_log = db.query(CheckInLog).filter(
        CheckInLog.user_id == target_user_id,
        CheckInLog.check_in_date == target_date
    ).first()

    if existing_log:
        logging.info(f"eKYC Check-in rejected: User {db_user.name} (ID: {target_user_id}) already checked in on {target_date}.")
        raise AppException(
            status_code=400,
            error_code=ErrorCode.ALREADY_CHECKIN,
            error_message=f"User '{db_user.name}' has already checked in on {target_date}."
        )

    # 5. Save CheckInLog with client_timestamp
    check_in_record = CheckInLog(
        user_id=target_user_id,
        check_in_at=client_timestamp,
        check_in_date=target_date
    )
    db.add(check_in_record)
    db.commit()
    db.refresh(check_in_record)

    logging.info(f"eKYC Check-in SUCCESSFUL: User {db_user.name} (ID: {target_user_id}) checked in for {target_date} at {client_timestamp}.")
    return check_in_record
