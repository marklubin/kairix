"""MCPEz Docker container manager for Kairix."""
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger

MCPEZ_REPO = "https://github.com/Veallym0n/mcpez.git"
MCPEZ_IMAGE = "mcpez:latest"
MCPEZ_CONTAINER = "kairix-mcpez"


class MCPEzManager:
    """Manages the MCPEz Docker container lifecycle."""

    def __init__(self, port: int = 8088, data_dir: Optional[Path] = None):
        """Initialize MCPEz manager.

        Args:
            port: Port for MCPEz web UI (default: 8088)
            data_dir: Directory for MCPEz data and repo (default: ~/.kairix/mcpez)
        """
        self.port = port
        self.data_dir = data_dir or Path.home() / ".kairix" / "mcpez"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.repo_dir = self.data_dir / "repo"
        self.container_name = MCPEZ_CONTAINER

    def _run_command(self, cmd: list[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            raise RuntimeError(f"Command timed out after 300 seconds") from e

    def _ensure_repo(self) -> None:
        """Clone MCPEz repository if not present."""
        if self.repo_dir.exists() and (self.repo_dir / ".git").exists():
            logger.info(f"MCPEz repository already exists at {self.repo_dir}")
            return

        logger.info(f"Cloning MCPEz repository to {self.repo_dir}")
        exitcode, stdout, stderr = self._run_command([
            "git", "clone", MCPEZ_REPO, str(self.repo_dir)
        ])

        if exitcode != 0:
            logger.error(f"Failed to clone repository: {stderr}")
            raise RuntimeError(f"Failed to clone MCPEz repository: {stderr}")

        logger.info("MCPEz repository cloned successfully")

    def _build_image(self) -> None:
        """Build MCPEz Docker image."""
        # Check if image already exists
        exitcode, stdout, stderr = self._run_command([
            "docker", "images", "-q", MCPEZ_IMAGE
        ])

        if exitcode == 0 and stdout.strip():
            logger.info(f"MCPEz Docker image already exists: {MCPEZ_IMAGE}")
            return

        logger.info("Building MCPEz Docker image...")
        exitcode, stdout, stderr = self._run_command([
            "docker", "build", "-t", MCPEZ_IMAGE, "."
        ], cwd=self.repo_dir)

        if exitcode != 0:
            logger.error(f"Failed to build Docker image: {stderr}")
            raise RuntimeError(f"Failed to build MCPEz Docker image: {stderr}")

        logger.info("MCPEz Docker image built successfully")

    def _is_container_running(self) -> bool:
        """Check if the MCPEz container is running."""
        exitcode, stdout, stderr = self._run_command([
            "docker", "ps", "-q", "-f", f"name={self.container_name}"
        ])

        return exitcode == 0 and bool(stdout.strip())

    def _stop_existing_container(self) -> None:
        """Stop and remove existing container if it exists."""
        # Check if container exists (running or stopped)
        exitcode, stdout, stderr = self._run_command([
            "docker", "ps", "-a", "-q", "-f", f"name={self.container_name}"
        ])

        if exitcode == 0 and stdout.strip():
            logger.info(f"Stopping existing container: {self.container_name}")
            self._run_command(["docker", "stop", self.container_name])
            self._run_command(["docker", "rm", self.container_name])

    async def start(self) -> None:
        """Start MCPEz Docker container."""
        if self._is_container_running():
            logger.warning("MCPEz is already running")
            return

        self._ensure_repo()
        self._build_image()
        self._stop_existing_container()

        logger.info(f"Starting MCPEz container on port {self.port}")

        # Create volume for data persistence
        volume_name = f"{self.container_name}-data"

        # Start the container
        cmd = [
            "docker", "run",
            "-d",  # Detached mode
            "-p", f"{self.port}:80",  # Map port
            "--name", self.container_name,
            "-v", f"{volume_name}:/data",  # Persistent volume
            "--restart", "unless-stopped",  # Auto-restart
            MCPEZ_IMAGE
        ]

        exitcode, stdout, stderr = self._run_command(cmd)

        if exitcode != 0:
            logger.error(f"Failed to start container: {stderr}")
            raise RuntimeError(f"Failed to start MCPEz container: {stderr}")

        # Give it a moment to start
        await asyncio.sleep(2)

        # Verify it's running
        if not self._is_container_running():
            # Check logs for error
            exitcode, stdout, stderr = self._run_command([
                "docker", "logs", self.container_name
            ])
            logger.error(f"Container failed to start. Logs: {stdout}\n{stderr}")
            raise RuntimeError("MCPEz container terminated immediately after start")

        logger.info(f"MCPEz started successfully at http://localhost:{self.port}")

    async def stop(self) -> None:
        """Stop MCPEz Docker container."""
        if not self._is_container_running():
            logger.warning("MCPEz is not running")
            return

        logger.info("Stopping MCPEz container")

        exitcode, stdout, stderr = self._run_command([
            "docker", "stop", self.container_name
        ])

        if exitcode != 0:
            logger.error(f"Failed to stop container: {stderr}")
            raise RuntimeError(f"Failed to stop MCPEz container: {stderr}")

        logger.info("MCPEz stopped successfully")

    async def health_check(self) -> bool:
        """Check if MCPEz is running and healthy.

        Returns:
            True if healthy, False otherwise
        """
        return self._is_container_running()

    def get_web_ui_url(self) -> str:
        """Get the Web UI URL.

        Returns:
            URL for the Web UI
        """
        return f"http://localhost:{self.port}"

    def get_mcp_endpoint(self) -> str:
        """Get the MCP SSE endpoint URL.

        Returns:
            URL for the MCP SSE endpoint (will vary by application)
        """
        return f"http://localhost:{self.port}/mcp/{{app_id}}/sse"
