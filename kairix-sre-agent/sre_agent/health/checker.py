"""Service health checking implementation."""

import psutil
import subprocess
from datetime import datetime
from typing import Dict, Optional, Any
import httpx
import structlog

logger = structlog.get_logger()


class HealthChecker:
    """Implements health checking functions for OpenAI function calling."""
    
    def __init__(self, config):
        self.config = config
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def check_service_health(
        self,
        service_name: str,
        port: int,
        endpoint: str = "/health",
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Check if a service is running and healthy via HTTP."""
        url = f"http://localhost:{port}{endpoint}"
        
        try:
            response = await self.client.get(url, timeout=timeout)
            
            return {
                "service": service_name,
                "port": port,
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "timestamp": datetime.utcnow().isoformat(),
                "error": None
            }
        except httpx.ConnectError:
            return {
                "service": service_name,
                "port": port,
                "status": "down",
                "status_code": None,
                "response_time_ms": None,
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Connection refused"
            }
        except httpx.TimeoutException:
            return {
                "service": service_name,
                "port": port,
                "status": "timeout",
                "status_code": None,
                "response_time_ms": timeout * 1000,
                "timestamp": datetime.utcnow().isoformat(),
                "error": f"Timeout after {timeout}s"
            }
        except Exception as e:
            return {
                "service": service_name,
                "port": port,
                "status": "error",
                "status_code": None,
                "response_time_ms": None,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def check_process_status(
        self,
        process_name: str,
        user: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if a process is running using psutil."""
        matching_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'status']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    if user is None or proc.info['username'] == user:
                        matching_processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "user": proc.info['username'],
                            "status": proc.info['status']
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            "process_name": process_name,
            "user_filter": user,
            "found": len(matching_processes) > 0,
            "count": len(matching_processes),
            "processes": matching_processes,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_port_listeners(self, port_range: Dict[str, int]) -> Dict[str, Any]:
        """Get list of processes listening on specific ports."""
        start_port = port_range["start"]
        end_port = port_range["end"]
        listeners = {}
        
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and start_port <= conn.laddr.port <= end_port:
                try:
                    proc = psutil.Process(conn.pid)
                    listeners[conn.laddr.port] = {
                        "pid": conn.pid,
                        "name": proc.name(),
                        "user": proc.username(),
                        "cmdline": ' '.join(proc.cmdline())
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    listeners[conn.laddr.port] = {
                        "pid": conn.pid,
                        "name": "unknown",
                        "user": "unknown",
                        "cmdline": "unknown"
                    }
        
        return {
            "port_range": f"{start_port}-{end_port}",
            "listeners": listeners,
            "count": len(listeners),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def analyze_service_logs(
        self,
        service_name: str,
        user: Optional[str] = None,
        minutes: int = 30
    ) -> Dict[str, Any]:
        """Analyze recent logs for a service."""
        # Construct log path
        if user:
            log_path = self.config.log_base_path / user / f"{service_name}.log"
        else:
            log_path = self.config.log_base_path / f"{service_name}.log"
        
        if not log_path.exists():
            return {
                "service": service_name,
                "user": user,
                "log_path": str(log_path),
                "exists": False,
                "error": "Log file not found",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Use tail to get recent logs
        try:
            # Get approximate lines for the time window (assuming ~1 log/second)
            lines_to_read = minutes * 60
            result = subprocess.run(
                ["tail", "-n", str(lines_to_read), str(log_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "service": service_name,
                    "user": user,
                    "log_path": str(log_path),
                    "exists": True,
                    "error": f"Failed to read logs: {result.stderr}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Analyze log content
            lines = result.stdout.strip().split('\n')
            error_count = sum(1 for line in lines if 'ERROR' in line.upper())
            warning_count = sum(1 for line in lines if 'WARNING' in line.upper() or 'WARN' in line.upper())
            
            # Extract recent errors
            recent_errors = [
                line for line in lines[-20:]  # Last 20 lines
                if 'ERROR' in line.upper()
            ]
            
            return {
                "service": service_name,
                "user": user,
                "log_path": str(log_path),
                "exists": True,
                "minutes_analyzed": minutes,
                "total_lines": len(lines),
                "error_count": error_count,
                "warning_count": warning_count,
                "recent_errors": recent_errors[:5],  # Top 5 recent errors
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except subprocess.TimeoutExpired:
            return {
                "service": service_name,
                "user": user,
                "log_path": str(log_path),
                "exists": True,
                "error": "Timeout reading logs",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "service": service_name,
                "user": user,
                "log_path": str(log_path),
                "exists": True,
                "error": f"Error analyzing logs: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a health check function by name."""
        if function_name == "check_service_health":
            return await self.check_service_health(**arguments)
        elif function_name == "check_process_status":
            return self.check_process_status(**arguments)
        elif function_name == "get_port_listeners":
            return self.get_port_listeners(**arguments)
        elif function_name == "analyze_service_logs":
            return self.analyze_service_logs(**arguments)
        else:
            raise ValueError(f"Unknown function: {function_name}")