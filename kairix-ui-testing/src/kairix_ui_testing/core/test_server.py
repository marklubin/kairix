"""Test server management for UI tests."""

import threading
import time
import requests
from typing import Optional, Dict, Any
import sys
from pathlib import Path
from contextlib import contextmanager
from unittest import mock

from ..mock_patches import create_mock_patches


class TestServer:
    """Manages a test UI server instance with patched dependencies."""
    
    def __init__(self, mock_config: Optional[Dict[str, Any]] = None, port: int = 7862):
        self.mock_config = mock_config or {}
        self.port = port
        self.url = f"http://localhost:{port}"
        self.app = None
        self.thread = None
        self.patches = []
        
    def start(self):
        """Start the test server in a background thread."""
        # Import the real memory pipeline UI
        # Add kairix modules to path if needed
        kairix_root = Path(__file__).parent.parent.parent.parent.parent
        offline_path = kairix_root / "kairix-offline" / "src"
        core_path = kairix_root / "kairix-core" / "src"
        
        for path in [core_path, offline_path]:
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        
        # Create mock module structure before importing
        mock_processing = type(sys)('kairix_offline.processing')
        mock_processing.initialize_processing = lambda: None
        mock_processing.load_sources_from_gpt_export = lambda x: iter(['mocked'])
        mock_processing.synth_memories = lambda x, y: 'mocked'
        
        # Insert into sys.modules so imports work
        sys.modules['kairix_offline.processing'] = mock_processing
        
        # Create mock patches
        mock_functions = create_mock_patches(self.mock_config)
        
        # Apply patches to the mock module
        for func_name, mock_func in mock_functions.items():
            if 'kairix_offline.processing.' in func_name:
                attr_name = func_name.split('.')[-1]
                setattr(mock_processing, attr_name, mock_func)
            
        try:
            # Import and create the real app
            from kairix_offline.ui.memory_pipeline import history_importer
            self.app = history_importer
        except ImportError as e:
            raise ImportError(
                f"Failed to import kairix_offline. Make sure to run 'uv sync' first. Error: {e}"
            )
        
        # Launch in thread
        def run_server():
            self.app.launch(
                server_name="127.0.0.1",
                server_port=self.port,
                share=False,
                quiet=True,
                prevent_thread_lock=True,
                show_error=True,
            )
            
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        
        # Wait for server to be ready
        self._wait_for_server()
        
    def stop(self):
        """Stop the test server."""
        if self.app:
            self.app.close()
            
        # Stop all patches
        for patch in self.patches:
            patch.stop()
            
    def _wait_for_server(self, timeout: int = 10):
        """Wait for server to be responsive."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(self.url, timeout=1)
                if response.status_code == 200:
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(0.5)
        raise RuntimeError(f"Test server did not start within {timeout} seconds")
        
    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        try:
            response = requests.get(self.url, timeout=1)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


@contextmanager
def test_server(mock_config: Optional[Dict[str, Any]] = None, port: int = 7862):
    """Context manager for test server."""
    server = TestServer(mock_config, port)
    server.start()
    try:
        yield server.url
    finally:
        server.stop()
        time.sleep(0.5)  # Give server time to shut down