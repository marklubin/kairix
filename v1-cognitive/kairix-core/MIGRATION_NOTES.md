# Migration Notes: Neo4j to SQLite

## Environment Variable Changes

When migrating from Neo4j to SQLite, you can remove the following environment variables:

### Remove:
- `NEO4J_URL` - No longer needed as SQLite is embedded
- Any Neo4j authentication variables

### Keep:
All other environment variables remain the same:
- `KAIRIX_AGENT_CONFIGURATION_SET_KEY`
- `KAIRIX_N_SUMMARIES_PER_MESSAGE` 
- `KAIRIX_USER_NAME`
- `KAIRIX_PERSONA_NAME`
- `KAIRIX_EMBEDDER_MODEL`
- `KAIRIX_EMBEDDER_DEVICE`

## Docker Compose Changes

The Neo4j service in docker-compose.yml is no longer needed. It's already configured with a profile `with-neo4j` so it won't start by default.

## Database Location

SQLite database will be created automatically at:
- Default: `./kairix.db` in the working directory
- Can be customized via `KAIRIX_SQLITE_DB_PATH` environment variable

## Migration Steps

1. Ensure you have run the migration script if you have existing Neo4j data:
   ```bash
   python -m kairix_core.database.neo4j_to_sqlite
   ```

2. Update your environment variables (remove NEO4J_URL)

3. Restart your services

The system will automatically initialize the SQLite database on first run.