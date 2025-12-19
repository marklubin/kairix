## Session 27 - [Date: 2025-12-12]

### Goals
- [x] Consolidate all kairix projects into monorepo
- [x] Set up GitHub Pages for project documentation
- [x] Update deploy.sh for monorepo structure
- [x] Move block configuration from code to database
- [x] Fix subagent block reuse logic

### What We Covered
- Monorepo structure design and implementation
- GitHub Pages configuration (CNAME, static.yml workflow)
- Podman-compose project naming with symlinks
- Database-driven block configuration
- Block sharing bugs in agent provisioning

### Key Concepts Learned

1. **Monorepo Structure**: Consolidated v0-apiana, v2-runtime, kairix-app, and kp3 into single repository with shared docs/, ops/, and journal/ directories at root.

2. **GitHub Pages with Static Files**: Need `.nojekyll` file to serve files directly without Jekyll processing. CNAME file for custom domain mapping.

3. **Podman-Compose Project Naming**: When using symlinks (e.g., `~/agent-server` → `~/kairix/v2-runtime`), podman-compose uses the symlink basename for project name, not the resolved path. Use `-p PROJECT_NAME` for explicit control.

4. **Block Config in Database**: Moved block definitions (labels, descriptions, initial values) from hardcoded Python constants to `block_definitions` table. Provisioning now queries DB for block specs.

### What We Built

**Monorepo Consolidation (120cede):**
- Root `README.md` with project overview
- `docs/` - Architecture docs, testing strategy
- `ops/` - Deployment scripts, Caddyfiles, runbooks
- `v0-apiana/` - Legacy conversation processing
- `v2-runtime/` - Current agent server
- `kairix-app/` - KMP mobile app
- `journal/` - Session logs

**GitHub Pages:**
- `.github/workflows/static.yml` - Deploy workflow
- `index.html` redirect at root
- CNAME for custom domain

**Deploy.sh Updates (3e71ac1, 01e891b):**
- Support for monorepo structure with `KAIRIX_REPO_PATH` and `RUNTIME_SUBDIR`
- Symlink management for deployment path
- Fixed project name detection for podman-compose

**Block Configuration (730a8ff):**
- `block_definitions` table with label, description, initial_value, is_shared
- Migration to seed default blocks (persona, human, background_insights)
- `provisioning/blocks.py` - `get_block_definitions()` loader
- Updated provisioning CLI to use DB blocks

**Block Reuse Fix (78bf286):**
- Fixed logic where subsidiary agents weren't properly reusing conversational agent's blocks
- Block lookup now uses both label AND agent association

### Files Modified

| File | Change |
|------|--------|
| `deploy.sh` | Monorepo path handling, symlink support |
| `alembic/versions/*_block_definitions.py` | NEW - Block definitions table |
| `provisioning/blocks.py` | NEW - DB block loader |
| `provisioning/agents.py` | Use DB blocks instead of constants |
| `.github/workflows/static.yml` | NEW - GitHub Pages deploy |

### Insights & Aha Moments

- **Symlinks complicate tooling**: Both Docker/Podman and git handle symlinks differently. Best to use explicit paths where possible.

- **Migration with seed data**: Alembic migrations can include `INSERT` statements for initial data, keeping schema and default data in sync.

### Next Steps
- [x] Test deployment with new monorepo structure
- [x] Verify block provisioning on production
- [ ] Add more comprehensive docs to GitHub Pages

### Questions/Blockers
- None
