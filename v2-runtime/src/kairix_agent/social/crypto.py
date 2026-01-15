"""Cryptographic utilities for social agent credentials.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256)
to encrypt social platform credentials at rest.

The encryption key should be a URL-safe base64-encoded 32-byte key.
Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from kairix_agent.config import Config

logger = logging.getLogger(__name__)


class CredentialEncryptionError(Exception):
    """Raised when credential encryption/decryption fails."""


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    """Get Fernet instance from CREDENTIAL_ENCRYPTION_KEY config.

    Returns:
        Configured Fernet instance for encryption/decryption

    Raises:
        CredentialEncryptionError: If encryption key is not configured
    """
    key = Config.CREDENTIAL_ENCRYPTION_KEY.value
    if not key:
        msg = (
            "CREDENTIAL_ENCRYPTION_KEY not configured. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
        raise CredentialEncryptionError(msg)

    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as e:
        msg = f"Invalid CREDENTIAL_ENCRYPTION_KEY format: {e}"
        raise CredentialEncryptionError(msg) from e


def encrypt_credentials(credentials: dict[str, Any]) -> bytes:
    """Encrypt a credentials dictionary to bytes.

    Args:
        credentials: Dictionary of credential key-value pairs
                     (e.g., {"identifier": "...", "password": "..."})

    Returns:
        Encrypted bytes suitable for database storage

    Raises:
        CredentialEncryptionError: If encryption fails
    """
    try:
        fernet = get_fernet()
        json_bytes = json.dumps(credentials).encode("utf-8")
        return fernet.encrypt(json_bytes)
    except CredentialEncryptionError:
        raise
    except Exception as e:
        msg = f"Failed to encrypt credentials: {e}"
        raise CredentialEncryptionError(msg) from e


def decrypt_credentials(encrypted: bytes) -> dict[str, Any]:
    """Decrypt bytes back to a credentials dictionary.

    Args:
        encrypted: Encrypted bytes from database

    Returns:
        Decrypted credentials dictionary

    Raises:
        CredentialEncryptionError: If decryption fails (wrong key, corrupted data)
    """
    try:
        fernet = get_fernet()
        decrypted_bytes = fernet.decrypt(encrypted)
        return json.loads(decrypted_bytes.decode("utf-8"))  # type: ignore[no-any-return]
    except InvalidToken as e:
        msg = (
            "Failed to decrypt credentials - key may have changed or data is corrupted"
        )
        raise CredentialEncryptionError(msg) from e
    except CredentialEncryptionError:
        raise
    except Exception as e:
        msg = f"Failed to decrypt credentials: {e}"
        raise CredentialEncryptionError(msg) from e
