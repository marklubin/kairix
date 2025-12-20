---

## Session 33 - 2025-12-19

### Goals
- [x] Add KP3 passage search API with REST and MCP interfaces
- [x] Refactor CLI to share search logic with new service
- [x] Create e2e tests for the query service

### What We Covered
- Designed and implemented a new query service for KP3 passages
- Integrated FastMCP with FastAPI for dual REST/MCP access
- Extracted search logic into reusable service module
- Set up testcontainers-based e2e testing infrastructure

### Key Concepts Learned
1. **FastMCP + FastAPI Integration**: Mount FastMCP at a subpath using `app.mount("/mcp", mcp.http_app())` to serve both REST and MCP from same service
2. **Hybrid Search with RRF**: Reciprocal Rank Fusion combines FTS and semantic search rankings: `1/(60+rank_fts) + 1/(60+rank_semantic)`
3. **Type Aliases for API Contracts**: Define types like `SearchMode = Literal["fts", "semantic", "hybrid"]` at service layer as single source of truth

### What We Built

**New Files:**
- `src/kp3/services/search.py` - Search service with FTS, semantic, hybrid modes
- `src/kp3/query_service/main.py` - FastAPI app with MCP mount
- `src/kp3/query_service/router.py` - REST endpoint `/passages/search`
- `src/kp3/query_service/mcp.py` - MCP tool `search_kp3_passages`
- `src/kp3/query_service/models.py` - Pydantic request/response models
- `tests/conftest.py` - Test fixtures with testcontainers
- `tests/test_query_service.py` - E2E tests (skip when Docker unavailable)
- `example.env` - Configuration template

**Modified Files:**
- `pyproject.toml` - Added fastapi, uvicorn, fastmcp, testcontainers deps + `kp3-service` script
- `src/kp3/cli.py` - Refactored to use new search service

### Insights & Aha Moments
- Keeping the query service separate from v2-runtime is cleaner architecture - each service has its own concerns
- FastMCP's `http_app()` returns an ASGI app that mounts cleanly into FastAPI
- Using `pytest.mark.docker` with autouse fixture provides clean skip behavior when containers unavailable

### Challenges & Solutions
- **Challenge**: Tests failing because Docker/Podman not running
- **Solution**: Added `skip_docker_tests` autouse fixture that skips tests marked with `@pytest.mark.docker`

- **Challenge**: Duplicate type definitions for search mode across files
- **Solution**: Defined `SearchMode` type alias in search service, imported elsewhere

### Next Steps
- [ ] Run tests with Docker to verify e2e functionality
- [ ] Add more projections to search results as needed
- [ ] Consider adding caching for frequently searched queries

### Questions/Blockers
- None - PR merged successfully
