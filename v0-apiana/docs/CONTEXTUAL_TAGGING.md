# Contextual Tagging System

## Overview
The contextual tagging system extracts rich metadata from experiential summaries to enable advanced search and analysis based on emotional state, environment, activities, and social context.

## Context Types

### 1. Emotional Context
Captures the user's emotional state during the conversation.

```json
{
  "primary": "curious",           // Dominant emotion
  "secondary": ["frustrated", "excited"],  // Other present emotions
  "intensity": 0.8,              // 0-1 scale
  "valence": 0.3,               // -1 (negative) to 1 (positive)
  "arousal": 0.6,               // 0 (calm) to 1 (activated)
  "transitions": [              // Emotional journey
    {"from": "confused", "to": "understanding", "trigger": "explanation"}
  ]
}
```

### 2. Environmental Context
Infers or extracts environmental conditions.

```json
{
  "location": "home_office",     // Inferred location
  "location_confidence": 0.8,
  "time_of_day": "late_evening", // morning, afternoon, evening, night
  "day_type": "weekday",         // weekday, weekend, holiday
  "weather": "rainy",            // If mentioned or inferred
  "season": "winter",            // If detectable
  "ambient": "quiet",            // noisy, quiet, busy
  "inferred": true               // Whether this was inferred vs explicit
}
```

### 3. Activity Context
What the user was doing during the conversation.

```json
{
  "primary_activity": "debugging",     // Main activity
  "domain": "software_development",    // Broader category
  "tools_mentioned": ["python", "docker", "postgres"],
  "project_phase": "implementation",   // planning, implementation, testing
  "complexity_level": "high",          // low, medium, high
  "learning_vs_doing": "doing",        // learning, doing, teaching
  "time_pressure": "moderate"          // none, low, moderate, high
}
```

### 4. Social Context
The nature of the interaction with the AI.

```json
{
  "interaction_type": "problem_solving",  // learning, problem_solving, exploration, venting
  "formality": "casual",                  // formal, casual, technical
  "user_role": "developer",               // developer, student, researcher, etc.
  "assistance_style": "collaborative",    // directive, collaborative, exploratory
  "knowledge_level": "intermediate",      // beginner, intermediate, expert
  "conversation_dynamics": "iterative"    // single_query, iterative, brainstorming
}
```

## Implementation Strategy

### Phase 1: Basic Extraction (Current)
- Run as part of summary generation pipeline
- Simple presence/absence detection
- Basic emotion keywords

### Phase 2: Dedicated Agent (Future)
```python
class ContextualTaggingAgent:
    """
    Specialized agent for extracting contextual tags.
    Uses fine-tuned prompts and possibly specialized models.
    """
    
    def extract_all_contexts(self, summary: str) -> Dict[str, Any]:
        # Emotional analysis
        emotional = self.extract_emotional_context(summary)
        
        # Environmental inference
        environmental = self.infer_environmental_context(summary)
        
        # Activity detection
        activity = self.extract_activity_context(summary)
        
        # Social analysis
        social = self.analyze_social_context(summary)
        
        return {
            'emotional_context': emotional,
            'environmental_context': environmental,
            'activity_context': activity,
            'social_context': social
        }
```

### Phase 3: Periodic Enrichment
- Run as scheduled job over existing summaries
- Update and refine tags with improved models
- Cross-reference multiple conversations for patterns

## Use Cases

### 1. Contextual Search
```cypher
// Find conversations when user was frustrated while debugging
MATCH (es:ExperientialSummary)
WHERE es.emotional_context.primary = 'frustrated'
  AND es.activity_context.primary_activity = 'debugging'
RETURN es
```

### 2. Mood Patterns
```cypher
// Analyze emotional patterns by time of day
MATCH (es:ExperientialSummary)
WHERE es.environmental_context.time_of_day IS NOT NULL
RETURN es.environmental_context.time_of_day as time,
       es.emotional_context.primary as emotion,
       count(*) as frequency
```

### 3. Learning Journey
```cypher
// Track progression in a specific domain
MATCH (es:ExperientialSummary)
WHERE es.activity_context.domain = 'machine_learning'
RETURN es.created_at, 
       es.social_context.knowledge_level,
       es.emotional_context.primary
ORDER BY es.created_at
```

## Future Enhancements

1. **Temporal Patterns**: Detect recurring contexts (e.g., "always frustrated on Mondays")
2. **Context Correlation**: Find relationships between contexts (e.g., weather affects mood)
3. **Personalized Insights**: "You're most productive in morning problem-solving sessions"
4. **Proactive Suggestions**: Based on current context, suggest optimal assistance style