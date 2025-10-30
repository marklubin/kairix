"""Telemetry tracking for Kairix server requests."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger


class TelemetryManager:
    """Manages request telemetry and aggregations."""

    def __init__(self, db_path: str = ".kairix/telemetry.db"):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        # Create directory
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS request_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL UNIQUE,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                status_code INTEGER,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                duration_ms REAL,
                model_id TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                perceptors_used TEXT,
                perceptor_duration_ms REAL,
                error_type TEXT,
                error_message TEXT,
                user_agent TEXT,
                client_ip TEXT,
                stream BOOLEAN,
                message_count INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_timestamp ON request_telemetry(timestamp);
            CREATE INDEX IF NOT EXISTS idx_endpoint ON request_telemetry(endpoint);
            CREATE INDEX IF NOT EXISTS idx_model_id ON request_telemetry(model_id);
            CREATE INDEX IF NOT EXISTS idx_status_code ON request_telemetry(status_code);

            CREATE TABLE IF NOT EXISTS health_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                active_requests INTEGER,
                db_connections INTEGER,
                cache_size_mb REAL
            );

            CREATE INDEX IF NOT EXISTS idx_health_timestamp ON health_snapshots(timestamp);
        """
        )

        conn.commit()
        conn.close()

        logger.info(f"Telemetry database initialized at {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def start_request(
        self,
        endpoint: str,
        method: str,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        """Start tracking a request. Returns request_id."""
        request_id = str(uuid.uuid4())

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO request_telemetry
                (request_id, endpoint, method, client_ip, user_agent, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (request_id, endpoint, method, client_ip, user_agent, datetime.utcnow()),
            )

            conn.commit()

        return request_id

    def end_request(
        self,
        request_id: str,
        status_code: int,
        duration_ms: float,
        model_id: str | None = None,
        tokens: dict[str, int] | None = None,
        perceptors: list[str] | None = None,
        perceptor_duration_ms: float | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        stream: bool = False,
        message_count: int | None = None,
    ):
        """End tracking a request with final metrics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            perceptors_json = json.dumps(perceptors) if perceptors else None

            cursor.execute(
                """
                UPDATE request_telemetry
                SET status_code = ?,
                    duration_ms = ?,
                    model_id = ?,
                    prompt_tokens = ?,
                    completion_tokens = ?,
                    total_tokens = ?,
                    perceptors_used = ?,
                    perceptor_duration_ms = ?,
                    error_type = ?,
                    error_message = ?,
                    stream = ?,
                    message_count = ?
                WHERE request_id = ?
            """,
                (
                    status_code,
                    duration_ms,
                    model_id,
                    tokens.get("prompt_tokens") if tokens else None,
                    tokens.get("completion_tokens") if tokens else None,
                    tokens.get("total_tokens") if tokens else None,
                    perceptors_json,
                    perceptor_duration_ms,
                    error_type,
                    error_message,
                    stream,
                    message_count,
                    request_id,
                ),
            )

            conn.commit()

    def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        endpoint: str | None = None,
        model_id: str | None = None,
    ) -> dict[str, Any]:
        """Get aggregated metrics for time range."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = ["timestamp BETWEEN ? AND ?"]
            params: list[Any] = [start_time, end_time]

            if endpoint:
                where_clauses.append("endpoint = ?")
                params.append(endpoint)

            if model_id:
                where_clauses.append("model_id = ?")
                params.append(model_id)

            where_sql = " AND ".join(where_clauses)

            # Get aggregated stats
            cursor.execute(
                f"""
                SELECT
                    COUNT(*) as total_requests,
                    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count,
                    AVG(duration_ms) as avg_duration,
                    SUM(total_tokens) as total_tokens,
                    AVG(total_tokens) as avg_tokens,
                    SUM(CASE WHEN stream = 1 THEN 1 ELSE 0 END) as streaming_requests
                FROM request_telemetry
                WHERE {where_sql}
            """,
                params,
            )

            row = cursor.fetchone()
            if not row:
                return self._empty_metrics()

            # Get percentiles
            cursor.execute(
                f"""
                SELECT duration_ms
                FROM request_telemetry
                WHERE {where_sql} AND duration_ms IS NOT NULL
                ORDER BY duration_ms
            """,
                params,
            )

            durations = [r[0] for r in cursor.fetchall()]

            def percentile(data, p):
                if not data:
                    return None
                k = (len(data) - 1) * (p / 100)
                f = int(k)
                c = k - f
                if f + 1 < len(data):
                    return data[f] + c * (data[f + 1] - data[f])
                return data[f]

            # Get request breakdown by endpoint
            cursor.execute(
                f"""
                SELECT endpoint, COUNT(*) as count
                FROM request_telemetry
                WHERE {where_sql}
                GROUP BY endpoint
                ORDER BY count DESC
            """,
                params,
            )

            endpoint_breakdown = [{"endpoint": r[0], "count": r[1]} for r in cursor.fetchall()]

            return {
                "total_requests": row[0] or 0,
                "error_count": row[1] or 0,
                "error_rate": (row[1] / row[0] * 100) if row[0] else 0,
                "avg_duration_ms": round(row[2], 2) if row[2] else None,
                "p50_duration_ms": round(percentile(durations, 50), 2) if durations else None,
                "p95_duration_ms": round(percentile(durations, 95), 2) if durations else None,
                "p99_duration_ms": round(percentile(durations, 99), 2) if durations else None,
                "total_tokens": row[3] or 0,
                "avg_tokens": round(row[4], 2) if row[4] else None,
                "streaming_requests": row[5] or 0,
                "endpoint_breakdown": endpoint_breakdown,
            }

    def get_timeseries(
        self,
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 5,
        endpoint: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get time-series data for charting."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = ["timestamp BETWEEN ? AND ?"]
            params: list[Any] = [start_time, end_time]

            if endpoint:
                where_clauses.append("endpoint = ?")
                params.append(endpoint)

            where_sql = " AND ".join(where_clauses)

            # SQLite time bucketing using strftime
            cursor.execute(
                f"""
                SELECT
                    strftime(
                        '%Y-%m-%d %H:%M:00',
                        timestamp,
                        '-' || (CAST(strftime('%M', timestamp) AS INTEGER) % {interval_minutes}) || ' minutes'
                    ) as time_bucket,
                    COUNT(*) as request_count,
                    AVG(duration_ms) as avg_duration,
                    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count
                FROM request_telemetry
                WHERE {where_sql}
                GROUP BY time_bucket
                ORDER BY time_bucket
            """,
                params,
            )

            return [
                {
                    "timestamp": r[0],
                    "request_count": r[1],
                    "avg_duration_ms": round(r[2], 2) if r[2] else None,
                    "error_count": r[3],
                }
                for r in cursor.fetchall()
            ]

    def record_health_snapshot(self):
        """Record current system health metrics."""
        try:
            import psutil

            # Get disk usage for .kairix directory
            cache_path = Path(".kairix")
            cache_size_mb = 0
            if cache_path.exists():
                cache_size_mb = (
                    sum(f.stat().st_size for f in cache_path.rglob("*") if f.is_file())
                    / (1024 * 1024)
                )

            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO health_snapshots
                    (cpu_percent, memory_percent, disk_percent, cache_size_mb)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        psutil.cpu_percent(),
                        psutil.virtual_memory().percent,
                        psutil.disk_usage("/").percent,
                        cache_size_mb,
                    ),
                )

                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to record health snapshot: {e}")

    def _empty_metrics(self) -> dict[str, Any]:
        """Return empty metrics structure."""
        return {
            "total_requests": 0,
            "error_count": 0,
            "error_rate": 0,
            "avg_duration_ms": None,
            "p50_duration_ms": None,
            "p95_duration_ms": None,
            "p99_duration_ms": None,
            "total_tokens": 0,
            "avg_tokens": None,
            "streaming_requests": 0,
            "endpoint_breakdown": [],
        }

    def cleanup_old_data(self, days: int = 30):
        """Remove telemetry data older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM request_telemetry WHERE timestamp < ?", (cutoff_date,)
            )

            cursor.execute("DELETE FROM health_snapshots WHERE timestamp < ?", (cutoff_date,))

            deleted_requests = cursor.rowcount
            conn.commit()

            # Vacuum to reclaim space
            cursor.execute("VACUUM")

            logger.info(
                f"Cleaned up {deleted_requests} telemetry records older than {days} days"
            )
