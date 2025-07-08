"""OpenAI function definitions for health checking."""

from typing import List, Dict, Any

# OpenAI function schemas
HEALTH_CHECK_FUNCTIONS = [
    {
        "name": "check_service_health",
        "description": "Check if a service is running and healthy",
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the service to check"
                },
                "port": {
                    "type": "integer",
                    "description": "Port number the service should be running on"
                },
                "endpoint": {
                    "type": "string",
                    "description": "Health check endpoint path",
                    "default": "/health"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds for the health check",
                    "default": 5.0
                }
            },
            "required": ["service_name", "port"]
        }
    },
    {
        "name": "check_process_status",
        "description": "Check if a process is running using psutil",
        "parameters": {
            "type": "object",
            "properties": {
                "process_name": {
                    "type": "string",
                    "description": "Name of the process to check"
                },
                "user": {
                    "type": "string",
                    "description": "Username the process should be running under",
                    "default": None
                }
            },
            "required": ["process_name"]
        }
    },
    {
        "name": "get_port_listeners",
        "description": "Get list of processes listening on specific ports",
        "parameters": {
            "type": "object",
            "properties": {
                "port_range": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "integer"},
                        "end": {"type": "integer"}
                    },
                    "description": "Port range to check"
                }
            },
            "required": ["port_range"]
        }
    },
    {
        "name": "analyze_service_logs",
        "description": "Analyze recent logs for a service",
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the service"
                },
                "user": {
                    "type": "string",
                    "description": "User running the service"
                },
                "minutes": {
                    "type": "integer",
                    "description": "Number of minutes to look back",
                    "default": 30
                }
            },
            "required": ["service_name"]
        }
    }
]

RECOVERY_FUNCTIONS = [
    {
        "name": "restart_service",
        "description": "Attempt to restart a service",
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the service to restart"
                },
                "user": {
                    "type": "string",
                    "description": "User under which to restart the service"
                },
                "command": {
                    "type": "string",
                    "description": "Command to start the service",
                    "default": None
                }
            },
            "required": ["service_name"]
        }
    },
    {
        "name": "clear_cache",
        "description": "Clear cache or temporary files for a service",
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the service"
                },
                "cache_path": {
                    "type": "string",
                    "description": "Path to cache directory"
                }
            },
            "required": ["service_name", "cache_path"]
        }
    },
    {
        "name": "send_alert",
        "description": "Send an alert via Discord webhook or other means",
        "parameters": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": ["info", "warning", "error", "critical"],
                    "description": "Alert severity level"
                },
                "message": {
                    "type": "string",
                    "description": "Alert message"
                },
                "service_name": {
                    "type": "string",
                    "description": "Affected service name"
                },
                "attempted_fixes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of recovery actions attempted"
                }
            },
            "required": ["severity", "message"]
        }
    }
]

def get_all_functions() -> List[Dict[str, Any]]:
    """Get all available OpenAI functions."""
    return HEALTH_CHECK_FUNCTIONS + RECOVERY_FUNCTIONS