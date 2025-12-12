from datetime import datetime
from typing import Optional


def parse_timestamp(value) -> Optional[datetime]:
    """Parse timestamp from various formats"""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        elif isinstance(value, str):
            return datetime.fromisoformat(value)
        elif isinstance(value, datetime):
            return value
    except (ValueError, TypeError, OSError):
        pass
    return None
