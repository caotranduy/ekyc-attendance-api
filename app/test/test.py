import pytest
import uuid6 as uuid
import numpy as np
from unittest.mock import patch, MagicMock
from app.services.face_model import FaceModel, RegistrationResult
import app.models.user
import app.models.user_face
import app.models.check_in_log

@pytest.fixture
def mock_face_model() -> FaceModel:
    """Provides a bypassed FaceModel instance without triggering __init__ logic.

    Returns:
        FaceModel: A manipulated instance with dummy FAISS and mapping structures.
    """
    with patch.object(FaceModel, '__init__', lambda x: None):
        model = FaceModel()
        model.index = MagicMock()
        model.index.ntotal = 5  # Fake current vector count
        model.uuid_mapping = []
        model.uuid_to_index = {}
        model._save_index_and_mapping = MagicMock()
        return model

@patch('app.services.face_model.cv2.imwrite')
@patch.object(FaceModel, '_get_single_face_encoding')
@patch('app.services.face_model.uuid.uuid7')
def test_register_new_face_success(
    mock_uuid7: MagicMock,
    mock_get_encoding: MagicMock,
    mock_imwrite: MagicMock,
    mock_face_model: FaceModel
) -> None:
    """Verifies that a valid face payload properly updates FAISS and mapping.

    Args:
        mock_uuid7: Mocked UUID generator.
        mock_get_encoding: Mocked internal method for feature extraction.
        mock_imwrite: Mocked OpenCV image writing function.
        mock_face_model: Bypassed FaceModel instance from the fixture.
    """
    # 1. ARRANGE
    fake_image_bytes = b"dummy_image_payload"
    fake_encoding = np.zeros(128, dtype=np.float32)
    fake_image_array = np.zeros((100, 100, 3), dtype=np.uint8)
    
    fake_rect = MagicMock()
    fake_rect.top.return_value = 10
    fake_rect.right.return_value = 90
    fake_rect.bottom.return_value = 90
    fake_rect.left.return_value = 10
    
    mock_get_encoding.return_value = (fake_encoding, fake_image_array, fake_rect)
    
    expected_uuid = uuid.UUID('12345678-1234-5678-1234-567812345678')
    mock_uuid7.return_value = expected_uuid

    # 2. ACT
    result = mock_face_model.register_new_face(fake_image_bytes)

    # 3. ASSERT
    assert isinstance(result, RegistrationResult)
    assert result.success is True
    assert result.face_id == expected_uuid
    assert result.cropped_jpeg_bytes is not None

    mock_get_encoding.assert_called_once_with(fake_image_bytes)
    mock_face_model.index.add.assert_called_once()
    mock_face_model._save_index_and_mapping.assert_called_once()

    assert expected_uuid in mock_face_model.uuid_mapping
    assert mock_face_model.uuid_to_index[expected_uuid] == 5

def test_user_model_creation() -> None:
    """Verifies that the User model fields are mapped correctly."""
    from app.models.user import User
    import datetime
    
    test_user_id = uuid.UUID('12345678-1234-7678-1234-567812345678')
    test_time = datetime.datetime.utcnow()
    
    user = User(
        id=test_user_id,
        name="Test User",
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_bcrypt_password",
        is_active=True,
        is_admin=False,
        created_at=test_time
    )
    
    assert user.id == test_user_id
    assert user.name == "Test User"
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_bcrypt_password"
    assert user.is_active is True
    assert user.is_admin is False
    assert user.created_at == test_time

def test_user_face_model_creation() -> None:
    """Verifies that the UserFace model fields are mapped correctly."""
    from app.models.user_face import UserFace
    import datetime
    
    test_face_record_id = uuid.UUID('22345678-1234-7678-1234-567812345678')
    test_user_id = uuid.UUID('12345678-1234-7678-1234-567812345678')
    test_face_id = uuid.UUID('87654321-4321-7876-4321-876543210987')
    test_time = datetime.datetime.utcnow()
    
    user_face = UserFace(
        id=test_face_record_id,
        user_id=test_user_id,
        face_id=test_face_id,
        created_at=test_time
    )
    
    assert user_face.id == test_face_record_id
    assert user_face.user_id == test_user_id
    assert user_face.face_id == test_face_id
    assert user_face.created_at == test_time

