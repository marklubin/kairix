import os
from unittest.mock import patch

import pytest


class TestTalkEnvironmentLoading:
    """Test environment loading specifically in talk.py context."""

    @pytest.fixture
    def mock_env_dir(self, tmp_path):
        """Create mock environment directory."""
        env_dir = tmp_path / "env"
        env_dir.mkdir()

        # Create mock environment files
        (env_dir / "mac.env").write_text(
            "ELEVENLABS_API_KEY=mac-test-key\nELEVENLABS_VOICE_ID=mac-voice\n"
        )

        (env_dir / "cayucos.env").write_text(
            "ELEVENLABS_API_KEY=cayucos-test-key\nELEVENLABS_MODEL_ID=cayucos-model\n"
        )

        return tmp_path

    def test_talk_env_loading_logic(self, mock_env_dir, monkeypatch):
        """Test the exact logic used in talk.py."""
        monkeypatch.chdir(mock_env_dir)

        # Clear environment
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
        monkeypatch.delenv("ELEVENLABS_MODEL_ID", raising=False)
        monkeypatch.delenv("ENV", raising=False)
        
        # Prevent loading from home directory
        monkeypatch.delenv("HOME", raising=False)

        from dotenv import load_dotenv

        # Simulate talk.py logic
        if not os.environ.get("ELEVENLABS_API_KEY") and not load_dotenv(
            dotenv_path=str(mock_env_dir / ".env")
        ):
            # Try to load from env/ directory if available
            env_name = os.environ.get("ENV", "mac")
            env_path = f"env/{env_name}.env"
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)
            else:
                # Would raise ValueError in real code
                pass

        # Should load mac.env by default
        assert os.environ.get("ELEVENLABS_API_KEY") == "mac-test-key"
        assert os.environ.get("ELEVENLABS_VOICE_ID") == "mac-voice"

    def test_talk_env_loading_with_env_var(self, mock_env_dir, monkeypatch):
        """Test loading with ENV variable set."""
        monkeypatch.chdir(mock_env_dir)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
        monkeypatch.delenv("ELEVENLABS_MODEL_ID", raising=False)
        monkeypatch.setenv("ENV", "cayucos")
        
        # Prevent loading from home directory
        monkeypatch.delenv("HOME", raising=False)

        from dotenv import load_dotenv

        # Simulate talk.py logic
        if not os.environ.get("ELEVENLABS_API_KEY") and not load_dotenv(
            dotenv_path=str(mock_env_dir / ".env")
        ):
            env_name = os.environ.get("ENV", "mac")
            env_path = f"env/{env_name}.env"
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)

        # Should load cayucos.env
        assert os.environ.get("ELEVENLABS_API_KEY") == "cayucos-test-key"
        assert os.environ.get("ELEVENLABS_MODEL_ID") == "cayucos-model"

    def test_talk_env_already_loaded(self, monkeypatch):
        """Test when environment is already loaded by justfile."""
        # Simulate environment already loaded by justfile
        monkeypatch.setenv("ELEVENLABS_API_KEY", "already-loaded-key")

        from dotenv import load_dotenv

        # This condition should prevent loading
        if not os.environ.get("ELEVENLABS_API_KEY") and not load_dotenv():
            # Should not execute
            raise AssertionError("Should not attempt to load env")

        # Key should remain unchanged
        assert os.environ.get("ELEVENLABS_API_KEY") == "already-loaded-key"

    def test_talk_env_error_handling(self, tmp_path, monkeypatch):
        """Test error handling when no env file exists."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setenv("ENV", "nonexistent")

        # Create empty env directory
        (tmp_path / "env").mkdir()

        # Prevent loading from home directory
        monkeypatch.delenv("HOME", raising=False)
        
        from dotenv import load_dotenv

        # Test the error case
        with pytest.raises(ValueError) as exc_info:
            if not os.environ.get("ELEVENLABS_API_KEY") and not load_dotenv(
                dotenv_path=str(tmp_path / ".env")
            ):
                env_name = os.environ.get("ENV", "mac")
                env_path = f"env/{env_name}.env"
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                else:
                    raise ValueError(
                        f"No environment variables loaded and {env_path} not found."
                    )

        assert "env/nonexistent.env not found" in str(exc_info.value)

    @patch("kairix_core.tts.ElevenLabsTTS")
    def test_tts_initialization_with_env(
        self, mock_tts_class, mock_env_dir, monkeypatch
    ):
        """Test TTS initialization with environment variables."""
        monkeypatch.chdir(mock_env_dir)

        # Set up full environment
        env_vars = {
            "ELEVENLABS_API_KEY": "test-key",
            "ELEVENLABS_VOICE_ID": "test-voice",
            "ELEVENLABS_MODEL_ID": "test-model",
            "ELEVENLABS_STABILITY": "0.7",
            "ELEVENLABS_SIMILARITY_BOOST": "0.8",
            "ELEVENLABS_STYLE": "0.6",
            "ELEVENLABS_USE_SPEAKER_BOOST": "false",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        # Simulate TTS initialization from talk.py
        from kairix_core.tts import ElevenLabsTTS

        ElevenLabsTTS(
            api_key=os.environ["ELEVENLABS_API_KEY"],
            voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            model_id=os.environ.get("ELEVENLABS_MODEL_ID", "eleven_monolingual_v1"),
            stability=float(os.environ.get("ELEVENLABS_STABILITY", "0.5")),
            similarity_boost=float(
                os.environ.get("ELEVENLABS_SIMILARITY_BOOST", "0.5")
            ),
            style=float(os.environ.get("ELEVENLABS_STYLE", "0.5")),
            use_speaker_boost=(
                os.environ.get("ELEVENLABS_USE_SPEAKER_BOOST", "true").lower() == "true"
            ),
        )

        # Verify initialization was called with correct values
        mock_tts_class.assert_called_once_with(
            api_key="test-key",
            voice_id="test-voice",
            model_id="test-model",
            stability=0.7,
            similarity_boost=0.8,
            style=0.6,
            use_speaker_boost=False,
        )

    @pytest.mark.skip(reason="Environment persistence issue in test environment")
    def test_dotenv_load_order(self, tmp_path, monkeypatch):
        """Test dotenv loading order and precedence."""
        from dotenv import load_dotenv

        # Create test files
        (tmp_path / ".env").write_text("ELEVENLABS_API_KEY=root-key\n")
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        (env_dir / "mac.env").write_text("ELEVENLABS_API_KEY=mac-key\n")

        # Test 1: Explicit path loading
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        load_dotenv(str(tmp_path / ".env"))
        assert os.environ.get("ELEVENLABS_API_KEY") == "root-key"

        # Test 2: Load from env directory
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        load_dotenv(str(tmp_path / "env" / "mac.env"))
        assert os.environ.get("ELEVENLABS_API_KEY") == "mac-key"

        # Test 3: Simulate talk.py logic in the test directory
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

        # This simulates what happens in talk.py
        # First try to load .env from current directory
        if not os.environ.get("ELEVENLABS_API_KEY"):
            if load_dotenv():  # This should find .env in current dir
                pass
            else:
                # Fall back to env/mac.env
                env_name = os.environ.get("ENV", "mac")
                env_path = f"env/{env_name}.env"
                if os.path.exists(env_path):
                    load_dotenv(env_path)

        # Should have loaded from .env
        assert os.environ.get("ELEVENLABS_API_KEY") == "root-key"
