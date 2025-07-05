# Kairix Multi-Tenant Deployment Guide

This guide explains how to deploy multiple isolated Kairix instances for different users.

## Quick Start

### 1. Start Base Services

First, create the Docker network and start Traefik:

```bash
docker network create kairix-network
docker compose -f docker-compose.base.yml up -d
```

### 2. Deploy a User Instance

Deploy an instance for a user (requires OpenAI API key):

```bash
./deploy-user.sh alice sk-your-openai-api-key
```

This will:
- Generate secure API key and Neo4j password
- Deploy isolated containers for the user
- Configure subdomain routing (alice.localhost)
- Save deployment info

### 3. Access the Instance

- **User URL**: http://alice.localhost
- **API Endpoint**: http://alice.localhost/api
- **Traefik Dashboard**: http://localhost:8080
- **Portainer**: http://admin.localhost

## Management Commands

```bash
# List all instances
./manage-users.sh list

# View instance status
./manage-users.sh status alice

# View logs
./manage-users.sh logs alice

# Stop instance
./manage-users.sh stop alice

# Start instance
./manage-users.sh start alice

# Remove instance (with data)
./manage-users.sh remove alice

# View deployment info
./manage-users.sh info alice
```

## Architecture

Each user gets:
- Dedicated React client (port isolation)
- Dedicated Python API server
- Dedicated Neo4j database
- Isolated data volumes
- Resource limits (CPU/Memory)

## API Authentication

All API endpoints require the generated API key in the header:

```bash
curl -H "X-API-Key: <generated-api-key>" http://alice.localhost/api/v1/models
```

## Production Setup

For production deployment:

1. Update `traefik.yml` to enable Let's Encrypt
2. Use real domain names instead of .localhost
3. Adjust resource limits in `docker-compose.user.yml`
4. Configure backup strategy for Neo4j volumes
5. Set up monitoring with Prometheus/Grafana

## Troubleshooting

### Check Container Health
```bash
docker compose -p kairix-alice ps
```

### View API Logs
```bash
docker logs kairix-api-alice
```

### Recreate Instance
```bash
./manage-users.sh remove alice
./deploy-user.sh alice
```

### Network Issues
Ensure the kairix-network exists:
```bash
docker network ls | grep kairix
```

## Resource Limits

Default limits per user:
- Client: 0.5 CPU, 512MB RAM
- API: 1 CPU, 2GB RAM  
- Neo4j: 0.5 CPU, 1GB RAM

Adjust in `docker-compose.user.yml` as needed.