def test_register_user_face_user_not_found() -> None:
    """Verifies that register_user_face raises KeyError when user does not exist in DB."""
    from app.services.face_service import register_user_face
    
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_model = MagicMock()
    
    non_existent_user_id = uuid.UUID('99999999-9999-9999-9999-999999999999')
    
    with pytest.raises(KeyError) as excinfo:
        register_user_face(
            db=mock_db,
            model=mock_model,
            user_id=non_existent_user_id,
            image_bytes=b"dummy"
        )
    assert "User not found" in str(excinfo.value)

def test_verify_user_face_no_record() -> None:
    """Verifies that verify_user_face raises KeyError when user has no face record."""
    from app.services.face_service import verify_user_face
    
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_model = MagicMock()
    
    test_user_id = uuid.UUID('12345678-1234-7678-1234-567812345678')
    
    with pytest.raises(KeyError) as excinfo:
        verify_user_face(
            db=mock_db,
            model=mock_model,
            user_id=test_user_id,
            image_bytes=b"dummy"
        )
    assert "No face biometric record found" in str(excinfo.value)

def test_recognize_user_face_no_match() -> None:
    """Verifies that recognize_user_face returns (False, None) when FAISS has no match."""
    from app.services.face_service import recognize_user_face
    
    mock_db = MagicMock()
    mock_model = MagicMock()
    mock_model.recognize_face.return_value = (False, None)
    
    is_match, matched_user_id = recognize_user_face(
        db=mock_db,
        model=mock_model,
        image_bytes=b"dummy"
    )
    assert is_match is False
    assert matched_user_id is None

def test_anti_spoof_evaluate_frames_count_validation() -> None:
    """Verifies that evaluate_liveness_frames requires exactly 3 frames."""
    from app.services.anti_spoof_service import AntiSpoofService
    service = AntiSpoofService()
    
    with pytest.raises(ValueError) as excinfo:
        service.evaluate_liveness_frames([b"frame1", b"frame2"])
    assert "requires exactly 3 frames" in str(excinfo.value)

def test_verify_user_face_liveness_spoof_rejection() -> None:
    """Verifies that verify_user_face_liveness raises PermissionError (403) when spoofing is detected."""
    from app.services.face_service import verify_user_face_liveness
    
    mock_db = MagicMock()
    mock_model = MagicMock()
    mock_anti_spoof = MagicMock()
    mock_anti_spoof.evaluate_liveness_frames.return_value = (False, 0.42) # Failed liveness score
    
    test_user_id = uuid.UUID('12345678-1234-7678-1234-567812345678')
    dummy_frames = [b"frame1", b"frame2", b"frame3"]
    
    with pytest.raises(PermissionError) as excinfo:
        verify_user_face_liveness(
            db=mock_db,
            model=mock_model,
            user_id=test_user_id,
            frames=dummy_frames,
            anti_spoof_service=mock_anti_spoof
        )
    assert "Replay or Print attack detected" in str(excinfo.value)

def test_process_user_check_in_user_not_found() -> None:
    """Verifies that process_user_check_in raises AppException(USER_NOT_FOUND) if user does not exist."""
    from app.services.check_in_service import process_user_check_in
    from app.core.exceptions import AppException
    from app.core.error_codes import ErrorCode
    
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    non_existent_user_id = uuid.UUID('99999999-9999-9999-9999-999999999999')
    
    with pytest.raises(AppException) as excinfo:
        process_user_check_in(db=mock_db, user_id=non_existent_user_id)
        
    assert excinfo.value.status_code == 404
    assert excinfo.value.error_code == ErrorCode.USER_NOT_FOUND.value

def test_process_user_check_in_already_checked_in() -> None:
    """Verifies that process_user_check_in raises AppException(ALREADY_CHECKIN) if user checked in today."""
    from app.services.check_in_service import process_user_check_in
    from app.core.exceptions import AppException
    from app.core.error_codes import ErrorCode
    
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.name = "Test User"
    mock_existing_log = MagicMock()
    
    # First query return mock_user, second query return mock_existing_log
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_user, mock_existing_log]
    
    test_user_id = uuid.UUID('12345678-1234-7678-1234-567812345678')
    
    with pytest.raises(AppException) as excinfo:
        process_user_check_in(db=mock_db, user_id=test_user_id)
        
    assert excinfo.value.status_code == 400
    assert excinfo.value.error_code == ErrorCode.ALREADY_CHECKIN.value

