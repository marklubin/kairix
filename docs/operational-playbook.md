# Kairix Operational Playbook

This playbook provides essential procedures for running Kairix in production, handling common scenarios, and troubleshooting issues.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Procedures](#deployment-procedures)
3. [Daily Operations](#daily-operations)
4. [Monitoring & Alerts](#monitoring--alerts)
5. [Incident Response](#incident-response)
6. [Maintenance Procedures](#maintenance-procedures)
7. [Disaster Recovery](#disaster-recovery)
8. [Security Operations](#security-operations)

## Pre-Deployment Checklist

### System Requirements Verification
- [ ] Python 3.10+ installed
- [ ] Docker & Docker Compose installed
- [ ] Minimum 4GB RAM available
- [ ] 10GB+ disk space free
- [ ] Ports 8080, 3000, 7687 available
- [ ] SSL certificates ready (for production)

### Configuration Review
- [ ] `.env` file configured with secure passwords
- [ ] Neo4j password changed from default
- [ ] API keys generated and stored securely
- [ ] Backup destination configured
- [ ] Log rotation configured

### Security Checklist
- [ ] Firewall rules configured
- [ ] SSL/TLS enabled
- [ ] Authentication enabled
- [ ] Default credentials changed
- [ ] Security headers configured

## Deployment Procedures

### Initial Deployment

```bash
# 1. Clone repository
git clone https://github.com/kairix/kairix.git
cd kairix

# 2. Create environment file
cp .env.example .env
# Edit .env with production values

# 3. Start infrastructure
docker-compose up -d neo4j

# 4. Wait for Neo4j to be ready
./scripts/wait-for-neo4j.sh

# 5. Install dependencies
uv sync

# 6. Run database migrations
uv run python -m kairix_core.db.migrate

# 7. Start backend server
uv run python -m kairix_apps.server &

# 8. Start frontend (production build)
cd kairix-apps/client
npm install
npm run build
npm run start &
```

### Docker Deployment (Beta)

```bash
# Deploy single instance
docker-compose -f docker-compose.prod.yml up -d

# Deploy multiple instances (containerized)
./scripts/deploy-instance.sh user1
./scripts/deploy-instance.sh user2
```

### Health Verification

```bash
# Check all services
curl http://localhost:8080/health
curl http://localhost:3000

# Verify Neo4j
docker exec kairix-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n) RETURN count(n) as nodeCount"

# Test chat endpoint
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"model":"kairix-gpt-4","messages":[{"role":"user","content":"test"}],"agent_id":"test"}'
```

## Daily Operations

### Morning Checklist (9 AM)

1. **Check Service Health**
   ```bash
   ./scripts/health-check.sh
   ```

2. **Review Overnight Logs**
   ```bash
   ./scripts/log-summary.sh --since "24 hours ago"
   ```

3. **Check Disk Space**
   ```bash
   df -h | grep -E "/$|/var|/data"
   ```

4. **Verify Backup Success**
   ```bash
   ls -la /backups/$(date +%Y-%m-%d)*
   ```

### Monitoring Dashboard

Access monitoring at: http://localhost:8080/admin/monitoring

Key Metrics to Watch:
- Response time (target: <500ms p95)
- Memory usage (alert: >80%)
- Active connections (normal: 10-50)
- Error rate (alert: >1%)
- Database size growth

### User Management

**Add New User**
```bash
uv run python -m kairix_core.cli user create \
  --username "newuser" \
  --email "user@example.com"
```

**Reset User Password**
```bash
uv run python -m kairix_core.cli user reset-password \
  --username "username"
```

**View User Activity**
```bash
uv run python -m kairix_core.cli user activity \
  --username "username" \
  --days 7
```

## Monitoring & Alerts

### Log Locations

- Backend logs: `/var/log/kairix/backend.log`
- Frontend logs: `/var/log/kairix/frontend.log`
- Neo4j logs: `/var/log/neo4j/`
- Nginx logs: `/var/log/nginx/`

### Key Log Patterns to Monitor

**Errors**
```bash
tail -f /var/log/kairix/backend.log | grep -E "ERROR|CRITICAL"
```

**Slow Queries**
```bash
grep "duration_ms.*[0-9]{4,}" /var/log/kairix/backend.log
```

**Failed Authentications**
```bash
grep "auth_failed" /var/log/kairix/backend.log
```

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| CPU Usage | 70% | 90% | Scale up/optimize |
| Memory Usage | 75% | 90% | Restart services |
| Disk Usage | 80% | 95% | Clean logs/data |
| Response Time | 1s | 3s | Check database |
| Error Rate | 1% | 5% | Check logs |
| Queue Depth | 100 | 500 | Scale workers |

## Incident Response

### Service Down

1. **Identify affected service**
   ```bash
   ./scripts/service-status.sh
   ```

2. **Check logs for errors**
   ```bash
   tail -n 1000 /var/log/kairix/backend.log | grep ERROR
   ```

3. **Restart service**
   ```bash
   # Backend
   systemctl restart kairix-backend
   
   # Frontend
   systemctl restart kairix-frontend
   
   # Neo4j
   docker-compose restart neo4j
   ```

4. **Verify recovery**
   ```bash
   ./scripts/health-check.sh
   ```

### Database Issues

**Connection Errors**
```bash
# Check Neo4j status
docker-compose ps neo4j

# View Neo4j logs
docker-compose logs --tail=100 neo4j

# Restart if needed
docker-compose restart neo4j
```

**Performance Issues**
```bash
# Check query performance
docker exec kairix-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.listQueries()"

# Kill long-running queries
docker exec kairix-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.killQuery('query-id')"
```

### Memory Leaks

1. **Identify process**
   ```bash
   ps aux | grep kairix | sort -k4 -r
   ```

2. **Get memory profile**
   ```bash
   ./scripts/memory-profile.sh <pid>
   ```

3. **Restart with monitoring**
   ```bash
   systemctl restart kairix-backend
   watch -n 5 'ps aux | grep kairix'
   ```

## Maintenance Procedures

### Weekly Maintenance

**Sunday 2 AM - 4 AM**

1. **Backup Database**
   ```bash
   ./scripts/backup-neo4j.sh
   ```

2. **Clean Old Logs**
   ```bash
   find /var/log/kairix -name "*.log.*" -mtime +30 -delete
   ```

3. **Update Dependencies**
   ```bash
   cd /opt/kairix
   git pull
   uv sync
   ```

4. **Database Optimization**
   ```bash
   docker exec kairix-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
     "CALL db.checkpoint()"
   ```

### Monthly Maintenance

1. **Full System Backup**
2. **Security Updates**
3. **Performance Review**
4. **Capacity Planning**

## Disaster Recovery

### Backup Procedures

**Automated Daily Backups**
```bash
# Cron job (add to crontab)
0 2 * * * /opt/kairix/scripts/daily-backup.sh
```

**Manual Backup**
```bash
# Stop writes (optional)
./scripts/maintenance-mode.sh enable

# Backup database
docker exec kairix-neo4j neo4j-admin dump --database=neo4j --to=/backups/neo4j-$(date +%Y%m%d).dump

# Backup application data
tar -czf /backups/kairix-data-$(date +%Y%m%d).tar.gz /opt/kairix/data

# Resume normal operation
./scripts/maintenance-mode.sh disable
```

### Recovery Procedures

**Database Recovery**
```bash
# Stop services
docker-compose down

# Restore database
docker run -v /backups:/backups neo4j:latest \
  neo4j-admin load --from=/backups/neo4j-20240115.dump --database=neo4j --force

# Start services
docker-compose up -d
```

**Full System Recovery**
```bash
# 1. Provision new server
# 2. Install dependencies
# 3. Restore from backup
./scripts/restore-from-backup.sh /backups/kairix-full-20240115.tar.gz

# 4. Verify data integrity
./scripts/verify-backup.sh

# 5. Update DNS/load balancer
# 6. Test functionality
```

## Security Operations

### Security Monitoring

**Check for Suspicious Activity**
```bash
# Failed login attempts
grep "auth_failed" /var/log/kairix/backend.log | tail -20

# Unusual API usage
./scripts/api-usage-report.sh --anomalies

# Database access patterns
./scripts/db-audit.sh --last-hour
```

### Security Updates

```bash
# Check for vulnerabilities
uv pip audit

# Update dependencies
uv sync --upgrade

# Apply system updates
apt update && apt upgrade -y
```

### Access Control Review

Monthly tasks:
1. Review user permissions
2. Rotate API keys
3. Update firewall rules
4. Review access logs

## Common Issues & Solutions

### Issue: High Memory Usage

**Symptoms**: OOM errors, slow responses

**Solution**:
```bash
# 1. Identify memory consumers
ps aux | sort -k4 -r | head -10

# 2. Check for memory leaks
./scripts/memory-analysis.sh

# 3. Restart services
systemctl restart kairix-backend

# 4. Adjust memory limits
export KAIRIX_MAX_MEMORY=4G
```

### Issue: Slow Response Times

**Symptoms**: >1s response times

**Solution**:
```bash
# 1. Check database queries
./scripts/slow-query-log.sh

# 2. Review indexes
docker exec kairix-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL db.indexes()"

# 3. Clear caches if needed
./scripts/clear-caches.sh
```

### Issue: Connection Refused

**Symptoms**: Can't connect to services

**Solution**:
```bash
# 1. Check service status
systemctl status kairix-*

# 2. Verify ports
netstat -tlnp | grep -E "8080|3000|7687"

# 3. Check firewall
iptables -L -n | grep -E "8080|3000|7687"

# 4. Review logs
journalctl -u kairix-backend -n 100
```

## Performance Tuning

### Neo4j Optimization

```bash
# Edit neo4j.conf
dbms.memory.heap.max_size=2G
dbms.memory.pagecache.size=2G
dbms.connector.bolt.thread_pool_max_size=400
```

### Backend Optimization

```python
# Environment variables
KAIRIX_WORKERS=4
KAIRIX_MAX_CONNECTIONS=100
KAIRIX_CACHE_SIZE=1000
KAIRIX_REQUEST_TIMEOUT=30
```

### Frontend Optimization

```javascript
// Build optimizations
npm run build -- --mode production
```

## Runbook Template

For each new feature/service, create a runbook:

1. **Service Description**
2. **Dependencies**
3. **Start/Stop Procedures**
4. **Health Checks**
5. **Common Issues**
6. **Escalation Path**
7. **Recovery Procedures**

## Contact Information

**On-Call Schedule**: See PagerDuty

**Escalation Path**:
1. L1: On-call engineer
2. L2: Backend team lead
3. L3: CTO

**Key Contacts**:
- Database Admin: dba@kairix.ai
- Security: security@kairix.ai
- Infrastructure: infra@kairix.ai