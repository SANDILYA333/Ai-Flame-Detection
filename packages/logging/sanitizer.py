"""Secret sanitization and context scrubbing for structured logging."""

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import SecretStr

# Sensitive key identifiers that must be scrubbed from structured context.
SENSITIVE_KEY_PATTERNS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "secret_key",
        "token",
        "access_token",
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "postgres_password",
        "database_url",
        "credential",
        "credentials",
        "private_key",
    }
)

REDACTED_PLACEHOLDER = "[REDACTED]"


def is_sensitive_key(key: str) -> bool:
    """Check if a dictionary key name indicates sensitive secret data."""
    lower_key = key.lower()
    if lower_key in SENSITIVE_KEY_PATTERNS:
        return True
    patterns = ["password", "secret", "token", "api_key", "auth"]
    return any(p in lower_key for p in patterns)


def sanitize_log_data(data: Any, max_depth: int = 8) -> Any:
    """Recursively scrub sensitive keys and SecretStr instances from log payloads.

    Args:
        data: Arbitrary data structure (dict, list, primitive, SecretStr).
        max_depth: Maximum recursion depth to prevent circular reference recursion.

    Returns:
        Sanitized data structure with sensitive values replaced by '[REDACTED]'.
    """
    if max_depth <= 0:
        return "<max_depth_reached>"

    if isinstance(data, SecretStr):
        return REDACTED_PLACEHOLDER

    if isinstance(data, Mapping):
        sanitized_dict: dict[str, Any] = {}
        for k, v in data.items():
            key_str = str(k)
            if is_sensitive_key(key_str):
                sanitized_dict[key_str] = REDACTED_PLACEHOLDER
            else:
                sanitized_dict[key_str] = sanitize_log_data(v, max_depth - 1)
        return sanitized_dict

    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        return [sanitize_log_data(item, max_depth - 1) for item in data]

    return data
