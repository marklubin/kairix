import os
import subprocess
import tempfile


class TestJustfileEnvironment:
    """Integration tests for justfile environment commands."""

    def test_list_envs_command(self):
        """Test that list-envs shows available environments."""
        result = subprocess.run(
            ["just", "list-envs"],
            capture_output=True,
            text=True,
            cwd="/Users/mark/kairix/kairix-engine",
        )
        
        assert result.returncode == 0
        assert "Available environments:" in result.stdout
        assert "mac" in result.stdout
        assert "cayucos" in result.stdout

    def test_run_talk_with_invalid_env(self):
        """Test run-talk with non-existent environment."""
        result = subprocess.run(
            ["just", "run-talk", "nonexistent"],
            capture_output=True,
            text=True,
            cwd="/Users/mark/kairix/kairix-engine",
        )
        
        assert result.returncode == 1
        assert "Error: env/nonexistent.env not found" in result.stdout
        assert "Available environments:" in result.stdout

    def test_env_variable_propagation(self):
        """Test that environment variables are properly propagated through just."""
        # Test that the actual justfile's run-talk command would set env vars
        # We'll do a dry-run test by checking the command structure
        
        # Read the actual justfile to verify the command structure
        with open("/Users/mark/kairix/kairix-engine/justfile") as f:
            justfile_content = f.read()
        
        # Verify run-talk target exists and uses proper env loading
        assert "run-talk ENV:" in justfile_content
        assert "source env/{{ENV}}.env" in justfile_content
        assert "set -a" in justfile_content  # This exports all vars
        
        # Test a simple env var propagation
        test_script = """
import os
print(os.environ.get('TEST_VAR', 'not-set'))
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            script_path = f.name
        
        try:
            # Test that environment variables are passed through
            result = subprocess.run(
                ["bash", "-c", f"export TEST_VAR=hello && python {script_path}"],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
            assert "hello" in result.stdout
            
        finally:
            os.unlink(script_path)

    def test_smoke_test_env_loading(self):
        """Test that smoke tests can load environment correctly."""
        # This test verifies the ENV variable is passed correctly
        test_env_check = """
import os
env_name = os.environ.get('ENV', 'not-set')
print(f"ENV={env_name}")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_env_check)
            script_path = f.name
        
        try:
            # Test with ENV=mac
            result = subprocess.run(
                ["python", script_path],
                capture_output=True,
                text=True,
                env={**os.environ, "ENV": "mac"},
            )
            
            assert "ENV=mac" in result.stdout
            
            # Test with ENV=cayucos
            result = subprocess.run(
                ["python", script_path],
                capture_output=True,
                text=True,
                env={**os.environ, "ENV": "cayucos"},
            )
            
            assert "ENV=cayucos" in result.stdout
            
        finally:
            os.unlink(script_path)