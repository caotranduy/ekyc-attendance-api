import hmac
import hashlib
import datetime
import logging
from typing import Tuple
from app.core.config import config
from app.core.exceptions import AppException
from app.core.error_codes import ErrorCode

MAX_DRIFT_SECONDS = 60

def verify_hmac_signature(timestamp_str: str, nonce: str, user_id_str: str, signature: str) -> bool:
    """Verifies HMAC-SHA256 request signature calculated as:
    
    String2Sign = timestamp_str + nonce + user_id_str
    ExpectedSignature = HexEncode(HMAC-SHA256(config.SECRET_KEY, String2Sign))
    """
    if not signature:
        return False

    secret_key = getattr(config, 'SECRET_KEY')

    string_to_sign = f"{timestamp_str}{nonce}{user_id_str}"
    expected_hmac = hmac.new(
        secret_key.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_hmac.lower(), signature.lower())

def validate_client_timestamp(timestamp_str: str, max_drift_seconds: int = MAX_DRIFT_SECONDS) -> datetime.datetime:
    """Parses ISO 8601 UTC timestamp and validates that time drift relative to server UTC is <= 60s.

    Returns:
        datetime.datetime: The validated client timestamp.

    Raises:
        AppException: If parsing fails (400) or if drift exceeds max_drift_seconds (400).
    """
    if not timestamp_str:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.INVALID_REQUEST,
            error_message="Missing X-Timestamp header."
        )

    clean_str = timestamp_str.rstrip('Z')
    try:
        client_dt = datetime.datetime.fromisoformat(clean_str)
    except ValueError:
        try:
            client_dt = datetime.datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            try:
                client_dt = datetime.datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                raise AppException(
                    status_code=400,
                    error_code=ErrorCode.INVALID_REQUEST,
                    error_message=f"Invalid X-Timestamp ISO format: '{timestamp_str}'."
                )

    if client_dt.tzinfo is not None:
        client_dt = client_dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    server_now = datetime.datetime.utcnow()
    drift = abs((server_now - client_dt).total_seconds())

    if drift > max_drift_seconds:
        logging.warning(f"Timestamp drift validation failed: Client={client_dt}, Server={server_now}, Drift={drift:.2f}s > {max_drift_seconds}s")
        raise AppException(
            status_code=400,
            error_code=ErrorCode.INVALID_REQUEST,
            error_message=f"Client timestamp drift excessive ({drift:.1f}s > {max_drift_seconds}s). Please enable automatic network time (NTP) on device."
        )

    return client_dt
