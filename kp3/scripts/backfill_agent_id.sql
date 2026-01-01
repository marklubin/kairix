-- Backfill agent_id for existing passages
-- Run this on salinas after deploying the migration

-- First, check if there's agent_id in metadata we can backfill from
SELECT COUNT(*) as passages_with_agent_in_metadata
FROM passages
WHERE metadata->>'agent_id' IS NOT NULL;

-- Option 1: Backfill from metadata (if agent_id was stored there)
UPDATE passages
SET agent_id = metadata->>'agent_id'
WHERE agent_id IS NULL
  AND metadata->>'agent_id' IS NOT NULL;

-- Option 2: Set all existing passages to a specific agent (single-agent setup)
-- Replace 'agent-xxxxxxxx' with the actual corindel agent ID from:
--   ./kx psql -c "SELECT id FROM letta.agents WHERE name = 'Corindel';"
-- or from v2-runtime's letta API

-- UPDATE passages
-- SET agent_id = 'agent-xxxxxxxx'
-- WHERE agent_id IS NULL;

-- Verify the update
SELECT agent_id, COUNT(*) as count
FROM passages
GROUP BY agent_id;
