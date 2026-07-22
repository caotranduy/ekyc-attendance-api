from typing import Optional, Dict, Any
from fastapi import Request, Depends
from sqlalchemy.orm import Session
from app.api.deps.db_deps import get_db
from app.models.user import User

async def get_graphql_context(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Context getter for Strawberry GraphQL.
    Extracts Bearer token from request header and sets current_user in info.context.
    """
    from app.core.jwt_utils import get_optional_user_id
    user_id = get_optional_user_id(request, db=db)
    current_user: Optional[User] = None
    if user_id:
        current_user = db.query(User).filter(User.id == user_id).first()

    return {
        "request": request,
        "db": db,
        "current_user": current_user
    }
