from typing import Optional
from pydantic import BaseModel, Field
import uuid

class RegisterSuccessResponse(BaseModel):
    """Defines the successful registration response schema."""
    status: str = "success"
    message: str = "User registered successfully."
    user_id: uuid.UUID = Field(..., description="The unique ID assigned to the new user.")

    class Config:
        # Example for documentation
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "User registered successfully.",
                "user_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }

class RecognizeResponse(BaseModel):
    """Defines the recognition response schema."""
    match: bool = Field(..., description="True if a match was found, otherwise False.")
    user_id: Optional[uuid.UUID] = Field(None, description="The unique ID of the matched user. Null if no match.")

    class Config:
        json_schema_extra = {
            "example": {
                "match": True,
                "user_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }

class VerifyResponse(BaseModel):
    """Defines the verification response schema."""
    verified: bool = Field(..., description="True if the face matches the given face_id.")

    class Config:
        json_schema_extra = {
            "example": {
                "verified": True
            }
        }        