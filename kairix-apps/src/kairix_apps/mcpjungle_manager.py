"""MCPJungle process manager for Kairix."""
import asyncio
import os
import platform
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional

from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger

MCPJUNGLE_VERSION = "0.2.4"
MCPJUNGLE_REPO = "mcpjungle/MCPJungle"


class MCPJungleManager:
    """Manages the MCPJungle subprocess lifecycle."""

    def __init__(self, port: int = 8080, data_dir: Optional[Path] = None):
        """Initialize MCPJungle manager.

        Args:
            port: Port for MCPJungle to listen on (default: 8080)
            data_dir: Directory for MCPJungle data (default: ~/.kairix/mcpjungle)
        """
        self.port = port
        self.data_dir = data_dir or Path.home() / ".kairix" / "mcpjungle"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.bin_dir = self.data_dir / "bin"
        self.bin_dir.mkdir(parents=True, exist_ok=True)

        self.binary_path = self.bin_dir / "mcpjungle"
        self.process: Optional[subprocess.Popen] = None

    def _get_download_url(self) -> str:
        """Get the download URL for the current platform."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Map platform names
        if system == "darwin":
            os_name = "Darwin"
        elif system == "linux":
            os_name = "Linux"
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

        # Map architecture names
        if machine in ["x86_64", "amd64"]:
            arch = "x86_64"
        elif machine in ["aarch64", "arm64"]:
            arch = "arm64"
        else:
            raise RuntimeError(f"Unsupported architecture: {machine}")

        # Construct URL
        filename = f"mcpjungle_{MCPJUNGLE_VERSION}_{os_name}_{arch}.tar.gz"
        return f"https://github.com/{MCPJUNGLE_REPO}/releases/download/v{MCPJUNGLE_VERSION}/{filename}"

    def _download_binary(self) -> None:
        """Download and extract MCPJungle binary."""
        if self.binary_path.exists():
            logger.info(f"MCPJungle binary already exists at {self.binary_path}")
            return

        url = self._get_download_url()
        logger.info(f"Downloading MCPJungle from {url}")

        tar_path = self.bin_dir / "mcpjungle.tar.gz"

        try:
            # Download
            urllib.request.urlretrieve(url, tar_path)
            logger.info(f"Downloaded MCPJungle to {tar_path}")

            # Extract
            import tarfile
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(self.bin_dir)

            # Make executable
            self.binary_path.chmod(0o755)
            logger.info(f"Extracted and set executable permissions for {self.binary_path}")

            # Cleanup
            tar_path.unlink()

        except Exception as e:
            logger.error(f"Failed to download MCPJungle: {e}")
            if tar_path.exists():
                tar_path.unlink()
            raise

    def _ensure_binary(self) -> None:
        """Ensure MCPJungle binary is available."""
        if not self.binary_path.exists():
            logger.info("MCPJungle binary not found, downloading...")
            self._download_binary()

    async def start(self) -> None:
        """Start MCPJungle process."""
        if self.process is not None:
            logger.warning("MCPJungle is already running")
            return

        self._ensure_binary()

        # Set environment variables
        env = os.environ.copy()
        env["SERVER_MODE"] = "production"
        env["MCPJUNGLE_PORT"] = str(self.port)

        # Use SQLite database in data directory
        db_path = self.data_dir / "mcpjungle.db"
        env["DATABASE_URL"] = f"sqlite:///{db_path}"

        logger.info(f"Starting MCPJungle on port {self.port}")
        logger.info(f"Database: {db_path}")

        try:
            # Start process
            self.process = subprocess.Popen(
                [str(self.binary_path), "start"],
                env=env,
                cwd=str(self.data_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Give it a moment to start
            await asyncio.sleep(2)

            # Check if process is still running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                logger.error(f"MCPJungle failed to start. stdout: {stdout}, stderr: {stderr}")
                self.process = None
                raise RuntimeError("MCPJungle process terminated immediately after start")

            logger.info(f"MCPJungle started successfully (PID: {self.process.pid})")

        except Exception as e:
            logger.error(f"Failed to start MCPJungle: {e}")
            self.process = None
            raise

    async def stop(self) -> None:
        """Stop MCPJungle process."""
        if self.process is None:
            logger.warning("MCPJungle is not running")
            return

        logger.info("Stopping MCPJungle")

        try:
            self.process.terminate()

            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=10)
                logger.info("MCPJungle stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("MCPJungle did not stop gracefully, killing")
                self.process.kill()
                self.process.wait()

        except Exception as e:
            logger.error(f"Error stopping MCPJungle: {e}")
        finally:
            self.process = None

    async def health_check(self) -> bool:
        """Check if MCPJungle is running and healthy.

        Returns:
            True if healthy, False otherwise
        """
        if self.process is None:
            return False

        # Check if process is still running
        if self.process.poll() is not None:
            logger.warning("MCPJungle process has terminated")
            self.process = None
            return False

        # TODO: Add HTTP health check to http://localhost:{port}/health if MCPJungle supports it
        return True

    def get_mcp_endpoint(self) -> str:
        """Get the MCP endpoint URL.

        Returns:
            URL for the MCP endpoint
        """
        return f"http://localhost:{self.port}/mcp"
