# Knowledge Graph & Entity Extraction Plan

## Overview
This document outlines the future implementation of knowledge graph construction and entity extraction that will run as a separate process over the stored conversation summaries in Neo4j.

## Architecture Vision

### Data Model in Neo4j

```cypher
// Current (Phase 1) - Just summaries
(:Memory {
  id, content, embedding,
  conversation_id, title,
  created_at, version: "1.0",
  memory_type: "experiential_summary"
})

// Future (Phase 2) - Knowledge extraction layer
(:Memory)-[:MENTIONS {position, context}]->(:Entity {
  name, type, canonical_form, aliases[]
})

(:Memory)-[:ASSERTS {confidence}]->(:Relationship {
  type, subject, object, confidence,
  first_observed, last_confirmed
})

(:Entity)-[:RELATES_TO {relationship_id}]->(:Entity)

// Ground truth layer
(:Fact {
  statement, confidence, evidence_count
})-[:EVIDENCED_BY]->(:Memory)
  -[:CONTRADICTED_BY]->(:Memory)
```

### Processing Pipeline (To Be Implemented)

1. **Entity Extraction Agent**
   - Scan Memory nodes periodically
   - Extract entities (people, concepts, tools, locations)
   - Create/merge Entity nodes
   - Track mentions with context

2. **Relationship Mapping Agent**
   - Analyze memories for relationships between entities
   - Create Relationship nodes with confidence scores
   - Build RELATES_TO edges between entities

3. **Fact Validation System**
   - Compare new assertions against existing facts
   - Promote high-confidence, repeated relationships to Facts
   - Detect and flag contradictions
   - Build ground truth repository

### Scheduled Processing Flow

```python
@flow(name="extract_knowledge_graph", schedule="0 2 * * *")  # Run at 2 AM daily
def extract_knowledge_from_memories():
    """
    Periodic job to extract entities and relationships from memories.
    
    1. Query recent unprocessed memories
    2. Run entity extraction
    3. Run relationship extraction
    4. Validate against ground truth
    5. Update fact repository
    """
    pass
```

### Key Features to Implement

1. **Versioning & Evolution**
   - Track how entity understanding evolves
   - Version insights when new information emerges
   - Maintain lineage for backtracking

2. **Backtracking Support**
   ```cypher
   // Get full context for any fact/insight
   MATCH (fact:Fact)-[:DERIVED_FROM*]->(:Memory)
   RETURN path
   ```

3. **Contradiction Detection**
   - Flag when new memories contradict established facts
   - Surface conflicting information for review

4. **Insight Evolution**
   - Allow insights to be refined with new context
   - Create new versions rather than overwriting
   - Track triggers (new info, user query, scheduled review)

### Agent Architecture

```python
class EntityExtractorAgent:
    """Uses LLM to extract entities from memory content."""
    def extract(self, content: str) -> List[Entity]
        # Prompt engineering for entity extraction
        # NER fallback for common entities
        # Confidence scoring
        pass

class RelationshipMapperAgent:
    """Uses LLM to identify relationships between entities."""
    def extract(self, content: str, entities: List[Entity]) -> List[Relationship]
        # Relationship extraction prompts
        # Confidence assessment
        # Contradiction checking
        pass
```

### Benefits of Separate Processing

1. **No blocking** - Summary generation stays fast
2. **Iterative refinement** - Can re-run extraction with better prompts
3. **A/B testing** - Try different extraction strategies
4. **Resource management** - Run during off-peak hours
5. **Incremental updates** - Only process new memories

### Integration Points

- Neo4j GraphRAG for vector operations
- Ollama for LLM-based extraction
- Prefect for scheduling and orchestration
- Optional: Dedicated NER models for entity extraction

### Future Queries This Enables

```cypher
// Find all memories about a specific topic cluster
MATCH (m:Memory)-[:DISCUSSES]->(topic:Topic)<-[:DISCUSSES]-(related:Memory)
WHERE topic.name = "Python"
RETURN m, related

// Track knowledge evolution
MATCH (e:Entity {name: "Prefect"})<-[:MENTIONS]-(m:Memory)
RETURN m.created_at, m.content
ORDER BY m.created_at

// Find contradictions
MATCH (f1:Fact)<-[:SUPPORTS]-(m1:Memory),
      (f2:Fact)<-[:SUPPORTS]-(m2:Memory)
WHERE f1.contradicts(f2)
RETURN f1, f2, m1, m2
```

## Next Steps

1. Implement basic entity extraction agent
2. Create relationship mapping logic
3. Design fact validation system
4. Build scheduled Prefect flows
5. Create monitoring dashboard for knowledge graph growth

## Notes

- Start simple with rule-based extraction, enhance with LLM
- Consider using spaCy or similar for initial entity recognition
- Build confidence scoring into every extraction
- Plan for manual review/correction interface
- Consider knowledge graph visualization tools (Neo4j Bloom, custom D3.js)