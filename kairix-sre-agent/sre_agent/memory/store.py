"""SQLite-based memory store for agent history."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import structlog

logger = structlog.get_logger()


@dataclass
class RunRecord:
    """Record of a single agent run."""
    id: Optional[int] = None
    timestamp: str = ""
    run_type: str = "scheduled"  # scheduled, manual, chat
    status: str = "running"  # running, completed, failed
    services_checked: int = 0
    issues_found: int = 0
    fixes_attempted: int = 0
    fixes_successful: int = 0
    summary: str = ""
    full_report: Dict[str, Any] = None
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        d = asdict(self)
        if self.full_report:
            d["full_report"] = json.dumps(self.full_report)
        return d


@dataclass
class ServiceEvent:
    """Record of a service event (issue, recovery, etc.)."""
    id: Optional[int] = None
    timestamp: str = ""
    service_name: str = ""
    event_type: str = ""  # down, unhealthy, recovered, error
    details: Dict[str, Any] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        d = asdict(self)
        if self.details:
            d["details"] = json.dumps(self.details)
        return d


class MemoryStore:
    """SQLite-based storage for agent memory."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        # Create tables
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                run_type TEXT NOT NULL,
                status TEXT NOT NULL,
                services_checked INTEGER DEFAULT 0,
                issues_found INTEGER DEFAULT 0,
                fixes_attempted INTEGER DEFAULT 0,
                fixes_successful INTEGER DEFAULT 0,
                summary TEXT,
                full_report TEXT,
                duration_seconds REAL DEFAULT 0.0
            );
            
            CREATE TABLE IF NOT EXISTS service_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                service_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT,
                recovery_attempted BOOLEAN DEFAULT FALSE,
                recovery_successful BOOLEAN DEFAULT FALSE
            );
            
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                function_calls TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON service_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_service ON service_events(service_name);
            CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_history(timestamp);
        """)
        self.conn.commit()
    
    def add_run(self, run: RunRecord) -> int:
        """Add a new run record."""
        data = run.to_dict()
        del data["id"]  # Remove id for insert
        
        cursor = self.conn.execute(
            """
            INSERT INTO runs (timestamp, run_type, status, services_checked, 
                            issues_found, fixes_attempted, fixes_successful, 
                            summary, full_report, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (data["timestamp"], data["run_type"], data["status"],
             data["services_checked"], data["issues_found"], 
             data["fixes_attempted"], data["fixes_successful"],
             data["summary"], data.get("full_report"), data["duration_seconds"])
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_run(self, run_id: int, **kwargs):
        """Update a run record."""
        # Build update query
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            if key == "full_report" and isinstance(value, dict):
                values.append(json.dumps(value))
            else:
                values.append(value)
        
        values.append(run_id)
        query = f"UPDATE runs SET {', '.join(fields)} WHERE id = ?"
        
        self.conn.execute(query, values)
        self.conn.commit()
    
    def add_event(self, event: ServiceEvent) -> int:
        """Add a service event."""
        data = event.to_dict()
        del data["id"]
        
        cursor = self.conn.execute(
            """
            INSERT INTO service_events (timestamp, service_name, event_type,
                                      details, recovery_attempted, recovery_successful)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (data["timestamp"], data["service_name"], data["event_type"],
             data.get("details"), data["recovery_attempted"], data["recovery_successful"])
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_recent_runs(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get runs from the last N hours."""
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        cursor = self.conn.execute(
            "SELECT * FROM runs WHERE timestamp > ? ORDER BY timestamp DESC",
            (cutoff,)
        )
        
        runs = []
        for row in cursor:
            run = dict(row)
            if run.get("full_report"):
                run["full_report"] = json.loads(run["full_report"])
            runs.append(run)
        
        return runs
    
    def get_service_events(self, service_name: Optional[str] = None, 
                          hours: int = 24) -> List[Dict[str, Any]]:
        """Get service events from the last N hours."""
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        if service_name:
            cursor = self.conn.execute(
                """SELECT * FROM service_events 
                   WHERE timestamp > ? AND service_name = ? 
                   ORDER BY timestamp DESC""",
                (cutoff, service_name)
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM service_events WHERE timestamp > ? ORDER BY timestamp DESC",
                (cutoff,)
            )
        
        events = []
        for row in cursor:
            event = dict(row)
            if event.get("details"):
                event["details"] = json.loads(event["details"])
            events.append(event)
        
        return events
    
    def get_service_health_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get a summary of service health over the last N hours."""
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        # Get event counts by service and type
        cursor = self.conn.execute(
            """
            SELECT service_name, event_type, COUNT(*) as count
            FROM service_events
            WHERE timestamp > ?
            GROUP BY service_name, event_type
            """,
            (cutoff,)
        )
        
        service_stats = {}
        for row in cursor:
            service = row["service_name"]
            if service not in service_stats:
                service_stats[service] = {
                    "total_events": 0,
                    "down_events": 0,
                    "unhealthy_events": 0,
                    "recovered_events": 0,
                    "error_events": 0
                }
            
            service_stats[service]["total_events"] += row["count"]
            service_stats[service][f"{row['event_type']}_events"] = row["count"]
        
        # Get recovery stats
        cursor = self.conn.execute(
            """
            SELECT COUNT(*) as total_recoveries,
                   SUM(recovery_successful) as successful_recoveries
            FROM service_events
            WHERE timestamp > ? AND recovery_attempted = 1
            """,
            (cutoff,)
        )
        
        recovery_stats = cursor.fetchone()
        
        return {
            "time_window_hours": hours,
            "services": service_stats,
            "recovery": {
                "total_attempts": recovery_stats["total_recoveries"] or 0,
                "successful": recovery_stats["successful_recoveries"] or 0
            }
        }
    
    def add_chat_message(self, role: str, content: str, 
                        function_calls: Optional[List[Dict]] = None):
        """Add a chat message to history."""
        self.conn.execute(
            """
            INSERT INTO chat_history (timestamp, role, content, function_calls)
            VALUES (?, ?, ?, ?)
            """,
            (datetime.utcnow().isoformat(), role, content,
             json.dumps(function_calls) if function_calls else None)
        )
        self.conn.commit()
    
    def get_chat_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent chat history."""
        cursor = self.conn.execute(
            "SELECT * FROM chat_history ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        
        messages = []
        for row in cursor:
            msg = dict(row)
            if msg.get("function_calls"):
                msg["function_calls"] = json.loads(msg["function_calls"])
            messages.append(msg)
        
        return list(reversed(messages))  # Return in chronological order
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()