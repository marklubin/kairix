"""Recovery action implementations."""

import asyncio
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
import structlog

logger = structlog.get_logger()


class RecoveryActions:
    """Implements recovery actions for OpenAI function calling."""
    
    def __init__(self, config):
        self.config = config
        self.max_retries = config.max_retry_attempts
    
    async def restart_service(
        self,
        service_name: str,
        user: Optional[str] = None,
        command: Optional[str] = None
    ) -> Dict[str, Any]:
        """Attempt to restart a service."""
        logger.info("Attempting to restart service", service=service_name, user=user)
        
        # First, try to stop the service gracefully
        await self._stop_service(service_name, user)
        
        # Wait a moment for clean shutdown
        await asyncio.sleep(2)
        
        # Start the service
        if command:
            start_cmd = command
        else:
            # Infer command based on service type
            if "_ui" in service_name or "vite" in service_name:
                start_cmd = "npm run dev"
            elif "_api" in service_name:
                start_cmd = "uvicorn main:app --reload"
            elif "_tools" in service_name:
                start_cmd = "python -m tools.server"
            else:
                return {
                    "service": service_name,
                    "action": "restart",
                    "success": False,
                    "error": "No command specified and could not infer",
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        # Execute start command
        try:
            # Run as specific user if provided
            if user:
                result = subprocess.run(
                    ["su", "-", user, "-c", start_cmd],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                result = subprocess.Popen(
                    start_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                # Give it a moment to start
                await asyncio.sleep(3)
                
                return {
                    "service": service_name,
                    "action": "restart",
                    "success": True,
                    "pid": result.pid,
                    "command": start_cmd,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                "service": service_name,
                "action": "restart",
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _stop_service(self, service_name: str, user: Optional[str] = None) -> bool:
        """Stop a service by name."""
        try:
            # Find process by name
            if user:
                result = subprocess.run(
                    ["pkill", "-U", user, "-f", service_name],
                    capture_output=True
                )
            else:
                result = subprocess.run(
                    ["pkill", "-f", service_name],
                    capture_output=True
                )
            
            return result.returncode == 0
        except Exception as e:
            logger.error("Failed to stop service", service=service_name, error=str(e))
            return False
    
    def clear_cache(
        self,
        service_name: str,
        cache_path: str
    ) -> Dict[str, Any]:
        """Clear cache or temporary files for a service."""
        cache_dir = Path(cache_path)
        
        if not cache_dir.exists():
            return {
                "service": service_name,
                "action": "clear_cache",
                "success": False,
                "error": f"Cache directory does not exist: {cache_path}",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            # Count files before deletion
            files_before = sum(1 for _ in cache_dir.rglob("*") if _.is_file())
            
            # Clear the cache
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
            
            return {
                "service": service_name,
                "action": "clear_cache",
                "success": True,
                "cache_path": cache_path,
                "files_cleared": files_before,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "service": service_name,
                "action": "clear_cache",
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def send_alert(
        self,
        severity: str,
        message: str,
        service_name: Optional[str] = None,
        attempted_fixes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send an alert via Discord webhook or other means."""
        alert_data = {
            "severity": severity,
            "message": message,
            "service": service_name,
            "attempted_fixes": attempted_fixes or [],
            "timestamp": datetime.utcnow().isoformat(),
            "hostname": subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
        }
        
        # Log the alert
        logger.warning("SRE Alert", **alert_data)
        
        # Send to Discord if configured
        if self.config.discord_webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    # Format Discord message
                    color = {
                        "info": 0x3498db,
                        "warning": 0xf39c12,
                        "error": 0xe74c3c,
                        "critical": 0x9b59b6
                    }.get(severity, 0x95a5a6)
                    
                    embed = {
                        "title": f"🚨 SRE Alert - {severity.upper()}",
                        "description": message,
                        "color": color,
                        "fields": []
                    }
                    
                    if service_name:
                        embed["fields"].append({
                            "name": "Service",
                            "value": service_name,
                            "inline": True
                        })
                    
                    if attempted_fixes:
                        embed["fields"].append({
                            "name": "Attempted Fixes",
                            "value": "\n".join(f"• {fix}" for fix in attempted_fixes),
                            "inline": False
                        })
                    
                    embed["fields"].append({
                        "name": "Timestamp",
                        "value": alert_data["timestamp"],
                        "inline": True
                    })
                    
                    response = await client.post(
                        self.config.discord_webhook_url,
                        json={"embeds": [embed]}
                    )
                    
                    alert_data["alert_sent"] = response.status_code == 204
                    alert_data["alert_method"] = "discord"
                    
            except Exception as e:
                alert_data["alert_sent"] = False
                alert_data["alert_error"] = str(e)
        else:
            alert_data["alert_sent"] = False
            alert_data["alert_method"] = "log_only"
        
        return alert_data
    
    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a recovery function by name."""
        if function_name == "restart_service":
            return await self.restart_service(**arguments)
        elif function_name == "clear_cache":
            return self.clear_cache(**arguments)
        elif function_name == "send_alert":
            return await self.send_alert(**arguments)
        else:
            raise ValueError(f"Unknown function: {function_name}")