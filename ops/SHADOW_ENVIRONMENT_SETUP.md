# Shadow Environment Setup Guide

This guide explains how to set up a shadow environment on coalinga for safe testing without affecting the production database.

## Overview

The shadow environment is a parallel instance of the Kairix server that:
- **Reads** from the production conversation and reflection databases
- **Never writes** to those databases (enforced at the code level)
- Handles requests identically to production
- Can be used for testing new features safely

## Architecture

```
Production Server (port 8000)
├── DB: .kairix/convo_history.db (READ/WRITE)
├── DB: .kairix/reflections.db (READ/WRITE)
└── Telemetry: .kairix/telemetry.db (WRITE)

Shadow Server (port 8889)
├── DB: .kairix/convo_history.db (READ ONLY)
├── DB: .kairix/reflections.db (READ ONLY)
└── Telemetry: .kairix/telemetry-shadow.db (WRITE)
```

## Setup Steps on Coalinga

### 1. Set Up Doppler Configuration for Shadow

```bash
# Switch to shadow environment config
doppler setup --project kairix --config coalinga-shadow

# Set required environment variables
doppler secrets set KAIRIX_ENVIRONMENT=shadow
doppler secrets set KAIRIX_DB_READ_ONLY=true
doppler secrets set KAIRIX_SERVER_PORT=8889
doppler secrets set TELEMETRY_DB_PATH=.kairix/telemetry-shadow.db

# Copy other necessary secrets from production
doppler secrets get --config coalinga | doppler secrets set --config coalinga-shadow
```

### 2. Create SystemD Service for Shadow

Create `/etc/systemd/system/kairix-server-shadow.service`:

```ini
[Unit]
Description=Kairix Shadow Server
After=network.target

[Service]
Type=simple
User=kairix
Group=kairix
WorkingDirectory=/home/kairix/kairix
Environment="PATH=/home/kairix/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/kairix/.local/bin/doppler run --config coalinga-shadow -- /home/kairix/kairix/kairix-apps/.venv/bin/python -m kairix_apps.server
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 3. Configure Caddy Reverse Proxy

Add to Caddyfile:

```caddyfile
# Shadow environment endpoint
dev.kairix.net {
    # Existing production route
    reverse_proxy /api/* localhost:8000

    # Shadow environment route
    reverse_proxy /shadow/* {
        to localhost:8889
        # Strip /shadow prefix
        rewrite * /api{uri}
    }
}
```

### 4. Start and Enable Shadow Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start shadow service
sudo systemctl start kairix-server-shadow

# Enable on boot
sudo systemctl enable kairix-server-shadow

# Check status
sudo systemctl status kairix-server-shadow

# View logs
sudo journalctl -u kairix-server-shadow -f
```

### 5. Test Shadow Environment

```bash
# Test from coalinga
curl http://localhost:8889/health

# Test from external (after Caddy config)
curl https://dev.kairix.net/shadow/health
```

## Verification

### Verify Read-Only Database Access

Check server logs on startup for:
```
Database .kairix/convo_history.db opened in READ-ONLY mode (shadow environment)
Running in SHADOW environment - telemetry active, DB access read-only
```

### Test Write Operations Fail

Try to make a request - it should work, but internal write operations should be blocked:
```bash
curl -X POST https://dev.kairix.net/shadow/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"kairix-conversational","messages":[{"role":"user","content":"test"}],"stream":false}'
```

The response should work, but check logs - any database write attempts should be logged as blocked.

## Monitoring

### Check Both Services

```bash
# Production status
sudo systemctl status kairix-server-mark

# Shadow status
sudo systemctl status kairix-server-shadow
```

### Compare Telemetry

- Production telemetry: https://dev.kairix.net/admin (Telemetry tab)
- Shadow has separate telemetry DB for tracking shadow requests

## Troubleshooting

### Shadow Service Won't Start

1. Check logs: `sudo journalctl -u kairix-server-shadow -n 50`
2. Verify Doppler config: `doppler secrets --config coalinga-shadow`
3. Check port availability: `sudo ss -tulpn | grep 8889`

### Database Permission Errors

Shadow should never write - if you see permission errors on DB writes, that's expected and correct behavior. The application should handle `ReadOnlyDatabaseError` gracefully.

### Telemetry Not Working

Check that `TELEMETRY_DB_PATH` is set correctly and points to a different file than production.

## Rollback

To disable shadow environment:

```bash
# Stop service
sudo systemctl stop kairix-server-shadow
sudo systemctl disable kairix-server-shadow

# Remove Caddy config for /shadow/*
# Reload Caddy
sudo systemctl reload caddy
```

## Notes

- Shadow environment uses the same codebase as production
- Only configuration differs (environment variables via Doppler)
- Both can run simultaneously on different ports
- Shadow is perfect for testing new features without risk
- Telemetry tracks shadow requests separately
