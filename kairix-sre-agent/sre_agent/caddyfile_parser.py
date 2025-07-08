"""Caddyfile parser to dynamically discover users and services."""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import structlog

logger = structlog.get_logger()


class CaddyfileParser:
    """Parse Caddyfile to extract user services configuration."""
    
    def __init__(self, caddyfile_path: Path = None):
        self.caddyfile_path = caddyfile_path or Path.home() / "kairix" / "caddyfile"
    
    def parse_services(self) -> List[Dict[str, any]]:
        """Parse Caddyfile and return list of services with their configurations."""
        if not self.caddyfile_path.exists():
            logger.warning(f"Caddyfile not found at {self.caddyfile_path}")
            return []
        
        services = []
        
        try:
            with open(self.caddyfile_path, 'r') as f:
                content = f.read()
            
            # Split into blocks by looking for domain definitions
            blocks = re.split(r'\n(?=http://)', content)
            
            for block in blocks:
                if not block.strip():
                    continue
                
                # Parse each user block
                service_info = self._parse_block(block)
                if service_info:
                    services.append(service_info)
            
            logger.info(f"Parsed {len(services)} service configurations from Caddyfile")
            return services
            
        except Exception as e:
            logger.error("Error parsing Caddyfile", error=str(e))
            return []
    
    def _parse_block(self, block: str) -> Optional[Dict[str, any]]:
        """Parse a single service block."""
        lines = block.strip().split('\n')
        if not lines:
            return None
        
        # Extract subdomain and username
        domain_match = re.match(r'http://([^.]+)\.kairix\.net', lines[0])
        if not domain_match:
            return None
        
        subdomain = domain_match.group(1)
        
        # Skip wildcard entry
        if subdomain == '*':
            return None
        
        # Extract username from basic_auth
        username = None
        for i, line in enumerate(lines):
            if 'basic_auth' in line and i + 1 < len(lines):
                # Next line should have username
                user_match = re.match(r'\s*(\w+)\s+\$', lines[i + 1])
                if user_match:
                    username = user_match.group(1)
                    break
        
        if not username:
            logger.warning(f"No username found for subdomain {subdomain}")
            return None
        
        # Extract port mappings
        ports = {}
        for line in lines:
            if 'reverse_proxy localhost:' in line:
                port_match = re.search(r'localhost:(\d+)', line)
                if port_match:
                    port = int(port_match.group(1))
                    
                    # Determine service type based on path or port range
                    if 'handle_path /' in lines[lines.index(line) - 1]:
                        if '/api/' in lines[lines.index(line) - 1]:
                            ports['api'] = port
                        elif '/tools/' in lines[lines.index(line) - 1]:
                            ports['tools'] = port
                        else:
                            ports['ui'] = port
                    else:
                        # Fallback to port range detection
                        if 6000 <= port < 7000:
                            ports['ui'] = port
                        elif 7000 <= port < 8000:
                            ports['api'] = port
                        elif 8000 <= port < 9000:
                            ports['tools'] = port
        
        return {
            'subdomain': subdomain,
            'username': username,
            'ports': ports
        }
    
    def get_user_services(self) -> List[Tuple[str, str, int, str]]:
        """Get list of (service_name, username, port, endpoint) tuples."""
        services = self.parse_services()
        user_services = []
        
        for service in services:
            username = service['username']
            
            for service_type, port in service['ports'].items():
                # Determine health check endpoint based on service type
                if service_type == 'ui':
                    endpoint = '/'
                elif service_type == 'api':
                    endpoint = '/api/status'
                elif service_type == 'tools':
                    endpoint = '/tools/health'
                else:
                    endpoint = '/health'
                
                service_name = f"{username}_{service_type}"
                user_services.append((service_name, username, port, endpoint))
        
        return user_services