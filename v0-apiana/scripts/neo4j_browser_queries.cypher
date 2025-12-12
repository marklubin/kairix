// Neo4j Browser Queries for Apiana AI Memory Data
// Copy and paste these into your Neo4j Browser at http://localhost:7474

// 1. Show all memory blocks with their connections
MATCH (b:Block)-[:GROUNDED_BY]->(g:Grounding)
OPTIONAL MATCH (b)-[:TAGGED_WITH]->(t:Tag)
RETURN b, g, t
LIMIT 25;

// 2. Recent conversations summary
MATCH (b:Block)-[:GROUNDED_BY]->(g:Grounding)
WHERE b.block_type = 'experience' AND b.experience_type = 'conversation'
RETURN g.external_label as conversation_title, 
       substring(b.content, 0, 100) + '...' as summary_preview,
       b.created_at as created
ORDER BY b.created_at DESC
LIMIT 10;

// 3. Count all data
MATCH (b:Block) 
WITH count(b) as blocks
MATCH (g:Grounding) 
WITH blocks, count(g) as groundings
MATCH (t:Tag) 
RETURN blocks, groundings, count(t) as tags;

// 4. Show database structure
CALL db.schema.visualization();

// 5. Search for specific conversation
MATCH (b:Block)-[:GROUNDED_BY]->(g:Grounding)
WHERE g.external_label CONTAINS 'your_search_term'
RETURN b, g;

// 6. Show all node types and counts
CALL db.labels() YIELD label
CALL {
  WITH label
  MATCH (n)
  WHERE label IN labels(n)
  RETURN count(n) as count
}
RETURN label, count
ORDER BY count DESC;

// 7. Show embeddings info (first few dimensions)
MATCH (b:Block)
WHERE b.embedding_v1 IS NOT NULL
RETURN b.block_id, 
       size(b.embedding_v1) as embedding_dimension,
       b.embedding_v1[0..5] as first_5_dimensions
LIMIT 5;