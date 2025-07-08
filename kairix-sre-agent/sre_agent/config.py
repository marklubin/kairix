"""Configuration for the SRE Agent."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import os
from .caddyfile_parser import CaddyfileParser


@dataclass
class ServiceConfig:
    """Configuration for a monitored service."""
    name: str
    port: int
    health_endpoint: str = "/health"
    user: Optional[str] = None


@dataclass
class Config:
    """Main configuration for the SRE agent."""
    # Service monitoring
    services: List[ServiceConfig]
    port_ranges: Dict[str, range] = None
    
    # Paths
    log_base_path: Path = Path("/var/log/kairix")  # User logs will be in subdirectories
    agent_log_path: Path = Path.home() / "kairix" / "logs" / "sre-agent"
    memory_db_path: Path = Path.home() / ".kairix" / "sre-agent.db"
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    
    # Behavior
    check_interval_seconds: int = 300  # 5 minutes
    log_window_minutes: int = 30
    max_retry_attempts: int = 1
    
    # Alerting
    discord_webhook_url: Optional[str] = None
    
    def __post_init__(self):
        """Set up default values."""
        if self.port_ranges is None:
            self.port_ranges = {
                "ui": range(6000, 6010),
                "api": range(7000, 7010),
                "tools": range(8000, 8010),
            }
        
        # Get OpenAI API key from environment
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        
        # Create directories if they don't exist
        self.agent_log_path.mkdir(parents=True, exist_ok=True)
        self.memory_db_path.parent.mkdir(parents=True, exist_ok=True)


def get_default_config() -> Config:
    """Get the default configuration."""
    services = []
    
    # Try to parse Caddyfile for dynamic service discovery
    parser = CaddyfileParser()
    user_services = parser.get_user_services()
    
    if user_services:
        # Use dynamically discovered services
        for service_name, username, port, endpoint in user_services:
            services.append(ServiceConfig(service_name, port, endpoint, username))
        print(f"Loaded {len(services)} services from Caddyfile")
    else:
        # Fallback to default services if Caddyfile parsing fails
        print("Warning: Could not parse Caddyfile, using default services")
        users = ["mark", "alice", "bob"]
        
        for user in users:
            base_port = users.index(user)
            services.extend([
                ServiceConfig(f"{user}_ui", 6000 + base_port, "/", user),
                ServiceConfig(f"{user}_api", 7000 + base_port, "/api/status", user),
                ServiceConfig(f"{user}_tools", 8000 + base_port, "/health", user),
            ])
    
    return Config(services=services)