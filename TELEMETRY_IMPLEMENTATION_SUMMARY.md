# Telemetry System Implementation Summary

## Overview

A comprehensive telemetry and analytics system has been implemented for the Kairix server, including:
- Request tracking and metrics collection
- Time-series data aggregation
- Admin dashboard with interactive charts
- Shadow environment support for safe testing

## What Was Built

### 1. Core Telemetry System

**File:** `kairix-apps/src/kairix_apps/telemetry_manager.py`

A complete telemetry manager with SQLite storage tracking:
- Request metadata (endpoint, method, timestamps, duration)
- Model usage and token counts
- Error tracking
- Client information (IP, user agent)
- Streaming vs non-streaming requests

**Key Features:**
- Automatic database creation with proper indexes
- Aggregated metrics (total requests, error rates, percentiles)
- Time-series data bucketing (configurable intervals)
- Endpoint breakdown analysis
- System health snapshots (CPU, memory, disk, cache)
- Automatic data cleanup (configurable retention period)

### 2. Read-Only Database Wrapper

**File:** `kairix-apps/src/kairix_apps/db_wrapper.py`

A database wrapper for enforcing read-only access in shadow environments:
- Environment detection via `KAIRIX_ENVIRONMENT` env var
- Read-only mode enforcement at database connection level
- Raises `ReadOnlyDatabaseError` on write attempts
- Safe for production database access in testing scenarios

### 3. Server Integration

**File:** `kairix-apps/src/kairix_apps/server.py`

**Changes Made:**
- Added `TelemetryManager` initialization in server startup
- Created `TelemetryMiddleware` to automatically track all requests
- Added two new admin endpoints:
  - `GET /admin/telemetry/metrics` - Aggregated metrics
  - `GET /admin/telemetry/timeseries` - Time-series data for charting

**Middleware Tracks:**
- Request start/end timestamps
- HTTP method and endpoint
- Response status codes
- Request duration (milliseconds)
- Client IP and user agent
- Errors (type and message)

### 4. Admin Dashboard

**File:** `kairix-apps/src/kairix_apps/admin_template.html`

**New Telemetry Tab Features:**
- Time range selector (1h, 6h, 24h, 7d, 30d)
- Key metrics display:
  - Total requests
  - Error count and rate
  - Average duration
  - P50, P95, P99 latency percentiles
  - Total tokens used
  - Streaming request count
- Interactive Chart.js chart showing:
  - Request count over time
  - Average duration over time
  - Dual Y-axis for easy comparison
- Endpoint breakdown showing request distribution

### 5. Shadow Environment Support

**File:** `SHADOW_ENVIRONMENT_SETUP.md`

Complete guide for setting up a parallel testing environment with:
- Read-only access to production databases
- Separate telemetry tracking
- SystemD service configuration
- Caddy reverse proxy setup
- Testing and verification procedures

## Database Schema

### request_telemetry Table

```sql
CREATE TABLE request_telemetry (
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
```

**Indexes:**
- `idx_timestamp` on timestamp
- `idx_endpoint` on endpoint
- `idx_model_id` on model_id
- `idx_status_code` on status_code

### health_snapshots Table

```sql
CREATE TABLE health_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cpu_percent REAL,
    memory_percent REAL,
    disk_percent REAL,
    active_requests INTEGER,
    db_connections INTEGER,
    cache_size_mb REAL
);
```

## API Endpoints

### GET /admin/telemetry/metrics

**Query Parameters:**
- `start_time` (optional): ISO format datetime
- `end_time` (optional): ISO format datetime
- `endpoint` (optional): Filter by endpoint
- `model_id` (optional): Filter by model
- `range_hours` (default: 24): Hours to look back

**Response:**
```json
{
  "metrics": {
    "total_requests": 150,
    "error_count": 2,
    "error_rate": 1.33,
    "avg_duration_ms": 1250.50,
    "p50_duration_ms": 1100.25,
    "p95_duration_ms": 2300.75,
    "p99_duration_ms": 3200.00,
    "total_tokens": 45000,
    "avg_tokens": 300.00,
    "streaming_requests": 75,
    "endpoint_breakdown": [
      {"endpoint": "/v1/chat/completions", "count": 145},
      {"endpoint": "/health", "count": 5}
    ]
  },
  "time_range": {
    "start": "2025-10-29T03:00:00",
    "end": "2025-10-30T03:00:00",
    "hours": 24
  }
}
```

