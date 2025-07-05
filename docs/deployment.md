# Kairix Deployment Guide

This guide covers various deployment options for Kairix, from local development to production environments.

## Deployment Options Overview

1. **Local Development**: Single machine, development mode
2. **Docker Deployment**: Containerized, single instance
3. **Multi-User Docker**: Multiple isolated instances
4. **Cloud Deployment**: AWS/GCP/Azure ready
5. **Kubernetes**: Scalable production deployment

## Prerequisites

### System Requirements

**Minimum (Development)**
- 4 CPU cores
- 8GB RAM
- 20GB storage
- Ubuntu 20.04+ / macOS 12+ / Windows WSL2

**Recommended (Production)**
- 8+ CPU cores
- 16GB+ RAM
- 100GB+ SSD storage
- Ubuntu 22.04 LTS

### Software Dependencies

```bash
# Required
- Python 3.10+
- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+
- Git

# Optional
- Nginx (reverse proxy)
- Certbot (SSL certificates)
- Prometheus (monitoring)
```

## Local Development Deployment

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/kairix/kairix.git
cd kairix

# 2. Setup environment
cp .env.example .env
# Edit .env with your settings

# 3. Start Neo4j
docker-compose up -d neo4j

# 4. Install dependencies
uv sync

# 5. Run migrations
uv run python -m kairix_core.db.migrate

# 6. Start backend
uv run python -m kairix_apps.server

# 7. Start frontend (new terminal)
cd kairix-apps/client
npm install
npm run dev
```

### Development Configuration

`.env` file:
```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=localpassword

# API
KAIRIX_HOST=0.0.0.0
KAIRIX_PORT=8080
KAIRIX_LOG_LEVEL=DEBUG

# Frontend
VITE_API_URL=http://localhost:8080
```

## Docker Deployment (Single Instance)

### Build and Run

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Production Docker Compose

`docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15
    restart: always
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=2G
    healthcheck:
      test: ["CMD", "neo4j", "status"]
      interval: 30s
      timeout: 10s
      retries: 3

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    restart: always
    ports:
      - "8080:8080"
    depends_on:
      neo4j:
        condition: service_healthy
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USERNAME=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - KAIRIX_LOG_LEVEL=INFO
    volumes:
      - app_logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./kairix-apps/client
      dockerfile: Dockerfile
    restart: always
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
    environment:
      - VITE_API_URL=http://backend:8080

volumes:
  neo4j_data:
  neo4j_logs:
  app_logs:
```

## Multi-User Docker Deployment

### Deployment Script

`scripts/deploy-user.sh`:
```bash
#!/bin/bash
set -e

USER_ID=$1
if [ -z "$USER_ID" ]; then
    echo "Usage: ./deploy-user.sh <user_id>"
    exit 1
fi

# Create user-specific directory
mkdir -p /opt/kairix/users/$USER_ID

# Generate unique ports
NEO4J_PORT=$((7687 + $USER_ID))
API_PORT=$((8080 + $USER_ID))
WEB_PORT=$((3000 + $USER_ID))

# Create user-specific docker-compose
cat > /opt/kairix/users/$USER_ID/docker-compose.yml <<EOF
version: '3.8'

services:
  neo4j-$USER_ID:
    image: neo4j:5.15
    restart: always
    ports:
      - "$NEO4J_PORT:7687"
    volumes:
      - ./neo4j_data:/data
    environment:
      - NEO4J_AUTH=neo4j/\${NEO4J_PASSWORD_$USER_ID}
      - NEO4J_dbms_memory_heap_max__size=1G

  backend-$USER_ID:
    image: kairix/backend:latest
    restart: always
    ports:
      - "$API_PORT:8080"
    environment:
      - NEO4J_URI=bolt://neo4j-$USER_ID:7687
      - NEO4J_USERNAME=neo4j
      - NEO4J_PASSWORD=\${NEO4J_PASSWORD_$USER_ID}
      - AGENT_PREFIX=user-$USER_ID

  frontend-$USER_ID:
    image: kairix/frontend:latest
    restart: always
    ports:
      - "$WEB_PORT:3000"
    environment:
      - VITE_API_URL=http://backend-$USER_ID:8080
EOF

# Start user instance
cd /opt/kairix/users/$USER_ID
docker-compose up -d

