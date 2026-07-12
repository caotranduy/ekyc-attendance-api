import pytest
import uuid6 as uuid
import numpy as np
from unittest.mock import patch, MagicMock
from app.models.face_model import FaceModel, RegistrationResult

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

@patch('app.models.face_model.cv2.imwrite')
@patch.object(FaceModel, '_get_single_face_encoding')
@patch('app.models.face_model.uuid.uuid7')
def test_register_new_face_success(
    mock_uuid4: MagicMock,
    mock_get_encoding: MagicMock,
    mock_imwrite: MagicMock,
    mock_face_model: FaceModel
) -> None:
    """Verifies that a valid face payload properly updates FAISS and mapping.

    Args:
        mock_uuid4: Mocked UUID generator.
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
    mock_uuid4.return_value = expected_uuid

    # 2. ACT
    result = mock_face_model.register_new_face(fake_image_bytes)

    # 3. ASSERT
    assert isinstance(result, RegistrationResult)
    assert result.success is True
    assert result.face_id == expected_uuid

    mock_get_encoding.assert_called_once_with(fake_image_bytes)
    mock_face_model.index.add.assert_called_once()
    mock_face_model._save_index_and_mapping.assert_called_once()
    mock_imwrite.assert_called_once()

    assert expected_uuid in mock_face_model.uuid_mapping
    assert mock_face_model.uuid_to_index[expected_uuid] == 5