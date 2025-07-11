"""Tests for data models."""

import pytest
from pydantic import ValidationError

from kairix_cli.models.user import User, UserConfig


class TestUser:
    """Tests for User model."""

    def test_user_creation_valid(self) -> None:
        """Test creating a valid user."""
        user = User(
            subdomain="abc",
            password_hash="$2a$14$hash",
            web_port=6010,
            api_port=7010,
            tools_port=8010,
            enabled=True,
        )

        assert user.subdomain == "abc"
        assert user.password_hash == "$2a$14$hash"
        assert user.web_port == 6010
        assert user.api_port == 7010
        assert user.tools_port == 8010
        assert user.enabled is True

    def test_user_subdomain_validation(self) -> None:
        """Test subdomain validation."""
        # Valid subdomains
        valid_subdomains = ["abc", "123", "a1b", "x9z"]
        for subdomain in valid_subdomains:
            user = User(
                subdomain=subdomain,
                password_hash="hash",
                web_port=6010,
                api_port=7010,
                tools_port=8010,
            )
            assert user.subdomain == subdomain

        # Invalid subdomains
        invalid_subdomains = ["ab", "abcd", "ABC", "a-b", "a_b", ""]
        for subdomain in invalid_subdomains:
            with pytest.raises(ValidationError):
                User(
                    subdomain=subdomain,
                    password_hash="hash",
                    web_port=6010,
                    api_port=7010,
                    tools_port=8010,
                )

    def test_user_port_validation(self) -> None:
        """Test port number validation."""
        # Valid ports
        user = User(
            subdomain="abc",
            password_hash="hash",
            web_port=1024,
            api_port=65535,
            tools_port=8080,
        )
        assert user.web_port == 1024
        assert user.api_port == 65535

        # Invalid ports - too low
        with pytest.raises(ValidationError):
            User(
                subdomain="abc",
                password_hash="hash",
                web_port=1023,
                api_port=7010,
                tools_port=8010,
            )

        # Invalid ports - too high
        with pytest.raises(ValidationError):
            User(
                subdomain="abc",
                password_hash="hash",
                web_port=6010,
                api_port=65536,
                tools_port=8010,
            )

    def test_user_default_enabled(self) -> None:
        """Test that enabled defaults to True."""
        user = User(
            subdomain="abc",
            password_hash="hash",
            web_port=6010,
            api_port=7010,
            tools_port=8010,
        )
        assert user.enabled is True

    def test_user_model_dump(self) -> None:
        """Test model serialization."""
        user = User(
            subdomain="abc",
            password_hash="hash",
            web_port=6010,
            api_port=7010,
            tools_port=8010,
            enabled=False,
        )

        data = user.model_dump()

        assert data == {
            "subdomain": "abc",
            "password_hash": "hash",
            "web_port": 6010,
            "api_port": 7010,
            "tools_port": 8010,
            "enabled": False,
        }

    def test_user_validate_assignment(self) -> None:
        """Test that assignment validation is enabled."""
        user = User(
            subdomain="abc",
            password_hash="hash",
            web_port=6010,
            api_port=7010,
            tools_port=8010,
        )

        # Should raise error when assigning invalid value
        with pytest.raises(ValidationError):
            user.subdomain = "invalid-subdomain"


class TestUserConfig:
    """Tests for UserConfig model."""

    def test_user_config_creation(self, sample_user: User) -> None:
        """Test creating a user configuration."""
        config = UserConfig(
            username="testuser",
            user=sample_user,
            sqlite_path="/var/kairix/users/testuser/sqlite/kairix.db",
        )

        assert config.username == "testuser"
        assert config.user == sample_user
        assert config.sqlite_path == "/var/kairix/users/testuser/sqlite/kairix.db"
        assert config.environment == {}

    def test_user_config_with_environment(self, sample_user: User) -> None:
        """Test user config with environment variables."""
        env = {"API_KEY": "secret", "DEBUG": "true"}
        config = UserConfig(
            username="testuser",
            user=sample_user,
            sqlite_path="/path/to/db",
            environment=env,
        )

        assert config.environment == env

    def test_user_config_model_dump(self, sample_user: User) -> None:
        """Test UserConfig serialization."""
        config = UserConfig(
            username="testuser",
            user=sample_user,
            sqlite_path="/path/to/db",
            environment={"KEY": "value"},
        )

        data = config.model_dump()

        assert data["username"] == "testuser"
        assert data["sqlite_path"] == "/path/to/db"
        assert data["environment"] == {"KEY": "value"}
        assert data["user"]["subdomain"] == "abc"
