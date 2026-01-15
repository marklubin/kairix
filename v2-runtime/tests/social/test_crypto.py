"""Tests for social credential encryption."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from kairix_agent.social.crypto import (
    CredentialEncryptionError,
    decrypt_credentials,
    encrypt_credentials,
    get_fernet,
)


class TestGetFernet:
    """Tests for get_fernet function."""

    def test_get_fernet_with_valid_key(self) -> None:
        """Should return Fernet instance with valid key."""
        valid_key = Fernet.generate_key().decode()

        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = valid_key
            # Clear LRU cache to ensure fresh call
            get_fernet.cache_clear()

            fernet = get_fernet()

            assert isinstance(fernet, Fernet)

    def test_get_fernet_without_key_raises(self) -> None:
        """Should raise error when key not configured."""
        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = None
            get_fernet.cache_clear()

            with pytest.raises(CredentialEncryptionError) as exc_info:
                get_fernet()

            assert "CREDENTIAL_ENCRYPTION_KEY not configured" in str(exc_info.value)

    def test_get_fernet_with_empty_key_raises(self) -> None:
        """Should raise error when key is empty string."""
        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = ""
            get_fernet.cache_clear()

            with pytest.raises(CredentialEncryptionError) as exc_info:
                get_fernet()

            assert "CREDENTIAL_ENCRYPTION_KEY not configured" in str(exc_info.value)

    def test_get_fernet_with_invalid_key_raises(self) -> None:
        """Should raise error when key format is invalid."""
        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = "not-a-valid-fernet-key"
            get_fernet.cache_clear()

            with pytest.raises(CredentialEncryptionError) as exc_info:
                get_fernet()

            assert "Invalid CREDENTIAL_ENCRYPTION_KEY format" in str(exc_info.value)


class TestEncryptDecryptRoundtrip:
    """Tests for credential encryption/decryption."""

    @pytest.fixture(autouse=True)
    def setup_fernet(self) -> None:
        """Set up valid encryption key for tests."""
        self.valid_key = Fernet.generate_key().decode()
        self.patcher = patch("kairix_agent.social.crypto.Config")
        self.mock_config = self.patcher.start()
        self.mock_config.CREDENTIAL_ENCRYPTION_KEY.value = self.valid_key
        get_fernet.cache_clear()

    def teardown_method(self) -> None:
        """Clean up patches."""
        self.patcher.stop()
        get_fernet.cache_clear()

    def test_encrypt_decrypt_roundtrip_simple(self) -> None:
        """Should encrypt and decrypt credentials back to original."""
        credentials = {"identifier": "user.bsky.social", "password": "secret123"}

        encrypted = encrypt_credentials(credentials)
        decrypted = decrypt_credentials(encrypted)

        assert decrypted == credentials

    def test_encrypt_decrypt_roundtrip_complex(self) -> None:
        """Should handle complex credential structures."""
        credentials = {
            "identifier": "user@example.com",
            "password": "complex-P@ssw0rd!",
            "app_password": "xxxx-xxxx-xxxx-xxxx",
            "extra_config": {
                "timeout": 30,
                "retry": True,
            },
        }

        encrypted = encrypt_credentials(credentials)
        decrypted = decrypt_credentials(encrypted)

        assert decrypted == credentials

    def test_encrypt_decrypt_roundtrip_unicode(self) -> None:
        """Should handle unicode characters in credentials."""
        credentials = {"identifier": "用户名", "password": "пароль🔐"}

        encrypted = encrypt_credentials(credentials)
        decrypted = decrypt_credentials(encrypted)

        assert decrypted == credentials

    def test_encrypt_decrypt_empty_dict(self) -> None:
        """Should handle empty credentials dict."""
        credentials: dict[str, str] = {}

        encrypted = encrypt_credentials(credentials)
        decrypted = decrypt_credentials(encrypted)

        assert decrypted == credentials

    def test_encrypted_data_is_bytes(self) -> None:
        """Encrypted output should be bytes."""
        credentials = {"password": "test"}

        encrypted = encrypt_credentials(credentials)

        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0

    def test_encrypted_data_is_different_from_plaintext(self) -> None:
        """Encrypted data should not contain plaintext."""
        password = "super_secret_password"
        credentials = {"password": password}

        encrypted = encrypt_credentials(credentials)

        assert password.encode() not in encrypted

    def test_same_credentials_produce_different_ciphertext(self) -> None:
        """Fernet uses random IV, so same input produces different output."""
        credentials = {"password": "test"}

        encrypted1 = encrypt_credentials(credentials)
        encrypted2 = encrypt_credentials(credentials)

        # Both decrypt to same value
        assert decrypt_credentials(encrypted1) == credentials
        assert decrypt_credentials(encrypted2) == credentials
        # But ciphertext is different (due to random IV)
        assert encrypted1 != encrypted2


class TestDecryptWithWrongKey:
    """Tests for decryption failure scenarios."""

    def test_decrypt_with_different_key_fails(self) -> None:
        """Should fail to decrypt when key changes."""
        # Encrypt with one key
        key1 = Fernet.generate_key().decode()
        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = key1
            get_fernet.cache_clear()
            encrypted = encrypt_credentials({"password": "secret"})

        # Try to decrypt with different key
        key2 = Fernet.generate_key().decode()
        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = key2
            get_fernet.cache_clear()

            with pytest.raises(CredentialEncryptionError) as exc_info:
                decrypt_credentials(encrypted)

            assert "key may have changed or data is corrupted" in str(exc_info.value)

    def test_decrypt_corrupted_data_fails(self) -> None:
        """Should fail to decrypt corrupted data."""
        key = Fernet.generate_key().decode()
        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = key
            get_fernet.cache_clear()

            encrypted = encrypt_credentials({"password": "secret"})
            # Corrupt the data
            corrupted = encrypted[:-10] + b"corrupted!"

            with pytest.raises(CredentialEncryptionError):
                decrypt_credentials(corrupted)

    def test_decrypt_random_bytes_fails(self) -> None:
        """Should fail to decrypt random bytes."""
        key = Fernet.generate_key().decode()
        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = key
            get_fernet.cache_clear()

            with pytest.raises(CredentialEncryptionError):
                decrypt_credentials(b"random bytes that are not encrypted")


class TestEncryptCredentialsErrors:
    """Tests for encryption error handling."""

    def test_encrypt_without_key_raises(self) -> None:
        """Should raise when trying to encrypt without key configured."""
        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = None
            get_fernet.cache_clear()

            with pytest.raises(CredentialEncryptionError):
                encrypt_credentials({"password": "test"})
