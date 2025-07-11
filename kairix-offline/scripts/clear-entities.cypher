// Clear entities by type or ID
// Usage: Replace ENTITY_TYPE_OR_ID with either:
//   - A node label (e.g., SourceDocument)
//   - A node ID (e.g., '123e4567-e89b-12d3-a456-426614174000')

// Option 1: Delete all nodes of a specific type
MATCH (n:ENTITY_TYPE_OR_ID)
DETACH DELETE n;

// Option 2: Delete a specific node by ID
// MATCH (n) WHERE id(n) = 'ENTITY_TYPE_OR_ID'
// DETACH DELETE n;