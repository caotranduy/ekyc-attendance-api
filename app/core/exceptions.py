from typing import Union
from app.core.error_codes import ErrorCode

class AppException(Exception):
    """Custom Application Exception carrying HTTP status code, error code enum, and message."""
    def __init__(self, status_code: int, error_code: Union[ErrorCode, str], error_message: str):
        self.status_code = status_code
        self.error_code = error_code.value if isinstance(error_code, ErrorCode) else error_code
        self.error_message = error_message
        super().__init__(self.error_message)
