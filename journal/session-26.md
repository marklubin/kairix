## Session 26 - [Date: 2025-12-09]

### Goals
- [x] Add database-driven system prompts for agent provisioning
- [x] Fix block divergence bug in provisioning

### What We Covered
- SQLAlchemy 2.0 async models with asyncpg
- Alembic migrations with seed data
- Letta SDK `client.agents.update()` for system prompt updates
- Block sharing architecture between agents
- Debugging production vs local block ID mismatches

### Key Concepts Learned

1. **Database-Driven Prompts**: System prompts moved from hardcoded constants in `agents.py` to PostgreSQL `agent_definitions` table. Provisioning now loads prompts via `get_system_prompt(agent_type)` and always updates existing agents to match the DB definition.

2. **Block Sharing Bug Pattern**: When agents are created manually or provisioned out of order, they can end up with different block IDs for "shared" blocks. The original code only checked if a block with the right *label* existed, not if it had the correct *ID*.

3. **Fix Strategy - ID Comparison**: Changed `find_agent_by_name()` to return `dict[label, block_id]` instead of `set[label]`. Now `_remediate_existing_agent()` compares block IDs for shared blocks and detaches/reattaches if they don't match.

4. **Future-Proof Design**: The fix works automatically for any new blocks added to `SharedBlocks.ALL` - no code changes needed. The provisioning logic iterates over the spec's shared blocks and ensures IDs match the conversational agent.

### What We Built

**Database-Driven Prompts:**
- `src/kairix_agent/provisioning/models.py` - `AgentDefinition` SQLAlchemy model
- `alembic/versions/c3d4e5f6a7b8_create_agent_definitions_table.py` - Migration with seed data
- `src/kairix_agent/provisioning/prompts.py` - `get_system_prompt()` async loader
- `src/kairix_agent/provisioning/agents.py` - Renamed dataclass to `AgentSpec`, factory functions now take `system_prompt` param
- `src/kairix_agent/provisioning/cli.py` - Loads prompts from DB, always updates system prompt on remediation

**Block Divergence Fix:**
- `find_agent_by_name()` - Returns `dict[str, str]` (label -> block_id)
- `_remediate_existing_agent()` - Compares shared block IDs, detaches wrong blocks, attaches correct ones
- `_attach_block_to_conversational_agent()` - Same fix for insights block attachment

### Insights & Aha Moments

- **Root cause**: Corindel was created manually before the insights agent existed, so it had its own `background_insights` block. When insights agent was later provisioned, it created a new block and tried to attach it, but got a ConflictError which was silently ignored.

- **The fix is symmetric**: Works for both directions - fixing subsidiary agents that have wrong blocks AND fixing the conversational agent when insights agent's block needs to be attached.

- **Production debugging workflow**: Query both local and production Letta instances with the same Python script to compare block IDs across agents.

### Challenges & Solutions

- **Challenge**: `background_insights` block had different IDs on Corindel vs Corindel-BackgroundInsights in production
- **Solution**: Added ID comparison logic that detaches incorrect blocks before attaching correct ones

- **Challenge**: Same bug could affect `persona`, `human`, or any future shared blocks
- **Solution**: Generalized the fix to `_remediate_existing_agent()` for all shared blocks, not just the insights-specific attachment function

### Files Modified

| File | Change |
|------|--------|
| `provisioning/models.py` | NEW - AgentDefinition SQLAlchemy model |
| `provisioning/prompts.py` | NEW - get_system_prompt() loader |
| `alembic/versions/c3d4e5f6a7b8_*.py` | NEW - Migration with seed data |
| `provisioning/agents.py` | Renamed AgentDefinition -> AgentSpec |
| `provisioning/cli.py` | DB prompt loading, block ID verification |
| `provisioning/__init__.py` | Updated exports |

### Next Steps
- [ ] Push commits to remote
- [ ] Run provisioning on production for all agents to ensure blocks are aligned
- [ ] Consider adding a `--verify-only` flag to provisioning CLI for dry-run checks

### Questions/Blockers
- None - both features implemented and tested against production
