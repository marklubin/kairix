# Kairix SRE Agent - Quick Reference

## 🚀 Quick Start
```bash
# First time setup
cd kairix-sre-agent
just install
export OPENAI_API_KEY="your-key"

# Run health check
just sre-run

# View status
just sre-status
```

## 📋 Common Commands

| Command | Description | When to Use |
|---------|-------------|-------------|
| `just sre-run` | Run full health check | Manual monitoring |
| `just sre-status` | View recent runs | Check agent history |
| `just sre-services` | List all services | Verify configuration |
| `just sre-shell` | Interactive mode | Investigate issues |
| `just logs` | View agent logs | Debug problems |
| `just sre-debug` | Verbose run | Troubleshooting |

## 🔍 Quick Diagnostics

### Is the agent running?
```bash
# Check last run
just sre-status --hours 1

# Check cron
crontab -l | grep kairix

# Check process
pgrep -f sre_agent
```

### Which services are monitored?
```bash
just sre-services
```

### Is a specific service healthy?
```bash
# Quick HTTP check
curl -I http://localhost:6010/  # UI
curl -I http://localhost:7010/api/status  # API

# Or use the shell
just sre-shell
> /check f_api
```

### View recent errors
```bash
# Agent errors
grep ERROR ~/kairix/logs/sre-agent/*.log | tail -20

# Service errors (example for user 'f')
grep ERROR /var/log/kairix/f/*.log | tail -20
```

## 🚨 Emergency Commands

### Stop automated runs
```bash
# Disable cron
crontab -l | grep -v kairix | crontab -

# Or stop systemd
sudo systemctl stop kairix-sre-agent
```

### Reset agent state
```bash
# Clear history (destructive!)
rm ~/.kairix/sre-agent.db

# Clear logs
rm ~/kairix/logs/sre-agent/*.log
```

### Manual service check
```bash
# Check all ports
for p in {6010..6014}; do echo -n "Port $p: "; curl -s -o /dev/null -w "%{http_code}\n" http://localhost:$p/ || echo "DOWN"; done
```

## 📁 Important Paths

| Path | Description |
|------|-------------|
| `~/kairix/caddyfile` | Service configuration source |
| `~/.kairix/sre-agent.db` | Agent memory/history |
| `~/kairix/logs/sre-agent/` | Agent logs |
| `/var/log/kairix/*/` | Service logs |

## 🔧 Configuration

### Add new user
1. Edit `~/kairix/caddyfile`
2. Add user block with ports
3. Agent auto-discovers on next run

### Change check frequency
```bash
# Edit cron (default: 5 minutes)
crontab -e
# Change */5 to */10 for 10 minutes
```

### Set OpenAI key permanently
```bash
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc
source ~/.zshrc
```

## 📊 Understanding Output

### Health Status Table
```
┏━━━━━━━━━━┳━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Service  ┃ Port ┃ Status  ┃ Response Time ┃
┡━━━━━━━━━━╇━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ f_api    │ 7010 │ healthy │ 15.2ms        │  ← Good
│ f_ui     │ 6010 │ down    │ N/A           │  ← Problem!
```

### Log Analysis Scores
- **90-100**: Excellent health
- **70-89**: Minor issues
- **50-69**: Degraded performance
- **0-49**: Critical issues

### Run Status
- `completed`: Successful run
- `failed`: Error during execution
- `running`: Currently executing

## 💡 Pro Tips

1. **Use shell for exploration**
   ```bash
   just sre-shell
   > What services had issues today?
   > Show me error patterns for chris_api
   ```

2. **Combine with system tools**
   ```bash
   # Watch live status
   watch -n 60 'just sre-status --hours 1'
   ```

3. **Debug specific service**
   ```bash
   # In shell
   just sre-shell
   > /check f_api
   > /logs f_api
   ```

4. **Export findings**
   ```bash
   just sre-status > report.txt
   ```

---
*Need more help? See RUNBOOK.md for detailed troubleshooting*