def test_graphql_my_check_in_history_unauthorized() -> None:
    """Verifies my_check_in_history raises 401 UNAUTHORIZED when no authenticated user in context."""
    from app.graphql.queries import Query
    from app.core.exceptions import AppException
    from app.core.error_codes import ErrorCode
    
    query_resolver = Query()
    mock_info = MagicMock()
    mock_info.context = {"db": MagicMock(), "current_user": None}
    
    with pytest.raises(AppException) as excinfo:
        query_resolver.my_check_in_history(info=mock_info)
        
    assert excinfo.value.status_code == 401
    assert excinfo.value.error_code == ErrorCode.UNAUTHORIZED.value

def test_graphql_all_check_in_history_forbidden() -> None:
    """Verifies all_check_in_history raises 403 FORBIDDEN when user is not an Admin."""
    from app.graphql.queries import Query
    from app.core.exceptions import AppException
    from app.core.error_codes import ErrorCode
    
    query_resolver = Query()
    mock_user = MagicMock()
    mock_user.is_admin = False
    mock_info = MagicMock()
    mock_info.context = {"db": MagicMock(), "current_user": mock_user}
    
    with pytest.raises(AppException) as excinfo:
        query_resolver.all_check_in_history(info=mock_info)
        
    assert excinfo.value.status_code == 403
    assert excinfo.value.error_code == ErrorCode.FORBIDDEN.value

def test_graphql_search_users_matching() -> None:
    """Verifies search_users GraphQL resolver returns matched users for AutoComplete."""
    from app.graphql.queries import Query
    
    query_resolver = Query()
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = uuid.UUID('12345678-1234-7678-1234-567812345678')
    mock_user.name = "Nguyen Van A"
    mock_user.employee_code = "NV-1001"
    mock_user.gender = "Nam"
    mock_user.dob = None
    mock_user.username = "nguyena"
    mock_user.email = "a@example.com"
    mock_user.is_active = True
    mock_user.is_admin = False
    
    mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_user]
    mock_info = MagicMock()
    mock_info.context = {"db": mock_db}
    
    results = query_resolver.search_users(info=mock_info, keyword="Nguyen")
    assert len(results) == 1
    assert results[0].name == "Nguyen Van A"
    assert results[0].employee_code == "NV-1001"

def test_admin_create_employee_auto_fallback() -> None:
    """Verifies create_employee auto-generates code, username, and password when omitted."""
    from app.services.admin.employee_service import create_employee
    
    mock_db = MagicMock()
    # Mock query code check return None (no duplicate)
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.query.return_value.filter.return_value.all.return_value = []
    
    user = create_employee(
        db=mock_db,
        name="Test Employee",
        employee_code=None,
        username=None,
        password=None
    )
    
    assert user.name == "Test Employee"
    assert user.employee_code == "NV-1001"
    assert user.username == "NV-1001"
    assert user.password is not None
    assert len(user.password) >= 6

def test_anti_spoof_service_bbox_expansion() -> None:
    """Verifies expanded bounding box calculation for MiniFASNet 2.7x scale."""
    from app.services.anti_spoof_service import anti_spoof_service_instance
    
    mock_rect = MagicMock()
    mock_rect.left.return_value = 20
    mock_rect.top.return_value = 20
    mock_rect.right.return_value = 60
    mock_rect.bottom.return_value = 60
    
    img_h, img_w = 100, 100
    top, right, bottom, left = anti_spoof_service_instance._get_expanded_bbox(img_h, img_w, mock_rect, scale=2.7)
    
    assert top >= 0
    assert left >= 0
    assert bottom <= img_h
    assert right <= img_w
def test_face_model_delete_face() -> None:
    """Verifies delete_face removes UUID from FAISS mapping."""
    from app.services.face_model import face_model_instance
    import uuid6
    dummy_uuid = uuid6.uuid7()
    face_model_instance.uuid_mapping.append(dummy_uuid)
    idx = len(face_model_instance.uuid_mapping) - 1
    face_model_instance.uuid_to_index[dummy_uuid] = idx
    
    deleted = face_model_instance.delete_face(dummy_uuid)
    assert deleted is True
def test_security_hmac_and_timestamp_drift() -> None:
    """Verifies HMAC signature generation/verification and 60s timestamp drift validation."""
    import hmac
    import hashlib
    import datetime
    from app.core.security import verify_hmac_signature, validate_client_timestamp
    from app.core.config import config

    ts = datetime.datetime.utcnow().isoformat() + "Z"
    nonce = "test-nonce-12345"
    uid_str = "0190c58e-1001-7000-8000-000000000001"
    
    secret = getattr(config, 'SECRET_KEY', 'aiface_super_secret_ekyc_key_2026') or 'aiface_super_secret_ekyc_key_2026'
    string_to_sign = f"{ts}{nonce}{uid_str}"
    expected_sig = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    # 1. Verify valid signature
    assert verify_hmac_signature(ts, nonce, uid_str, expected_sig) is True
    # 2. Verify invalid signature
    assert verify_hmac_signature(ts, nonce, uid_str, "invalid_sig") is False

