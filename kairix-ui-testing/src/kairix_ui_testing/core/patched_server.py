"""Simple patched server for UI testing."""

import threading
import time
import requests
from typing import Optional, Dict, Any
from contextlib import contextmanager
from unittest import mock

from ..mock_patches import create_mock_patches


class PatchedUIServer:
    """Runs the real UI with patched dependencies."""
    
    def __init__(self, app_module: str, app_attr: str, mock_config: Optional[Dict[str, Any]] = None, port: int = 7862):
        self.app_module = app_module
        self.app_attr = app_attr
        self.mock_config = mock_config or {}
        self.port = port
        self.url = f"http://localhost:{port}"
        self.app = None
        self.thread = None
        self.patches = []
        
    def start(self):
        """Start the server with patches applied."""
        # Create mock patches instance
        mock_patches_instance = create_mock_patches(self.mock_config)
        
        # Apply patches
        patch_map = {
            'kairix_offline.processing.initialize_processing': mock_patches_instance.mock_initialize_processing,
            'kairix_offline.processing.load_sources_from_gpt_export': mock_patches_instance.mock_load_sources_from_gpt_export,
            'kairix_offline.processing.synth_memories': mock_patches_instance.mock_synth_memories,
        }
        
        for module_path, mock_func in patch_map.items():
            patch = mock.patch(module_path, mock_func)
            self.patches.append(patch)
            patch.start()
        
        # Import and get the app
        import importlib
        module = importlib.import_module(self.app_module)
        self.app = getattr(module, self.app_attr)
        
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
        """Stop the server and remove patches."""
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
        raise RuntimeError(f"Server did not start within {timeout} seconds")


@contextmanager
def patched_ui_server(app_module: str, app_attr: str, mock_config: Optional[Dict[str, Any]] = None, port: int = 7862):
    """Context manager for patched UI server."""
    server = PatchedUIServer(app_module, app_attr, mock_config, port)
    server.start()
    try:
        yield server.url
    finally:
        server.stop()
        time.sleep(0.5)  # Give server time to shut down