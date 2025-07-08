# Kairix SRE Agent Runbook

## Table of Contents
1. [Overview](#overview)
2. [How the Agent Runs](#how-the-agent-runs)
3. [Monitoring and Logs](#monitoring-and-logs)
4. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
5. [Emergency Procedures](#emergency-procedures)
6. [Maintenance Tasks](#maintenance-tasks)

## Overview

The Kairix SRE Agent is an AI-powered monitoring system that:
- Automatically discovers services from Caddyfile
- Performs health checks on all user services
- Analyzes logs for errors and anomalies
- Attempts basic recovery actions
- Maintains 24-hour historical context

### Architecture
```
Caddyfile → Parser → Config → Health Checker → Recovery Actions
                           ↓
                      Log Analyzer → Memory Store (SQLite)
                           ↓
                      OpenAI API → Intelligent Decisions
```

## How the Agent Runs

### Execution Methods

#### 1. Manual One-Shot Run
```bash
just sre-run
# or with verbose logging
just sre-debug
```
- Runs once and exits
- Takes ~30-60 seconds
- Best for testing or manual checks

#### 2. Scheduled via Cron (RECOMMENDED)
```bash
# Install cron job (runs every 5 minutes)
just install-cron

# View cron entry
crontab -l | grep kairix

# Expected output:
*/5 * * * * cd /Users/mark/kairix/kairix-sre-agent && /path/to/uv run python -m sre_agent.main run >> /var/log/kairix/sre-agent/cron.log 2>&1
```

#### 3. Systemd Service (Linux servers)
```bash
# Install service
just install-service

# Enable and start
sudo systemctl enable --now kairix-sre-agent

# Check status
sudo systemctl status kairix-sre-agent
```

#### 4. Interactive Shell (Debugging)
```bash
just sre-shell
# Commands: /help, /status, /check, /logs, /exit
```

### Run Lifecycle

1. **Startup** (0-2s)
   ```
   Load Caddyfile → Parse services → Initialize memory → Connect OpenAI
   ```

2. **Discovery** (2-5s)
   ```
   Read 24h history → Build context → Plan health checks
   ```

3. **Health Checks** (5-20s)
   ```
   HTTP checks → Process checks → Port scans → Log analysis
   ```

4. **Recovery** (20-30s)
   ```
   Identify issues → Attempt fixes → Send alerts
   ```

5. **Reporting** (30-35s)
   ```
   Update memory → Write logs → Display summary → Exit
   ```

## Monitoring and Logs

### Log Locations

```bash
# Agent's own logs
~/kairix/logs/sre-agent/
├── agent.log       # Main agent activity
├── cron.log        # Cron execution logs
└── errors.log      # Error details

# Service logs (analyzed by agent)
/var/log/kairix/
├── f/
│   ├── f_ui.log
│   ├── f_api.log
│   └── f_tools.log
├── chris/
│   └── ...
└── [other users]/
```

### Viewing Logs

```bash
# View recent agent activity
tail -f ~/kairix/logs/sre-agent/agent.log

# View last 50 lines
just logs

# View cron execution
tail -f ~/kairix/logs/sre-agent/cron.log

# Check for errors
grep ERROR ~/kairix/logs/sre-agent/*.log
```

### Key Log Patterns

```bash
# Successful run
2025-01-07T10:00:00 [info] Starting SRE Agent health check...
2025-01-07T10:00:02 [info] Loaded 15 services from Caddyfile
2025-01-07T10:00:30 [info] Health check complete: 15 services checked, 2 issues found

# Failed run
2025-01-07T10:00:00 [error] OpenAI API error: Invalid API key
2025-01-07T10:00:00 [error] Health check failed: Error: Invalid API key

# Service down
2025-01-07T10:00:10 [warning] Service chris_api (port 7011) is down
2025-01-07T10:00:15 [info] Attempting to restart chris_api
```

## Common Issues and Troubleshooting

### 1. Agent Won't Start

**Symptom**: `just sre-run` fails immediately

**Diagnosis**:
```bash
# Check Python environment
uv run python --version

# Check dependencies
uv sync

# Test config loading
uv run python -c "from sre_agent.config import get_default_config; print('OK')"
```

**Common Causes**:
- Missing dependencies → Run `just install`
- Permission errors → Check log directory permissions
- Invalid Caddyfile → Verify syntax

### 2. "No services found" or Wrong Services

**Symptom**: Agent reports 0 services or shows default services

**Diagnosis**:
```bash
# Check Caddyfile location
ls -la ~/kairix/caddyfile

# Test parser directly
uv run python -c "from sre_agent.caddyfile_parser import CaddyfileParser; p = CaddyfileParser(); print(p.parse_services())"

# View detected services
just sre-services
```

**Common Causes**:
- Caddyfile in wrong location → Should be at `~/kairix/caddyfile`
- Invalid Caddyfile format → Check for syntax errors
- Parser regex mismatch → Ensure standard Caddy format

### 3. OpenAI API Errors

**Symptom**: "Invalid API key" or "Rate limit exceeded"

**Diagnosis**:
```bash
# Check API key is set
echo $OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json"
```

**Solutions**:
- Set API key: `export OPENAI_API_KEY="sk-..."`
- Add to shell profile: `echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc`
- Check OpenAI dashboard for usage/limits

### 4. Service Health Checks Fail

**Symptom**: All services show as "down" or "error"

**Diagnosis**:
```bash
# Test manual health check
curl -I http://localhost:6010/
curl -I http://localhost:7010/api/status

# Check if services are running
lsof -i :6010-6015 | grep LISTEN
ps aux | grep -E "vite|uvicorn|npm"
```

**Common Causes**:
- Services actually down → Start them manually
- Wrong endpoints → Check Caddyfile paths
- Firewall blocking → Check iptables/pf rules

### 5. Log Analysis Errors

**Symptom**: "Log file not found" or empty analysis

**Diagnosis**:
```bash
# Check log directories exist
ls -la /var/log/kairix/

# Check log file permissions
ls -la /var/log/kairix/*/

# Test log analysis
uv run python -c "from sre_agent.logs.analyzer import LogAnalyzer; from sre_agent.config import get_default_config; a = LogAnalyzer(get_default_config()); print(a.analyze_logs('f_api', 'f', 30))"
```

**Solutions**:
- Create log directories: `sudo mkdir -p /var/log/kairix/{f,chris,allie,demo,nb}`
- Fix permissions: `sudo chown -R $USER:staff /var/log/kairix`
- Ensure services write to correct log paths

### 6. Memory/Database Issues

**Symptom**: "Database locked" or historical data missing

**Diagnosis**:
```bash
# Check database file
ls -la ~/.kairix/sre-agent.db

# Test database access
sqlite3 ~/.kairix/sre-agent.db "SELECT COUNT(*) FROM runs;"

# Check for locks
lsof ~/.kairix/sre-agent.db
```

**Solutions**:
- Remove stale lock: `rm ~/.kairix/sre-agent.db-journal`
- Reset database: `rm ~/.kairix/sre-agent.db` (loses history)
- Check disk space: `df -h ~`

### 7. Cron Job Not Running

**Symptom**: No automatic runs happening

**Diagnosis**:
```bash
# Check cron is running
pgrep cron

# Check cron logs (macOS)
log show --predicate 'process == "cron"' --last 1h

# Check cron logs (Linux)
grep CRON /var/log/syslog

# Test cron command manually
cd /Users/mark/kairix/kairix-sre-agent && /path/to/uv run python -m sre_agent.main run
```

**Solutions**:
- Ensure cron service is running
- Check PATH in cron environment
- Add full paths to commands
- Check mail for cron errors: `mail`

## Emergency Procedures

### All Services Down
```bash
# 1. Get immediate status
just sre-status

# 2. Run manual check with verbose output
just sre-debug

# 3. Check each service manually
for port in 6010 6011 6012 6013 6014; do
  echo "Checking port $port:"
  curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/ || echo "DOWN"
done

# 4. Restart all services (example)
cd ~/kairix/kairix-apps && just restart-all
```

### Agent Crash Loop
```bash
# 1. Disable automated runs
crontab -l | grep -v kairix | crontab -
# or
sudo systemctl stop kairix-sre-agent

# 2. Run in debug mode
just sre-debug

# 3. Check for corrupted state
rm ~/.kairix/sre-agent.db
rm ~/kairix/logs/sre-agent/*.log

# 4. Test with minimal config
OPENAI_API_KEY="" uv run python test_demo.py
```

### High Error Rate Detected
```bash
# 1. Check which services are affected
just sre-shell
/logs  # In the shell

# 2. Tail service logs
tail -f /var/log/kairix/*/*.log | grep -E "ERROR|CRITICAL"

# 3. Check system resources
top
df -h
free -m  # Linux
vm_stat  # macOS
```

## Maintenance Tasks

### Daily
- Review agent status: `just sre-status`
- Check for persistent issues
- Verify cron is running

### Weekly
- Review error patterns in logs
- Check disk space for logs
- Update service configurations if needed

### Monthly
- Rotate logs to prevent disk filling
- Review and optimize OpenAI usage
- Update agent code if new version available

### Log Rotation Setup
```bash
# Create logrotate config (Linux)
sudo tee /etc/logrotate.d/kairix-sre <<EOF
/var/log/kairix/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}

/home/*/kairix/logs/sre-agent/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
EOF

# macOS: Use newsyslog
sudo tee -a /etc/newsyslog.conf <<EOF
/var/log/kairix/*/*.log    644  7    *    @T00  J
EOF
```

### Monitoring the Monitor
```bash
# Add a cron job to ensure SRE agent is running
*/30 * * * * pgrep -f "sre_agent.main" || echo "SRE Agent not running!" | mail -s "SRE Agent Alert" your@email.com
```

## Quick Reference

### Essential Commands
```bash
just sre-run         # Run health check
just sre-status      # View recent runs
just sre-services    # List monitored services
just sre-shell       # Interactive mode
just logs            # View agent logs
```

### Health Check Flow
```
Caddyfile → Services → Health Checks → Issues? → Recovery → Alert → Log
```

### Service Naming Convention
```
{username}_{service_type}
Examples: f_api, chris_ui, demo_tools
```

### Port Ranges
- UI: 6010-6019
- API: 7010-7019
- Tools: 8010-8019

### Required Environment
```bash
OPENAI_API_KEY=sk-...           # OpenAI API key
DISCORD_WEBHOOK_URL=https://... # Optional: Discord alerts
```

## Contact

For issues not covered in this runbook:
1. Check agent logs for detailed errors
2. Run in debug mode for more context
3. Review recent code changes in git log
4. Contact SRE team lead

---

*Last updated: 2025-07-07*
*Version: 1.0.0*