echo "User $USER_ID deployed:"
echo "  Web UI: http://localhost:$WEB_PORT"
echo "  API: http://localhost:$API_PORT"
```

### Nginx Configuration

`/etc/nginx/sites-available/kairix`:
```nginx
# User routing
server {
    listen 80;
    server_name kairix.example.com;

    # User 1
    location /user1/ {
        proxy_pass http://localhost:3001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # User 2
    location /user2/ {
        proxy_pass http://localhost:3002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Add more users as needed
}
```

## Cloud Deployment

### AWS Deployment

**1. EC2 Setup**

```bash
# Launch EC2 instance (Ubuntu 22.04, t3.large minimum)
# Security groups: 22 (SSH), 80 (HTTP), 443 (HTTPS)

# Connect and setup
ssh ubuntu@your-ec2-ip
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**2. RDS for Neo4j (Alternative)**

```bash
# Use Neo4j Aura or deploy Neo4j on EC2
# Update connection strings in .env
NEO4J_URI=neo4j+s://your-neo4j-instance.cloud:7687
```

**3. S3 for Backups**

```bash
# Configure AWS CLI
aws configure

# Backup script
aws s3 sync /opt/kairix/backups s3://your-backup-bucket/kairix/
```

### Google Cloud Deployment

**1. Compute Engine Setup**

```bash
# Create VM instance
gcloud compute instances create kairix-server \
    --machine-type=n2-standard-4 \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=100GB
```

**2. Cloud SQL (if using managed database)**

```bash
# Create Cloud SQL instance
gcloud sql instances create kairix-db \
    --database-version=POSTGRES_14 \
    --tier=db-g1-small \
    --region=us-central1
```

### Azure Deployment

**1. VM Setup**

```bash
# Create resource group
az group create --name kairix-rg --location eastus

# Create VM
az vm create \
    --resource-group kairix-rg \
    --name kairix-vm \
    --image Ubuntu2204 \
    --size Standard_D4s_v3 \
    --admin-username azureuser \
    --generate-ssh-keys
```

## Kubernetes Deployment

### Kubernetes Manifests

`k8s/namespace.yaml`:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kairix
```

`k8s/neo4j-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: neo4j
  namespace: kairix
spec:
  serviceName: neo4j
  replicas: 1
  selector:
    matchLabels:
      app: neo4j
  template:
    metadata:
      labels:
        app: neo4j
    spec:
      containers:
      - name: neo4j
        image: neo4j:5.15
        ports:
        - containerPort: 7687
        - containerPort: 7474
        env:
        - name: NEO4J_AUTH
          valueFrom:
            secretKeyRef:
              name: neo4j-secret
              key: auth
        volumeMounts:
        - name: data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
```

`k8s/backend-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kairix-backend
  namespace: kairix
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: kairix/backend:latest
        ports:
        - containerPort: 8080
        env:
        - name: NEO4J_URI
          value: "bolt://neo4j:7687"
        - name: NEO4J_USERNAME
          value: "neo4j"
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: neo4j-secret
              key: password
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
```

### Helm Chart

```bash
# Install with Helm
helm install kairix ./helm/kairix \
    --namespace kairix \
    --create-namespace \
    --set neo4j.password=secure-password \
    --set ingress.host=kairix.example.com
```

## SSL/TLS Configuration

### Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d kairix.example.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Nginx SSL Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name kairix.example.com;

    ssl_certificate /etc/letsencrypt/live/kairix.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/kairix.example.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Environment Variables Reference

### Backend Environment Variables

```bash
# Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=secure-password
NEO4J_DATABASE=neo4j

# Server
KAIRIX_HOST=0.0.0.0
KAIRIX_PORT=8080
KAIRIX_WORKERS=4
KAIRIX_LOG_LEVEL=INFO

# Security
JWT_SECRET_KEY=your-secret-key
API_KEY_SALT=your-salt

# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_HOST=http://localhost:11434

# Features
ENABLE_VOICE=true
ENABLE_REFLECTIONS=true
MAX_MEMORY_DEPTH=100

# Storage
UPLOAD_DIR=/app/uploads
BACKUP_DIR=/app/backups
```

### Frontend Environment Variables

```bash
# API Connection
VITE_API_URL=http://localhost:8080
VITE_WS_URL=ws://localhost:8080

# Features
VITE_ENABLE_VOICE=true
VITE_ENABLE_DEBUG=false

# Analytics (optional)
VITE_GA_ID=UA-XXXXX-Y
```

## Backup and Recovery

### Automated Backups

`scripts/backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/opt/kairix/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup Neo4j
docker exec kairix-neo4j neo4j-admin dump \
    --database=neo4j \
    --to=/backups/neo4j.dump

# Backup application data
tar -czf $BACKUP_DIR/app-data.tar.gz /opt/kairix/data

# Upload to cloud storage (optional)
aws s3 cp $BACKUP_DIR s3://backup-bucket/kairix/ --recursive

# Clean old backups
find /opt/kairix/backups -mtime +30 -delete
```

### Restore Procedure

```bash
# Stop services
docker-compose down

# Restore Neo4j
docker run -v /path/to/backup:/backup neo4j:5.15 \
    neo4j-admin load --database=neo4j --from=/backup/neo4j.dump

# Restore application data
tar -xzf /path/to/backup/app-data.tar.gz -C /

# Restart services
docker-compose up -d
```

## Monitoring Setup

### Prometheus Configuration

`prometheus.yml`:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'kairix-backend'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'

  - job_name: 'neo4j'
    static_configs:
      - targets: ['localhost:2004']
```

### Grafana Dashboard

Import dashboard ID: 14896 for Kairix monitoring

## Troubleshooting Deployment

### Common Issues

**Neo4j Won't Start**
```bash
# Check logs
docker logs kairix-neo4j

# Verify memory settings
echo "dbms.memory.heap.max_size=2G" >> neo4j.conf
```

**Port Conflicts**
```bash
# Find process using port
sudo lsof -i :8080

# Change port in .env
KAIRIX_PORT=8081
```

**Permission Issues**
```bash
# Fix ownership
sudo chown -R $(whoami):$(whoami) /opt/kairix

# Fix permissions
chmod -R 755 /opt/kairix
```

## Production Checklist

- [ ] SSL certificates configured
- [ ] Firewall rules set
- [ ] Backup automation enabled
- [ ] Monitoring configured
- [ ] Log rotation setup
- [ ] Security headers enabled
- [ ] Rate limiting configured
- [ ] Health checks passing
- [ ] Documentation updated
- [ ] Runbook created