import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from pydantic import BaseModel, Field
from app.services.face_model import face_model_instance, FaceModel
from app.services.anti_spoof_service import anti_spoof_service_instance, AntiSpoofService
from app.core.config import config

router = APIRouter(
    prefix="/test-face",
    tags=["Test Face Model & Anti-Spoofing (No DB)"]
)

def get_face_model() -> FaceModel:
    """Dependency injection for the FaceModel instance."""
    return face_model_instance

def get_anti_spoof_service() -> AntiSpoofService:
    """Dependency injection for the AntiSpoofService instance."""
    return anti_spoof_service_instance

class VerifyTestResponse(BaseModel):
    status: str = "success"
    message: str = "Face verification successful."

class RecognizeTestResponse(BaseModel):
    match: bool = Field(..., description="True if a match was found in FAISS, otherwise False.")
    face_id: Optional[uuid.UUID] = Field(None, description="The matched FAISS face UUID.")

class RegisterTestResponse(BaseModel):
    status: str = "success"
    message: str = "Face registered in FAISS successfully."
    face_id: uuid.UUID = Field(..., description="The newly generated FAISS face UUID.")

class AntiSpoofSingleResponse(BaseModel):
    liveness_score: float = Field(..., description="Real face probability score (0.0 to 1.0).")
    is_real_face: bool = Field(..., description="True if score >= threshold.")
    threshold: float = Field(..., description="Configured liveness threshold.")
    message: str = Field(..., description="Human readable result message.")

class AntiSpoof3FramesResponse(BaseModel):
    is_real: bool = Field(..., description="True if average liveness score >= threshold.")
    average_liveness_score: float = Field(..., description="Average liveness score across 3 frames.")
    threshold: float = Field(..., description="Configured liveness threshold.")
    message: str = Field(..., description="Human readable result message.")

@router.post(
    "/verify",
    response_model=VerifyTestResponse,
    summary="Verify face against FAISS UUID (Returns 200 on success, 403 on fail)"
)
async def test_verify_face_endpoint(
    file: UploadFile = File(..., description="An image file containing one face."),
    face_id: uuid.UUID = Form(..., description="The FAISS face UUID to compare against."),
    model: FaceModel = Depends(get_face_model)
):
    """
    Receives an image and a face_id, verifies directly against FAISS without database involvement.
    Returns HTTP 200 OK if matched, or HTTP 403 Forbidden if not matched.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await file.read()
        is_verified = model.verify_face(image_bytes=image_bytes, face_id_to_verify=face_id)
        
        if not is_verified:
            raise HTTPException(
                status_code=403, 
                detail="Face verification failed. The uploaded image does not match the provided face ID."
            )
        
        return VerifyTestResponse()
    except HTTPException:
        raise
    except ValueError as e:
        logging.warning(f"Verification validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred during test verification: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post(
    "/recognize",
    response_model=RecognizeTestResponse,
    summary="Recognize face and return FAISS UUID"
)
async def test_recognize_face_endpoint(
    file: UploadFile = File(..., description="An image file to search in FAISS."),
    model: FaceModel = Depends(get_face_model)
):
    """
    Receives an image, searches FAISS for the closest matching face encoding,
    and returns the matched FAISS UUID without database involvement.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await file.read()
        is_match, matched_face_id = model.recognize_face(image_bytes=image_bytes)
        return RecognizeTestResponse(match=is_match, face_id=matched_face_id)
    except ValueError as e:
        logging.warning(f"Recognition validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred during test recognition: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post(
    "/register",
    response_model=RegisterTestResponse,
    summary="Register face directly to FAISS (Helper for testing)"
)
async def test_register_face_endpoint(
    file: UploadFile = File(..., description="An image file containing one face to register in FAISS."),
    model: FaceModel = Depends(get_face_model)
):
    """
    Receives an image, registers the face directly into FAISS, and returns the generated FAISS UUID.
    This helper endpoint allows registering test faces without database involvement.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await file.read()
        registered_face = model.register_new_face(image_bytes=image_bytes)
        if registered_face.success and registered_face.face_id is not None:
            return RegisterTestResponse(face_id=registered_face.face_id)
        else:
            raise HTTPException(status_code=400, detail=registered_face.error_message)
    except HTTPException:
        raise
    except ValueError as e:
        logging.warning(f"Registration validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred during test registration: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post(
    "/anti-spoof",
    response_model=AntiSpoofSingleResponse,
    summary="Test Anti-Spoofing on a single uploaded image frame"
)
async def test_anti_spoof_single_frame_endpoint(
    file: UploadFile = File(..., description="An image frame to evaluate for liveness."),
    anti_spoof_service: AntiSpoofService = Depends(get_anti_spoof_service)
):
    """
    Evaluates anti-spoofing (passive liveness score) on a single uploaded image frame.
    Returns liveness score, pass/fail status, and threshold.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JPG or PNG image.")

    try:
        image_bytes = await file.read()
        liveness_score = anti_spoof_service.predict_single_frame(image_bytes)
        is_real = liveness_score >= config.LIVENESS_THRESHOLD
        
        msg = f"Real face detected ({liveness_score:.4f} >= {config.LIVENESS_THRESHOLD})" if is_real else f"Spoof/Fake face detected ({liveness_score:.4f} < {config.LIVENESS_THRESHOLD})"
        
        return AntiSpoofSingleResponse(
            liveness_score=round(liveness_score, 4),
            is_real_face=is_real,
            threshold=config.LIVENESS_THRESHOLD,
            message=msg
        )
    except ValueError as e:
        logging.warning(f"Anti-spoof test validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error evaluating single frame anti-spoofing: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post(
    "/anti-spoof-3-frames",
    response_model=AntiSpoof3FramesResponse,
    summary="Test eKYC Anti-Spoofing pipeline on exactly 3 uploaded image frames"
)
async def test_anti_spoof_3_frames_endpoint(
    files: List[UploadFile] = File(..., description="Exactly 3 image frames to evaluate average liveness."),
    anti_spoof_service: AntiSpoofService = Depends(get_anti_spoof_service)
):
    """
    Evaluates eKYC Anti-Spoofing pipeline on exactly 3 uploaded image frames.
    Calculates average liveness score and returns HTTP 200 with result or HTTP 403 on liveness rejection.
    """
    if len(files) != 3:
        raise HTTPException(status_code=400, detail=f"Exactly 3 image frames are required. Received {len(files)}.")

    frames_bytes = []
    for i, file in enumerate(files):
        if file.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(status_code=400, detail=f"Frame {i+1} has invalid file type. Must be JPG or PNG.")
        content = await file.read()
        frames_bytes.append(content)

    try:
        is_real, avg_score = anti_spoof_service.evaluate_liveness_frames(frames_bytes)
        
        if not is_real:
            raise HTTPException(
                status_code=403,
                detail=f"eKYC Anti-Spoofing Rejected: Average Liveness Score {avg_score:.4f} is below threshold {config.LIVENESS_THRESHOLD} (Replay/Print attack detected)."
            )

        return AntiSpoof3FramesResponse(
            is_real=is_real,
            average_liveness_score=round(avg_score, 4),
            threshold=config.LIVENESS_THRESHOLD,
            message=f"eKYC Anti-Spoofing PASSED. Average score: {avg_score:.4f} >= {config.LIVENESS_THRESHOLD}"
        )
    except HTTPException:
        raise
    except ValueError as e:
        logging.warning(f"3-Frame Anti-spoof validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error evaluating 3-frame anti-spoofing: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