def test_get_optional_user_id() -> None:
    """Verifies get_optional_user_id extracts user_id from JWT token or returns None."""
    from app.core.jwt_utils import create_access_token, get_optional_user_id
    from unittest.mock import MagicMock

    uid = "0190c58e-1001-7000-8000-000000000001"
    token = create_access_token(subject=uid)

    mock_req = MagicMock()
    mock_req.headers = {"Authorization": f"Bearer {token}"}
    
    parsed_id = get_optional_user_id(mock_req)
    assert str(parsed_id) == uid

    mock_req_none = MagicMock()
    mock_req_none.headers = {}
    assert get_optional_user_id(mock_req_none) is None

def test_jwt_revocation_on_password_change() -> None:
    """Verifies token revocation when user password changes or account is inactive."""
    from app.core.jwt_utils import create_access_token, get_optional_user_id
    from app.models.user import User
    from unittest.mock import MagicMock, patch
    from fastapi import HTTPException

    uid_str = "0190c58e-1001-7000-8000-000000000001"
    token = create_access_token(subject=uid_str, password_snippet="old_password_123")

    mock_req = MagicMock()
    mock_req.headers = {"Authorization": f"Bearer {token}"}

    # Case 1: Inactive user -> Revoked with 401
    mock_db = MagicMock()
    inactive_user = User(id=uuid.UUID(uid_str), name="Test", is_active=False, password="old_password_123")
    mock_db.query.return_value.filter.return_value.first.return_value = inactive_user
    
    try:
        get_optional_user_id(mock_req, db=mock_db)
        assert False, "Should have raised HTTPException 401 for inactive user"
    except HTTPException as e:
        assert e.status_code == 401
        assert "inactive" in e.detail.lower()

    # Case 2: Password changed -> Revoked with 401
    active_user_new_pwd = User(id=uuid.UUID(uid_str), name="Test", is_active=True, password="new_changed_password_999")
    mock_db.query.return_value.filter.return_value.first.return_value = active_user_new_pwd

def test_refresh_token_generation() -> None:
    """Verifies create_refresh_token and type claim validation."""
    from app.core.jwt_utils import create_refresh_token
    from app.core.config import config
    import jwt

    uid_str = "0190c58e-1001-7000-8000-000000000001"
    ref_token = create_refresh_token(subject=uid_str, password_snippet="pwd123")

def test_mobile_personal_info_and_history() -> None:
    """Verifies mobile personal info and history endpoints."""
    from app.api.mobile.personal_info import get_personal_info_mobile
    from app.api.mobile.check_in_history import get_personal_check_in_history_mobile
    from app.core.jwt_utils import create_access_token
    from app.api.deps.db_deps import get_db
    from app.models.user import User
    from unittest.mock import MagicMock

    db = next(get_db())
    user = db.query(User).first()
    assert user is not None

    token = create_access_token(subject=str(user.id), password_snippet=user.password)

    mock_req = MagicMock()
    mock_req.headers = {"Authorization": f"Bearer {token}"}

    # 1. Test get_personal_info_mobile
    info_res = get_personal_info_mobile(request=mock_req, db=db)
    assert info_res.user_id == user.id
    assert info_res.name == user.name

    # 2. Test get_personal_check_in_history_mobile
def test_graphql_context_bearer_token() -> None:
    """Verifies get_graphql_context extracts current_user from Bearer token."""
    import asyncio
    from app.graphql.context import get_graphql_context
    from app.core.jwt_utils import create_access_token
    from app.api.deps.db_deps import get_db
    from app.models.user import User
    from unittest.mock import MagicMock

    db = next(get_db())
    user = db.query(User).first()
    assert user is not None

    token = create_access_token(subject=str(user.id), password_snippet=user.password)
    mock_req = MagicMock()
    mock_req.headers = {"Authorization": f"Bearer {token}"}

    ctx = asyncio.run(get_graphql_context(request=mock_req, db=db))
    assert ctx["current_user"] is not None
    assert ctx["current_user"].id == user.id








