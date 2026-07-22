import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps.db_deps import get_db
from app.models.check_in_log import CheckInLog
from app.core.jwt_utils import get_optional_user_id

router = APIRouter(
    prefix="/check-in-history",
    tags=["Mobile Attendance History"]
)

class PersonalCheckInLogDTO(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    check_in_at: datetime.datetime
    check_in_date: datetime.date

@router.get(
    "",
    response_model=List[PersonalCheckInLogDTO],
    summary="Get Attendance History for Logged-in Employee (JWT Bearer Token)"
)
def get_personal_check_in_history_mobile(
    request: Request,
    start_date: Optional[datetime.date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[datetime.date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    user_id = get_optional_user_id(request, db=db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required. Please provide a valid Bearer token.")

    query = db.query(CheckInLog).filter(CheckInLog.user_id == user_id)
    if isinstance(start_date, datetime.date):
        query = query.filter(CheckInLog.check_in_date >= start_date)
    if isinstance(end_date, datetime.date):
        query = query.filter(CheckInLog.check_in_date <= end_date)

    logs = query.order_by(CheckInLog.check_in_at.desc()).all()
    return [
        PersonalCheckInLogDTO(
            id=log.id,
            user_id=log.user_id,
            check_in_at=log.check_in_at,
            check_in_date=log.check_in_date
        )
        for log in logs
    ]
