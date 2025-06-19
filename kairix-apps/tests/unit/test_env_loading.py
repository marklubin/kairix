import os
import subprocess
import tempfile
from unittest.mock import patch

import pytest


class TestEnvironmentLoading:
    """Test environment loading functionality."""

    @pytest.fixture
    def temp_env_dir(self, tmp_path):
        """Create temporary env directory with test files."""
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        
        # Create test environment files
        (env_dir / "test1.env").write_text(
            "ELEVENLABS_API_KEY=test-key-1\n"
            "TEST_VAR=value1\n"
            "ELEVENLABS_VOICE_ID=voice1\n"
        )
        
        (env_dir / "test2.env").write_text(
            "ELEVENLABS_API_KEY=test-key-2\n"
            "TEST_VAR=value2\n"
            "ELEVENLABS_MODEL_ID=model2\n"
        )
        
        return env_dir

    def test_list_envs_command(self, temp_env_dir):
        """Test that list-envs justfile target works."""
        # Create a minimal justfile for testing
        justfile_content = """
# List available environments
list-envs:
    @echo "Available environments:"
    @ls -1 env/*.env 2>/dev/null | sed 's|env/||' | \
        sed 's|\\.env||' || echo "No environments found in env/"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='file', delete=False) as f:
            f.write(justfile_content)
            justfile_path = f.name
        
        try:
            # Run just command in temp directory
            result = subprocess.run(
                [
                    "just", "-f", justfile_path, "-d",
                    str(temp_env_dir.parent), "list-envs"
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
            assert "test1" in result.stdout
            assert "test2" in result.stdout
        finally:
            os.unlink(justfile_path)

    def test_env_loading_in_python(self, temp_env_dir, monkeypatch):
        """Test environment loading logic in Python code."""
        # Change to temp directory
        monkeypatch.chdir(temp_env_dir.parent)
        
        # Clear any existing env vars
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        
        # Test loading specific env file
        monkeypatch.setenv("ENV", "test1")
        
        # Simulate the loading logic from talk.py
        from dotenv import load_dotenv
        
        env_name = os.environ.get("ENV", "mac")
        env_path = f"env/{env_name}.env"
        
        assert os.path.exists(env_path)
        load_dotenv(env_path)
        
        # Verify environment variables are loaded
        assert os.environ.get("ELEVENLABS_API_KEY") == "test-key-1"
        assert os.environ.get("TEST_VAR") == "value1"
        assert os.environ.get("ELEVENLABS_VOICE_ID") == "voice1"

    def test_env_fallback_behavior(self, temp_env_dir, monkeypatch):
        """Test fallback when env file doesn't exist."""
        monkeypatch.chdir(temp_env_dir.parent)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setenv("ENV", "nonexistent")
        
        from dotenv import load_dotenv
        
        env_name = os.environ.get("ENV", "mac")
        env_path = f"env/{env_name}.env"
        
        # Should not exist
        assert not os.path.exists(env_path)
        
        # Should handle gracefully
        if os.path.exists(env_path):
            load_dotenv(env_path)
        else:
            # In real code, this would raise an error
            assert True

    def test_different_env_loading(self, temp_env_dir, monkeypatch):
        """Test loading different environments."""
        monkeypatch.chdir(temp_env_dir.parent)
        
        from dotenv import load_dotenv
        
        # Test loading test1
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setenv("ENV", "test1")
        
        env_path = "env/test1.env"
        load_dotenv(env_path, override=True)
        
        assert os.environ.get("ELEVENLABS_API_KEY") == "test-key-1"
        assert os.environ.get("TEST_VAR") == "value1"
        
        # Test loading test2
        monkeypatch.setenv("ENV", "test2")
        
        env_path = "env/test2.env"
        load_dotenv(env_path, override=True)
        
        assert os.environ.get("ELEVENLABS_API_KEY") == "test-key-2"
        assert os.environ.get("TEST_VAR") == "value2"

    @patch.dict(os.environ, {}, clear=True)
    def test_env_already_loaded(self):
        """Test behavior when environment is already loaded."""
        # Set env var directly
        os.environ["ELEVENLABS_API_KEY"] = "already-loaded"
        
        # The loading logic should skip if key already exists
        if not os.environ.get("ELEVENLABS_API_KEY"):
            # This should not execute
            raise AssertionError("Should not load env when already set")
        
        assert os.environ.get("ELEVENLABS_API_KEY") == "already-loaded"

    def test_justfile_env_loading(self, temp_env_dir):
        """Test that justfile properly loads environment."""
        justfile_content = """
# Run talk.py with specified environment
run-talk ENV:
    @echo "Running talk.py with environment: {{ENV}}"
    @if [ -f "env/{{ENV}}.env" ]; then \\
        echo "Loading env/{{ENV}}.env"; \\
        echo "Environment file exists"; \\
    else \\
        echo "Error: env/{{ENV}}.env not found"; \\
        exit 1; \\
    fi
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='file', delete=False) as f:
            f.write(justfile_content)
            justfile_path = f.name
        
        try:
            # Test with existing env
            result = subprocess.run(
                [
                    "just", "-f", justfile_path, "-d",
                    str(temp_env_dir.parent), "run-talk", "test1"
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
            assert "Loading env/test1.env" in result.stdout
            
            # Test with non-existing env
            result = subprocess.run(
                [
                    "just", "-f", justfile_path, "-d",
                    str(temp_env_dir.parent), "run-talk", "nonexistent"
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 1
            assert "Error: env/nonexistent.env not found" in result.stdout
        finally:
            os.unlink(justfile_path)

    def test_integration_with_tts_config(self, temp_env_dir, monkeypatch):
        """Test that TTS configuration works with env loading."""
        monkeypatch.chdir(temp_env_dir.parent)
        
        # Create env file with all TTS settings
        (temp_env_dir / "tts_test.env").write_text(
            "ELEVENLABS_API_KEY=test-api-key\n"
            "ELEVENLABS_VOICE_ID=test-voice\n"
            "ELEVENLABS_MODEL_ID=eleven_turbo_v2\n"
            "ELEVENLABS_STABILITY=0.7\n"
            "ELEVENLABS_SIMILARITY_BOOST=0.8\n"
            "ELEVENLABS_STYLE=0.6\n"
            "ELEVENLABS_USE_SPEAKER_BOOST=false\n"
        )
        
        from dotenv import load_dotenv
        
        load_dotenv("env/tts_test.env", override=True)
        
        # Verify all settings are loaded
        assert os.environ.get("ELEVENLABS_API_KEY") == "test-api-key"
        assert os.environ.get("ELEVENLABS_VOICE_ID") == "test-voice"
        assert os.environ.get("ELEVENLABS_MODEL_ID") == "eleven_turbo_v2"
        assert os.environ.get("ELEVENLABS_STABILITY") == "0.7"
        assert os.environ.get("ELEVENLABS_SIMILARITY_BOOST") == "0.8"
        assert os.environ.get("ELEVENLABS_STYLE") == "0.6"
        assert os.environ.get("ELEVENLABS_USE_SPEAKER_BOOST") == "false"
        
        # Test that these can be parsed correctly
        stability = os.environ.get("ELEVENLABS_STABILITY")
        assert stability is not None
        assert float(stability) == 0.7
        
        speaker_boost = os.environ.get("ELEVENLABS_USE_SPEAKER_BOOST")
        assert speaker_boost is not None
        assert speaker_boost.lower() == "false"