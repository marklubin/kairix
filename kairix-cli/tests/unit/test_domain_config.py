"""Tests for domain configuration functionality."""

import os
from unittest import mock

import pytest

from kairix_cli.commands.users import get_kairix_domain


class TestDomainConfiguration:
    """Test domain configuration."""

    def test_get_default_domain(self):
        """Test default domain when no env var is set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            assert get_kairix_domain() == "kairix.net"

    def test_get_custom_domain_from_env(self):
        """Test custom domain from environment variable."""
        with mock.patch.dict(os.environ, {"KAIRIX_DOMAIN": "dev.kairix.net"}):
            assert get_kairix_domain() == "dev.kairix.net"

    def test_get_empty_domain_uses_default(self):
        """Test empty domain env var uses default."""
        with mock.patch.dict(os.environ, {"KAIRIX_DOMAIN": ""}):
            assert get_kairix_domain() == "kairix.net"

    @pytest.mark.parametrize(
        "domain",
        [
            "example.com",
            "test.example.com",
            "sub.domain.example.com",
            "localhost",
            "127.0.0.1.nip.io",
        ],
    )
    def test_various_domain_formats(self, domain):
        """Test various domain formats work correctly."""
        with mock.patch.dict(os.environ, {"KAIRIX_DOMAIN": domain}):
            assert get_kairix_domain() == domain
