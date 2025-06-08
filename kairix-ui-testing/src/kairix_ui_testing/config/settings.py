"""Test configuration settings."""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal


class TestConfig(BaseSettings):
    """Test configuration using pydantic-settings."""
    
    # URLs
    memory_pipeline_url: str = "http://localhost:7860"
    
    # Timeouts (in seconds)
    default_timeout: int = 30
    page_load_timeout: int = 60
    
    # Browser settings - Firefox only
    headless: bool = False
    browser: Literal["firefox"] = "firefox"
    
    # Firefox-specific options
    firefox_prefs: dict = {
        "dom.webnotifications.enabled": False,
        "dom.push.enabled": False,
    }
    
    # Test data paths
    test_data_dir: Path = Path("test_data")
    screenshot_dir: Path = Path("screenshots")
    
    # Download directory for Firefox
    firefox_downloads_dir: Path = Path("downloads")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"