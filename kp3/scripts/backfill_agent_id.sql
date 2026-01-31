-- Backfill agent_id for existing passages
-- Run this after deploying the g2b3c4d5e678_add_agent_id_to_passages migration

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
-- Replace 'agent-xxxxxxxx' with your actual agent ID

-- UPDATE passages
-- SET agent_id = 'agent-xxxxxxxx'
-- WHERE agent_id IS NULL;

-- Verify the update
SELECT agent_id, COUNT(*) as count
FROM passages
GROUP BY agent_id;
