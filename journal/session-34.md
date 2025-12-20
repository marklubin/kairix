## Session 34 - Date: 2025-12-19

### Goals
- [x] Consolidate Docker Compose files into single file
- [x] Containerize KP3 query service
- [x] Create admin CLI for service management
- [x] Fix deployment workflow

### What We Covered
- Docker Compose consolidation with profile-based service selection
- Admin CLI (`kx`) for unified service management
- Deployment script improvements with health checks
- PostgreSQL volume management across project renames
- FastMCP SSE transport configuration for HTTP MCP clients

### Key Concepts Learned
1. **Docker Compose Profiles**: Services without profiles always start; services with `profiles: ["app"]` only start when `COMPOSE_PROFILES=app` is set. Use env var in `.env` for default behavior.

2. **Podman Volume Naming**: Podman-compose prefixes volume names with project name (directory). When renaming projects, volumes get new names - must use `external: true` with explicit `name:` to reference existing volumes.

3. **FastMCP Transports**:
   - `mcp.http_app()` defaults to streamable HTTP transport
   - Use `mcp.http_app(transport="sse")` for SSE transport
   - SSE endpoint exposes at `/sse` under mount path
   - Client connects to SSE, gets session ID, POSTs to `/messages/?session_id=...`

### What We Built

**`v2-runtime/kx`** - Admin CLI wrapper:
- Service management: `up`, `down`, `restart`, `status`, `logs`, `build`
- Development: `dev`, `dev:down`
- Database: `migrate`, `psql`, `db:reset`
- Health checks: `wait [postgres|redis|letta|kairix|kp3|all]` with 30s timeout
- KP3 CLI: `kp3 <command>`
- Deployment: `deploy <target>`

**`v2-runtime/docker-compose.yml`** - Consolidated:
- Infrastructure (always starts): postgres, redis, letta, redis-insight, dozzle, metamcp, pmb proxies
- App services (profile: app): kairix-server, kairix-worker, kp3-service
- One-shot runners (profile: migrate, cli): migrate, kp3

**`v2-runtime/deploy.sh`** - Simplified:
- Uses `kx` commands: `down`, `build`, `dev`, `wait postgres`, `migrate`, `up`
- Proper ordering: stop -> build -> start infra -> wait -> migrate -> start apps

**`kp3/src/kp3/query_service/main.py`** - Updated:
- SSE transport for MCP HTTP endpoint at `/mcp/sse`

### Insights & Aha Moments
- Podman-compose project name (from directory) affects volume naming - caused data "loss" when moving from `agent-server` to `v2-runtime` directory
- The `./kx down` in deploy was necessary to avoid container name conflicts with podman-compose
- FastMCP's default HTTP transport isn't SSE - need explicit `transport="sse"` for SSE clients

### Challenges & Solutions

**Challenge**: Container name conflicts during deployment
**Solution**: Added `./kx down` before rebuilding to ensure clean state

**Challenge**: Migrations failing - postgres not running
**Solution**: Start infra first (`./kx dev`), wait for postgres (`./kx wait postgres`), then migrate

**Challenge**: KP3 database missing after consolidation
**Solution**: Volume had different name due to project rename. Fixed with `external: true` and `name: agent-server_kairix-pgdata`

**Challenge**: MCP endpoint returning 404 at `/mcp/sse`
**Solution**: Need `mcp.http_app(transport="sse")` - default transport is streamable HTTP, not SSE

### Files Changed
| File | Action |
|------|--------|
| `v2-runtime/docker-compose.yml` | Consolidated all services, fixed kp3 database URL, external volume |
| `v2-runtime/docker-compose.dev.yml` | Deleted |
| `v2-runtime/docker-compose.prod.yml` | Deleted |
| `v2-runtime/kx` | Created - admin CLI |
| `v2-runtime/deploy.sh` | Simplified to use kx commands |
| `kp3/Dockerfile` | Updated entrypoint for service mode |
| `kp3/src/kp3/query_service/main.py` | SSE transport for MCP |

### Next Steps
- [ ] Test MCP connection from kairix-server to kp3-service via SSE
- [ ] Consider adding `kx logs -f` (follow) as default behavior
- [ ] Add kp3 migrations to deploy flow if needed

### Service URLs (from salinas)
- REST API: `http://salinas:8080/passages/search?query=...`
- MCP SSE: `http://salinas:8080/mcp/sse`
- Internal (kairix-net): `http://kp3-service:8080/mcp/sse`