### GET /admin/telemetry/timeseries

**Query Parameters:**
- `start_time` (optional): ISO format datetime
- `end_time` (optional): ISO format datetime
- `endpoint` (optional): Filter by endpoint
- `interval_minutes` (default: 5): Bucket size
- `range_hours` (default: 24): Hours to look back

**Response:**
```json
{
  "data": [
    {
      "timestamp": "2025-10-30 02:00:00",
      "request_count": 15,
      "avg_duration_ms": 1250.50,
      "error_count": 0
    }
  ],
  "time_range": {...},
  "config": {...}
}
```

## Testing

**Test File:** `kairix-apps/test_telemetry.py`

Tests verify:
- ✅ TelemetryManager initialization
- ✅ Request tracking (start/end)
- ✅ Metrics aggregation
- ✅ Timeseries data generation
- ✅ DatabaseWrapper read/write modes
- ✅ Environment detection

**All tests passing!**

## Deployment Steps

### To Production (Main Branch)

1. Merge feature/telemetry-system to main:
   ```bash
   git checkout main
   git merge feature/telemetry-system
   git push origin main
   ```

2. On coalinga server:
   ```bash
   cd /home/kairix/kairix
   git pull origin main
   cd kairix-core && uv sync && cd ../kairix-apps && uv sync
   sudo systemctl restart kairix-server-mark
   ```

3. Verify telemetry is working:
   - Visit https://dev.kairix.net/admin
   - Click "Telemetry" tab
   - Should see metrics and charts

### To Shadow Environment

Follow `SHADOW_ENVIRONMENT_SETUP.md` for complete instructions:

1. Set up Doppler config for shadow
2. Create SystemD service
3. Configure Caddy reverse proxy
4. Start and test shadow server

## Monitoring

### Check Telemetry Data

```bash
# On coalinga
sqlite3 /home/kairix/kairix/.kairix/telemetry.db

# View recent requests
SELECT endpoint, method, status_code, duration_ms, timestamp
FROM request_telemetry
ORDER BY timestamp DESC
LIMIT 10;

# View aggregated stats
SELECT
    endpoint,
    COUNT(*) as total_requests,
    AVG(duration_ms) as avg_duration,
    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as errors
FROM request_telemetry
WHERE timestamp > datetime('now', '-24 hours')
GROUP BY endpoint;
```

### Admin Dashboard

Access at: https://dev.kairix.net/admin

The Telemetry tab provides:
- Real-time metrics visualization
- Interactive time range selection
- Request timeline charts
- Endpoint distribution analysis

## Performance Impact

- **Minimal overhead**: Database writes are async via middleware
- **Efficient storage**: SQLite with proper indexes
- **Automatic cleanup**: Configurable data retention
- **Non-blocking**: Server continues if telemetry fails

## Future Enhancements

Potential additions:
- [ ] Model-specific token cost tracking
- [ ] Perceptor performance metrics
- [ ] Real-time alerting on error rates
- [ ] Export telemetry data (CSV, JSON)
- [ ] Integration with external monitoring (Prometheus, Grafana)
- [ ] Automated health snapshots at intervals
- [ ] Request/response payload sampling for debugging

## Files Modified

### New Files Created:
- `kairix-apps/src/kairix_apps/telemetry_manager.py`
- `kairix-apps/src/kairix_apps/db_wrapper.py`
- `kairix-apps/test_telemetry.py`
- `SHADOW_ENVIRONMENT_SETUP.md`
- `TELEMETRY_IMPLEMENTATION_SUMMARY.md`

### Files Modified:
- `kairix-apps/src/kairix_apps/server.py`
  - Added telemetry imports
  - Added TelemetryMiddleware class
  - Added telemetry initialization
  - Added telemetry API endpoints
- `kairix-apps/src/kairix_apps/admin_template.html`
  - Added Chart.js CDN import
  - Added Telemetry tab button
  - Added telemetry tab content
  - Added loadTelemetry() JavaScript function

## Notes

- Telemetry data is stored separately from conversation/reflection data
- Shadow environment enforces read-only access at DB connection level
- All linting issues resolved (except pre-existing ones)
- Tests confirm full functionality
- Ready for deployment to coalinga

---

**Implementation completed:** 2025-10-30
**Status:** ✅ All features implemented and tested
**Next steps:** Deploy to production and set up shadow environment
