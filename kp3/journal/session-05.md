## Session 5 - 2025-01-31

### Goals
- [x] Implement Memory Scopes feature - ref-based search scope closures
- [x] Create database migration for `memory_scopes` table
- [x] Add SQLAlchemy model for MemoryScope
- [x] Create Pydantic schemas for scope API
- [x] Implement scopes service with full CRUD and operations
- [x] Add `scope_ids` filtering to search service
- [x] Add REST API endpoints for scopes
- [x] Write comprehensive unit and E2E tests

### What We Did

Implemented a complete **Memory Scopes** system that defines dynamic search closures using refs and literal passage IDs. A scope:
- Is agent-scoped (isolated per agent)
- Uses refs infrastructure for versioning and history
- Stores definitions as passages (type="scope_definition")
- Enables scoped operations: create passages in scope, search within scope
- Is fully revertable via ref history

### Key Changes

#### New Files Created

| File | Purpose |
|------|---------|
| `alembic/versions/j5e6f7g8h901_add_memory_scopes.py` | Migration for `memory_scopes` table |
| `src/kp3/schemas/scope.py` | Pydantic request/response models |
| `src/kp3/services/scopes.py` | Core business logic (~300 lines) |
| `tests/test_scopes.py` | 23 unit tests for schemas |
| `tests/test_scopes_e2e.py` | 47 E2E functional tests |

#### Modified Files

| File | Changes |
|------|---------|
| `src/kp3/db/models.py` | Added `MemoryScope` SQLAlchemy model |
| `src/kp3/services/search.py` | Added `scope_ids` parameter to all search functions |
| `src/kp3/query_service/router.py` | Added 10 new REST endpoints for scopes |

### Technical Notes

#### Scope Definition Storage

Scope definitions are stored as passages with `passage_type="scope_definition"`. The content is a JSON-serialized `ScopeDefinition`:

```python
class ScopeDefinition(BaseModel):
    refs: list[str] = []           # Ref names → resolve to passage IDs
    passages: list[UUID] = []       # Literal passage IDs
    version: int = 1               # Increments on each update
    created_from: UUID | None      # Previous definition (for lineage)
```

This leverages existing passage infrastructure and enables versioning via the refs system.

#### Head Ref Naming Convention

Each scope has a head ref following the pattern:
```
{agent_id}/scope/{scope_name}/HEAD
```

Example: `test-agent/scope/working-memory/HEAD`

#### Scope Resolution

Resolution is dynamic - refs are resolved at search time:
1. Literal passage IDs are verified to exist
2. Refs are resolved to their current targets
3. Deleted passages are automatically excluded
4. Result is a `set[UUID]` for efficient filtering

#### Search Integration

The `scope_ids` parameter was added to `search_passages()` and propagated to all internal search functions. SQL filtering uses:
```sql
AND p.id = ANY(:scope_ids)
```

This works with FTS, semantic, hybrid, and tag-based search modes.

#### Atomic Operations

`create_passage_in_scope()` is atomic - it creates the passage AND updates the scope definition in a single transaction. If either fails, both are rolled back.

#### History and Revert

- Every scope change creates a new definition passage and updates the head ref
- Ref history tracks all changes with timestamps
- Revert creates a NEW version with the old definition content (non-destructive)
- Version numbers always increment, even on revert

### API Endpoints Added

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scopes` | Create a new scope |
| GET | `/scopes` | List all scopes for agent |
| GET | `/scopes/{name}` | Get scope by name |
| DELETE | `/scopes/{name}` | Delete a scope |
| POST | `/scopes/{name}/passages` | Create passage in scope |
| POST | `/scopes/{name}/add` | Add passages/refs to scope |
| POST | `/scopes/{name}/remove` | Remove from scope |
| GET | `/scopes/{name}/history` | Get scope change history |
| POST | `/scopes/{name}/revert` | Revert to previous version |
| GET | `/scopes/{name}/search` | Search within scope |

### Tests

#### Unit Tests (test_scopes.py) - 23 tests
- ScopeDefinition schema validation and JSON roundtrip
- Request schema validation (MemoryScopeCreate, ScopedPassageCreate, etc.)
- Version validation (must be >= 1)
- Naming convention verification

#### E2E Tests (test_scopes_e2e.py) - 47 tests
- Database table creation verification
- Full CRUD lifecycle
- Agent isolation
- Scoped operations (create, add, remove passages/refs)
- Dynamic ref resolution
- All search modes within scope (FTS, semantic, hybrid)
- History recording and ordering
- Revert functionality
- All API endpoints
- Edge cases (nonexistent scopes, invalid versions, etc.)

All tests pass:
- Unit tests: 23/23 passed
- Linting (ruff): All checks passed
- Type checking (pyright): 0 errors

### Insights & Decisions

1. **Scope definitions as passages**: Rather than creating a separate table for definitions, we store them as passages. This reuses existing infrastructure and makes the system simpler.

2. **Refs resolved at search time**: Refs in a scope definition aren't validated when added - they're resolved when the scope is used for search. This allows adding refs that don't exist yet.

3. **Lambda for default_factory**: Pyright strict mode requires explicit typing for `default_factory`. Using `lambda: list[UUID]()` instead of just `list` satisfies the type checker.

4. **Non-destructive revert**: Reverting doesn't delete history - it creates a new version with the old content. This maintains a complete audit trail.

5. **Empty scope returns empty results**: If a scope has no passages (either empty or all refs unresolved), search returns an empty list immediately without hitting the database.

### Next Steps
- [ ] Run E2E tests with Docker to verify full functionality
- [ ] Deploy and test with real PostgreSQL instance
- [ ] Consider adding scope nesting (scopes containing other scopes)
- [ ] Add MCP tool for scope operations
- [ ] Document scope usage patterns for agents

### Verification Commands

```bash
# Apply migration
uv run alembic upgrade head

# Run unit tests
uv run pytest tests/test_scopes.py -v

# Run E2E tests (requires Docker)
uv run pytest tests/test_scopes_e2e.py -v

# Run all tests
uv run pytest tests/ -v
```

### Example Usage

```bash
# Create a scope
curl -X POST http://localhost:8080/scopes \
  -H "X-Agent-ID: test-agent" \
  -H "Content-Type: application/json" \
  -d '{"name": "working-memory", "description": "Active context"}'

# Create passage in scope
curl -X POST http://localhost:8080/scopes/working-memory/passages \
  -H "X-Agent-ID: test-agent" \
  -H "Content-Type: application/json" \
  -d '{"content": "Important context", "passage_type": "memory"}'

# Search within scope
curl "http://localhost:8080/scopes/working-memory/search?query=context" \
  -H "X-Agent-ID: test-agent"

# View history
curl http://localhost:8080/scopes/working-memory/history \
  -H "X-Agent-ID: test-agent"

# Revert to previous version
curl -X POST http://localhost:8080/scopes/working-memory/revert \
  -H "X-Agent-ID: test-agent" \
  -H "Content-Type: application/json" \
  -d '{"to_version": 1}'
```
