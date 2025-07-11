# Kairix Functional Tests Outline

## Database Layer Tests

### 1. SQLite Core Functionality
- **Database initialization and schema creation**
- **Connection pooling and thread safety**
- **Transaction management and rollback scenarios**

### 2. Semantic Graph Module Tests
- **Entity Management**
  - Create new entities
  - Update entity properties
  - Delete entities with cascade handling
  - Query entities by type and properties
  
- **Relationship Management**
  - Create relationships between entities
  - Update relationship properties
  - Traverse relationships (1-hop, multi-hop)
  - Handle circular relationships
  
- **Concurrency Tests**
  - Multiple simultaneous entity creations
  - Concurrent relationship updates
  - Graph integrity under parallel access

### 3. Memory Shard System Tests
- **Memory Creation**
  - Generate memory shards from conversations
  - Validate memory metadata (timestamps, context)
  - Test memory deduplication
  
- **Vector Storage**
  - Embedding generation consistency
  - Vector similarity search accuracy
  - Performance with large memory sets (10k+ shards)
  
- **Memory Retrieval**
  - Relevance scoring validation
  - Context-aware memory selection
  - Memory age weighting

### 4. Notebook Functionality Tests
- **Agent Note Operations**
  - Create notes via agent API
  - Update existing notes
  - Delete notes
  - Search notes by content
  
- **Access Control**
  - Verify agent-only access
  - Test isolation between different agents
  - Validate user cannot directly modify

### 5. Conversation History Tests
- **Message Persistence**
  - Store user messages accurately
  - Store agent responses with metadata
  - Handle special characters and long messages
  
- **Sliding Window Retrieval**
  - Retrieve last N messages correctly
  - Maintain message ordering
  - Handle conversations exceeding window size
  
- **History Management**
  - Archive old conversations
  - Query historical conversations
  - Export conversation data

### 6. Vector Search Extension Tests
- **Embedding Operations**
  - Generate embeddings for different content types
  - Validate embedding dimensions
  - Test embedding caching
  
- **Similarity Search**
  - K-nearest neighbor accuracy
  - Distance metric validation
  - Performance benchmarks
  
- **Index Management**
  - Index creation and updates
  - Index optimization
  - Recovery from corrupted indexes

## Integration Test Scenarios

### 1. End-to-End Conversation Flow
- User sends message
- System generates response
- Response stored in history
- Memory shard created if significant
- Semantic graph updated with entities

### 2. System Restart Resilience
- Active conversation → System restart → Resume conversation
- Verify all data persisted correctly
- Check memory continuity

### 3. Multi-User Scenarios
- Multiple users chatting simultaneously
- Verify data isolation
- Test performance under load

### 4. Data Migration Tests
- Test upgrade paths between versions
- Validate data integrity after migration
- Rollback scenarios

## Runtime Components - BDD Stories

### 1. Agent Runtime (Singleton Manager for LLM Access)

**Story: Agent Runtime Initialization**
```
Given the system is starting up
When AgentRuntime.initialize() is called
Then a singleton instance is created
And configuration is loaded from environment
And the runtime is ready to serve agent requests
```

**Story: OpenAI Agent Library Integration**
```
Given the Agent Runtime is initialized
When a request for an OpenAI-compatible agent is made
Then the runtime provides access to the agent
And manages the agent lifecycle
And handles connection pooling
```

**Story: Llama-cpp In-Process Inference (Pre-Beta)**
```
Given the Agent Runtime is configured for local inference
When a request for llama-cpp model is made
Then the runtime loads the model in-process
And provides inference capabilities
And manages memory constraints
```

**Story: Concurrent Agent Access**
```
Given multiple threads need agent access
When they request agents simultaneously
Then the runtime serializes access appropriately
And prevents resource contention
And maintains thread safety
```

### 2. Cache Runtime (Built on diskcache)

**Story: Cache Runtime Initialization**
```
Given the application needs caching capabilities
When CacheRuntime.initialize() is called
Then a singleton cache instance is created
And disk cache is configured with proper paths
And the cache is ready for operations
```

**Story: Low-Overhead Value Caching**
```
Given the cache runtime is initialized
When application code stores a value
Then the value is persisted to disk efficiently
And retrieval has minimal overhead
And expired values are automatically cleaned
```

**Story: Cache Key Management**
```
Given values are stored in cache
When a key collision might occur
Then the cache runtime handles it gracefully
And maintains data integrity
And provides namespace isolation
```

**Story: Cache Performance Under Load**
```
Given high concurrent cache operations
When multiple threads access cache
Then operations complete without blocking
And cache maintains consistency
And performance degrades gracefully
```

### 3. Storage Runtime (SQLite Manager)

**Story: Storage Runtime Initialization**
```
Given the application needs database access
When StorageRuntime.initialize() is called
Then SQLite connections are established
And schema is verified/migrated
And DAOs are ready for use
```

**Story: Connection Pool Management**
```
Given multiple components need database access
When they request connections concurrently
Then the runtime provides connections from pool
And manages connection lifecycle
And prevents connection exhaustion
```

**Story: Transaction Boundary Management**
```
Given a complex operation spanning multiple tables
When the operation is executed
Then the runtime provides transaction support
And ensures atomicity
And handles rollback on failure
```

### 4. Vector Storage Runtime

**Story: Vector Storage Initialization**
```
Given the system needs semantic search
When VectorStorage.initialize() is called
Then SQLite VSS extension is loaded
And vector indexes are prepared
And embedding pipeline is ready
```

**Story: Embedding Generation**
```
Given text content needs vectorization
When embed() is called
Then the runtime generates consistent embeddings
And caches results when appropriate
And handles batch operations efficiently
```

**Story: Similarity Search**
```
Given a query vector
When similarity search is performed
Then the runtime returns relevant results
And applies proper distance metrics
And respects result count limits
```

### 5. Logging Runtime

**Story: Structured Logging Setup**
```
Given the application needs logging
When LoggingRuntime.initialize() is called
Then structured logging is configured
And log levels are set appropriately
And outputs are directed correctly
```

**Story: Cross-Component Logging**
```
Given multiple components emit logs
When they log simultaneously
Then logs maintain proper ordering
And include component context
And are formatted consistently
```

## Cognition Module - Perception Model BDD Stories

### 1. Perception Model Core

**Story: Stimulus-Triggered Perception**
```
Given a stimulus arrives (user message, environmental change)
When the perception system processes it
Then a unit of thinking (Perception) is triggered
And the perception can cascade to other perceptions
And actions or information responses are generated
```

**Story: Perception Cascade Chain**
```
Given an initial perception is processing
When it determines additional analysis is needed
Then it triggers secondary perceptions
And maintains causal relationships
And prevents infinite loops
```

**Story: Internal Narrative Formation**
```
Given multiple perceptions have been processed
When the system forms its response
Then it constructs a coherent internal narrative
And integrates information from all perceptions
And maintains consistency with persona traits
```

### 2. Persona Orchestration

**Story: Persona Initialization**
```
Given a new conversation session starts
When the Persona is instantiated
Then it loads its fundamental traits and characteristics
And initializes its perception processors
And establishes its narrative continuity
```

**Story: Persona Evolution Over Time**
```
Given the Persona has engaged in multiple conversations
When significant experiences accumulate
Then the Persona's understanding evolves
And core traits remain stable
And new insights are integrated coherently
```

**Story: User Understanding Development**
```
Given ongoing interactions with a user
When the Persona processes new information
Then it updates its model of the user
And maintains historical context
And adapts responses to user patterns
```

### 3. Reflection and Memory Formation

**Story: Periodic Reflection Trigger**
```
Given conversation has progressed for N turns
When the reflection threshold is reached
Then the Persona initiates reflection
And extracts significant information
And updates its first-person narrative
```

**Story: First-Person Narrative Construction**
```
Given reflection has identified key experiences
When constructing the narrative entry
Then it writes in first-person perspective
And maintains temporal continuity
And preserves emotional context
```

**Story: Long-Term Memory Integration**
```
Given new reflections are created
When they are stored in memory
Then they link to relevant existing memories
And update the knowledge graph
And remain searchable via embeddings
```

### 4. Knowledge Graph Integration

**Story: Concept Extraction from Conversation**
```
Given a conversation contains entities and relationships
When the perception system processes it
Then concepts are extracted and identified
And new nodes are added to the knowledge graph
And relationships are established or strengthened
```

**Story: Knowledge Graph Influence on Response**
```
Given a user query requires contextual knowledge
When the Persona formulates a response
Then relevant graph nodes are retrieved
And relationships inform the response
And the response reflects connected knowledge
```

**Story: Graph Evolution Through Experience**
```
Given new information contradicts existing knowledge
When the knowledge graph is updated
Then conflicts are resolved coherently
And versioning maintains history
And the Persona can explain changes
```

### 5. Vector Space Search and Semantic Relevance

**Story: Embedding-Based Memory Retrieval**
```
Given a user input with semantic content
When searching for relevant memories
Then input is converted to embeddings
And vector similarity search is performed
And most relevant passages are retrieved
```

**Story: Context-Aware Relevance Scoring**
```
Given multiple potentially relevant memories
When ranking for current context
Then recency is considered
And conversation context weights results
And persona state influences selection
```

**Story: Semantic Influence on Perception**
```
Given retrieved memories from vector search
When they inform current perception
Then they shape the interpretation of stimulus
And guide the response generation
And maintain semantic coherence
```

### 6. Perceptor Component Integration

**Story: Multi-Perceptor Coordination**
```
Given multiple perceptors are active
When processing a single stimulus
Then each contributes its perspective
And results are merged coherently
And conflicts are resolved by the Persona
```

**Story: Perceptor State Management**
```
Given perceptors maintain internal state
When conversation context changes
Then state is updated appropriately
And persistence is handled correctly
And state influences future perceptions
```

**Story: Perceptor Performance Under Load**
```
Given high-frequency stimulus input
When multiple perceptors process concurrently
Then system maintains responsiveness
And perception quality is preserved
And resource usage remains bounded
```

## Individual Perceptor Functional Tests

### 1. SQLiteConversationHistoryPerceptor
**What it does (User-Friendly)**: *"Your AI's conversation journal - remembers every chat you've had together, like a diary that never forgets your inside jokes!"*

**Test Case 1: Basic Conversation Storage**
```
Data Prerequisites:
- Fresh SQLite database with schema initialized
- Agent ID: "test-agent-001"
- User ID: "test-user-001"

Given a new conversation starts
When user says "Hello, how are you?" 
And assistant responds "I'm doing well, thank you!"
And user says "What's the weather like?"
And assistant responds "Let me check that for you..."
Then the perceptor stores exactly 4 messages in order
And retrieving history shows the complete conversation
And messages maintain role labels (user/assistant)
```

**Test Case 2: Sliding Window Management**
```
Data Prerequisites:
- SQLite database with 60 existing messages for agent/user pair
- Window size set to 50

Given conversation history exceeds window size
When 5 new message pairs are added
Then only the most recent 50 messages are retrieved
And older messages remain in database but outside window
And sequence numbers maintain integrity
```

### 2. EnvironmentTrackingPerceptor
**What it does (User-Friendly)**: *"Your AI's environmental awareness - knows when you're jogging in the park or sitting at your desk, making conversations feel more natural!"*

**Test Case 1: Live Sensor Data Processing**
```
Data Prerequisites:
- Mock GPS coordinates: (37.7749, -122.4194) 
- Mock motion data: "walking"
- Mock device state: "phone_in_hand"

Given environmental sensors are providing data
When location updates to Golden Gate Park coordinates
And motion sensor indicates "walking" 
And device state shows "phone_in_hand"
Then perceptor generates context "You're walking in Golden Gate Park"
And includes natural language instructions for contextual responses
```

**Test Case 2: Environmental History Tracking**
```
Data Prerequisites:
- Previous location: "home"
- Previous activity: "stationary"
- Current location: "office"
- Current activity: "stationary"

Given environmental context has changed
When transitioning from home to office
Then perceptor maintains history of previous states
And can reference the transition in responses
And provides temporal context for the change
```

### 3. IncrementalReflectionPerceptor
**What it does (User-Friendly)**: *"Your AI's thoughtful moments - periodically pauses to reflect on your conversations and extract meaningful insights, like a wise friend who really listens!"*

**Test Case 1: Reflection Trigger and Summary Generation**
```
Data Prerequisites:
- 20 conversation messages about planning a trip to Japan
- Configured summarization_interval: 20
- Working LLM agent for summarization
- Initialized vector embedder

Given 20 messages have accumulated about Japan travel
When the summarization threshold is reached
Then perceptor generates a reflection summary
And summary captures key trip details (dates, cities, interests)
And creates embedding for semantic search
And stores as MemoryShard with proper metadata
```

**Test Case 2: Multi-Topic Reflection**
```
Data Prerequisites:
- 10 messages about work stress
- 10 messages about weekend plans
- Total 20 messages triggering reflection

Given conversation covers multiple distinct topics
When reflection is triggered
Then summary identifies both topics
And maintains coherent narrative across topics
And assigns appropriate importance weights
```

### 4. SemanticGraphPerceptor (DEFERRED - Fast Follow)
**Note**: This perceptor is being moved to a fast follow-up release as it currently lacks:
- Configuration mechanism
- Update process for graph data
- Entity extraction pipeline

Will be refined and included in a future release once the update process is implemented.

### 5. SummaryInsightPerceptor
**What it does (User-Friendly)**: *"Your AI's memory search engine - instantly finds relevant memories from past conversations, like having perfect recall of every meaningful moment!"*

**Test Case 1: Keyword-Based Memory Retrieval**
```
Data Prerequisites:
- 5 memory shards about "machine learning projects"
- 3 memory shards about "cooking recipes"
- 2 memory shards about "vacation plans"
- All with embeddings in vector store

Given user asks "What ML projects did we discuss?"
When insight perceptor searches memories
Then extracts keywords ["ML", "projects", "machine learning"]
And retrieves top 3 relevant ML memory shards
And ranks by semantic similarity score
And excludes unrelated memories (cooking, vacation)
```

**Test Case 2: Contextual Insight Extraction**
```
Data Prerequisites:
- Memory shard: "User expressed interest in learning guitar, particularly jazz style"
- Memory shard: "User bought a Fender Stratocaster last month"
- Query about musical interests

Given user asks "What instrument was I interested in?"
When searching for insights
Then finds both guitar-related memories
And extracts specific sentences mentioning guitar
And provides confidence scores for relevance
```

### 6. EnvironmentalContextPerceptor
**What it does (User-Friendly)**: *"Your AI's weather station and clock - always knows the time, date, and weather where you are, making conversations timely and relevant!"*

**Test Case 1: Location-Based Weather Fetch**
```
Data Prerequisites:
- Mock IP geolocation: San Francisco, CA
- Mock weather API response: 65°F, partly cloudy
- Current time: 2024-01-15 14:30 PST

Given perceptor needs environmental context
When checking current conditions
Then determines location via IP (San Francisco)
And fetches current weather (65°F, partly cloudy)
And formats context with local time
And caches result for 5 minutes
```

**Test Case 2: Cache Efficiency Test**
```
Data Prerequisites:
- Recent cached context (age: 2 minutes)
- Cache duration: 300 seconds

Given recent context exists in cache
When multiple requests occur within cache window
Then returns cached data without API calls
And updates cache only after expiration
And handles cache misses gracefully
```

## Reflection Perceptor Configuration Tests

### Reflection vs Regular Perceptor Behavior
**What it does (User-Friendly)**: *"The self-improvement engine - your AI reflects on conversations after responding, learning and growing from each interaction like a thoughtful friend who ponders what was said!"*

**Test Case 1: Reflection Perceptor Async Triggering**
```
Data Prerequisites:
- ConversationalPersona with IncrementalReflectionPerceptor in both regular AND reflection lists
- SQLiteConversationHistoryPerceptor in reflection list only
- Test conversation with 3 message pairs

Given a perceptor is configured as a reflection perceptor
When the assistant completes a response
Then a self_perception stimulus is created with the response content
And reflection perceptors process it asynchronously
And regular perceptors do NOT receive this stimulus
And reflection processing does not block the conversation flow
```

**Test Case 2: Dual-Mode Perceptor Behavior**
```
Data Prerequisites:
- IncrementalReflectionPerceptor configured in BOTH regular and reflection lists
- Conversation with user message and assistant response

Given a perceptor is in both regular and reflection lists
When processing user message
Then it acts as regular perceptor (accumulates message)
When processing self_perception stimulus
Then it acts as reflection perceptor (may trigger summarization)
And maintains separate behavior based on stimulus type
```

**Test Case 3: Reflection-Only Perceptor Isolation**
```
Data Prerequisites:
- ConversationHistoryPerceptor ONLY in reflection_perceptors list
- Active conversation flow

Given a perceptor is only in reflection_perceptors list
When user sends a message
Then the perceptor does NOT process the user stimulus
When assistant completes response
Then the perceptor DOES process the self_perception stimulus
And updates conversation history after response completion
```

**Test Case 4: Learning Feedback Loop Verification**
```
Data Prerequisites:
- IncrementalReflectionPerceptor with summarization_interval=5
- 10 conversation messages
- SummaryInsightPerceptor in regular perceptors list

Given reflection has created 2 memory shards from past summaries
When user asks about a topic covered in memories
Then SummaryInsightPerceptor retrieves relevant memories
And these influence the assistant's response
And new response eventually creates new reflection
And demonstrates the complete learning loop
```

## Stateful Application E2E Tests (Mixed Open/Closed Box)

### Configuration-Driven Behavior Tests
**What it does**: *Ensures the application respects environment variables and maintains proper state across sessions*

**Test Case 1: Summarization Interval Configuration**
```
Environment Variables:
- KAIRIX_SUMMARIZATION_INTERVAL=20
- KAIRIX_MESSAGE_RETENTION_WINDOW=20
- KAIRIX_AGENT_CONFIGURATION_SET_KEY=test-agent
- KAIRIX_N_SUMMARIES_PER_MESSAGE=3
- KAIRIX_USER_NAME=TestUser
- KAIRIX_PERSONA_NAME=TestPersona

Test Steps:
1. Start application with above environment
2. Send 19 user messages with responses
3. Verify NO summarization occurs (check DB: memory_shards table should be empty)
4. Send 20th message
5. Verify summarization triggers
6. Check DB: Verify memory_shard created with:
   - agent_id matches configuration
   - embedding is not null
   - memory_text contains summary of 20 messages
   - timestamp is recent
7. Continue with 19 more messages
8. Send 40th message
9. Verify second summarization occurs
10. Check DB: Verify 2 memory_shards exist
```

**Test Case 2: Message Retention Window Enforcement**
```
Environment Variables:
- KAIRIX_MESSAGE_RETENTION_WINDOW=20
- Other required vars as above

Test Steps:
1. Start fresh application instance
2. Send 30 message pairs (user + assistant)
3. Query conversation history via API
4. Verify only last 20 messages returned
5. Check DB directly:
   - Query: SELECT COUNT(*) FROM conversation_messages WHERE agent_id=? AND user_id=?
   - Verify all 30 messages exist in DB
   - Query with window: SELECT * FROM conversation_messages ORDER BY sequence_number DESC LIMIT 20
   - Verify correct 20 messages returned
6. Restart application
7. Query conversation history again
8. Verify same 20 recent messages returned (persistence check)
```

**Test Case 3: Self-Reflection Loop Execution**
```
Data Prerequisites:
- Clean database
- Environment configured as above

Test Steps:
1. Start application
2. Send user message: "I love hiking in the mountains"
3. Wait for assistant response
4. Check async task execution:
   - Monitor logs for reflection perceptor activation
   - Verify self_perception stimulus created
5. Check DB after response:
   - conversation_messages table has both messages
   - Verify sequence numbers are correct
6. Continue until 20 messages accumulated
7. After summarization triggers:
   - Check memory_shards table for new entry
   - Verify embedding vector stored
   - Check memory_text reflects conversation themes
8. Send new message: "What outdoor activities do I enjoy?"
9. Verify response references hiking (from memory)
10. Check logs show SummaryInsightPerceptor retrieved memory
```

**Test Case 4: Cross-Session State Persistence**
```
Test Steps:
1. Session 1:
   - Start application
   - Send 10 messages about "Project Alpha"
   - Verify conversation stored
   - Stop application

2. Session 2:
   - Start application with same config
   - Send message: "What were we discussing about Project Alpha?"
   - Verify response shows continuity
   - Check DB shows all messages from both sessions
   - Send 10 more messages (total 20)
   - Verify summarization triggers
   - Stop application

3. Session 3:
   - Start application
   - Query for memories about "Project Alpha"
   - Verify memory shard retrieved
   - Verify conversation continues seamlessly
```

**Test Case 5: Configuration Change Impact**
```
Test Steps:
1. Start with KAIRIX_SUMMARIZATION_INTERVAL=10
2. Send 10 messages
3. Verify summarization occurs
4. Stop application
5. Start with KAIRIX_SUMMARIZATION_INTERVAL=5
6. Send 5 more messages
7. Verify new summarization triggers after 5 (not 10)
8. Check DB shows both memory shards
9. Verify different interval configurations coexist
```

### Database Verification Queries

**For Open-Box Testing:**
```sql
-- Check conversation messages
SELECT role, content, sequence_number, created_at 
FROM conversation_messages 
WHERE agent_id = ? AND user_id = ?
ORDER BY sequence_number DESC;

-- Check memory shards
SELECT id, memory_text, embedding IS NOT NULL as has_embedding, created_at
FROM memory_shards
WHERE agent_id = ?
ORDER BY created_at DESC;

-- Check reflection execution
SELECT COUNT(*) as total_messages,
       MAX(sequence_number) as latest_seq,
       (SELECT COUNT(*) FROM memory_shards WHERE agent_id = ?) as shard_count
FROM conversation_messages
WHERE agent_id = ? AND user_id = ?;

-- Verify entities created from conversations
SELECT e.name, e.entity_type, COUNT(l.id) as relationship_count
FROM entities e
LEFT JOIN linkages l ON e.id = l.source_id OR e.id = l.target_id
WHERE e.agent_id = ?
GROUP BY e.id;
```

### Performance and Load Tests

**Test Case 6: High-Volume Message Processing**
```
Environment:
- KAIRIX_SUMMARIZATION_INTERVAL=100
- KAIRIX_MESSAGE_RETENTION_WINDOW=50

Test Steps:
1. Send 200 messages rapidly (simulate active conversation)
2. Monitor:
   - Response times remain under 2 seconds
   - Memory usage stays bounded
   - DB writes don't block responses
3. Verify:
   - Exactly 2 summarizations occurred (at 100 and 200)
   - Window queries return exactly 50 messages
   - All 200 messages persisted in DB
   - Async reflection tasks complete successfully
```

## Web Application Frontend Tests

### Frontend Architecture Overview
**Technology Stack**: React-based SPA with real-time chat capabilities
**Testing Framework**: Playwright for browser automation (headless browser E2E tests)
**Test Environment**: Dedicated test user account in development environment

### User Journey Flow

#### 1. Authentication Flow (Future Implementation)
```
Note: To be implemented - currently documenting for future reference
- User arrives at login page
- Enters username and password
- Basic auth flow validates credentials
- Successful auth redirects to main chat interface
```

#### 2. Onboarding Workflow (Future Implementation)
```
Note: To be implemented - currently documenting for future reference
- First-time users see onboarding wizard
- Introduction to AI assistant capabilities
- Tutorial on voice features
- Privacy and data usage information
- Completion stores onboarding state
```

### Core Chat Interface Tests

**Test Case 1: Initial Page Load - New User**
```
Prerequisites:
- Test user account with NO conversation history
- Clean browser state (no localStorage)
- Server configured with test database

Test Steps:
1. Navigate to main chat URL
2. Wait for page load completion
3. Verify chat interface renders
4. Check for empty conversation state:
   - No messages displayed
   - Welcome prompt visible
   - Input field active and ready
5. Verify no API call for history (client-side check first)
6. If API call made, verify empty response
7. Confirm "new user" state indicators
```

**Test Case 2: Initial Page Load - Returning User**
```
Prerequisites:
- Test user with existing conversation history (20+ messages)
- Server has conversation data

Test Steps:
1. Navigate to main chat URL
2. Wait for page load
3. Verify browser checks localStorage first
4. If no local history, verify API call to /v1/conversations/history
5. Verify last N messages render correctly:
   - Correct message order
   - User/assistant role styling
   - Timestamps if displayed
6. Scroll position at bottom (most recent)
7. Input field ready for new message
```

**Test Case 3: Basic Chat Flow**
```
Prerequisites:
- Logged in user
- Chat interface loaded

Test Steps:
1. Type message: "Hello, how are you today?"
2. Press Enter or click Send
3. Verify:
   - Message appears in chat with user styling
   - Loading indicator shows
   - Input field clears and disables
4. Wait for response stream:
   - Verify streaming text appears progressively
   - Assistant message has correct styling
5. After response complete:
   - Loading indicator hidden
   - Input field re-enabled
6. Send follow-up: "What's the weather like?"
7. Verify conversation continuity maintained
```

**Test Case 4: Message Persistence Verification**
```
Test Steps:
1. Send 3 messages in conversation
2. Refresh browser page
3. Verify messages persist after reload
4. Open new incognito window
5. Login with same credentials
6. Verify same messages appear
7. Send message from window 2
8. Refresh window 1
9. Verify new message appears
```

### Audio Feature Tests

**Test Case 5: Voice Input (STT)**
```
Prerequisites:
- Browser with microphone permissions
- Mock audio input capability for testing

Test Steps:
1. Click microphone button
2. Verify recording indicator active
3. Simulate speech input (test audio file)
4. Click stop or wait for auto-stop
5. Verify:
   - Transcribed text appears in input field
   - User can edit before sending
   - Send button enabled
6. Send transcribed message
7. Verify normal chat flow continues
```

**Test Case 6: Voice Output (TTS)**
```
Prerequisites:
- Audio output enabled
- TTS service configured

Test Steps:
1. Send message to trigger response
2. Click speaker icon on assistant message
3. Verify:
   - Audio playback starts
   - Visual indicator shows playing state
   - Other UI remains responsive
4. Click pause/stop
5. Verify playback stops
6. Test auto-play setting if available
```

### Error Handling Tests

**Test Case 7: Network Disconnection**
```
Test Steps:
1. Start conversation normally
2. Simulate network disconnection
3. Attempt to send message
4. Verify:
   - Error message displays
   - Message remains in input field
   - Retry option available
5. Restore network
6. Retry sending
7. Verify message sends successfully
```

**Test Case 8: Server Error Response**
```
Test Steps:
1. Configure server to return 500 error
2. Send message
3. Verify:
   - Error message displays to user
   - Conversation state preserved
   - Retry mechanism available
4. Fix server
5. Verify recovery without data loss
```

### Performance Tests

**Test Case 9: Long Conversation Rendering**
```
Prerequisites:
- User with 100+ message history

Test Steps:
1. Load chat interface
2. Measure time to:
   - Initial render
   - Full history load
   - Become interactive
3. Verify:
   - Virtual scrolling if implemented
   - Smooth scrolling performance
   - No UI freezing
4. Send new message
5. Verify responsive despite history length
```

### Browser Automation Setup

**Playwright Configuration:**
```javascript
// playwright.config.js structure
{
  testDir: './e2e/web-app',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    ignoreHTTPSErrors: true,
    video: 'retain-on-failure',
  },
  projects: [
    // Desktop Browsers
    {
      name: 'chromium',
      use: { 
        viewport: { width: 390, height: 844 }, // Fixed mobile-like viewport
      },
    },
    {
      name: 'firefox', 
      use: { 
        viewport: { width: 390, height: 844 }, // Fixed mobile-like viewport
      },
    },
  ],
}
```

### Browser Compatibility Testing

**Test Case 10: Chrome & Firefox Compatibility**
```
Browsers: Chrome, Firefox
Fixed Viewport: 390x844 (portrait only, mobile-like layout)

Test Points:
1. Chat interface renders identically in both browsers
2. Fixed layout maintains same appearance regardless of window size
3. Message input and sending works
4. Streaming responses display properly
5. Voice features work in both browsers
6. Scrolling and history loading
7. Basic keyboard shortcuts (Enter to send)
```

**Test Case 11: Fixed Layout Verification**
```
Test Steps:
1. Open app in Chrome at 1920x1080
2. Verify layout stays at fixed 390px width centered
3. Resize browser window
4. Verify layout does NOT respond/change
5. Content should look like mobile layout always
6. Test same in Firefox
7. Verify identical appearance
```

**Test Case 12: Voice Feature Testing**
```
Browsers: Chrome, Firefox

Test Steps:
1. Click microphone button
2. Grant browser permission for mic
3. Record test message
4. Verify transcription appears
5. Send transcribed message
6. Test voice output (TTS)
7. Verify works in both browsers
8. Note any browser-specific limitations
```

**Test Execution Notes:**
- All tests use UI interactions only (no direct API calls)
- Screenshots on failure for debugging

## Agent Notebook Feature Tests

### Notebook Functionality Tests
**What it does**: *The agent's personal note-taking system - allows agents to record observations and thoughts at their own discretion*

**Test Case 1: Basic Notebook Writing**
```
Prerequisites:
- Test agent configured with notebook tool access
- Clean notebook state

Test Steps:
1. User: "Remember that my favorite color is blue"
2. Agent responds and internally writes to notebook
3. User: "I also love hiking on weekends"
4. Agent responds and updates notebook
5. Backend verification:
   - Query notebook entries via DB
   - Verify entries contain color preference
   - Verify hiking interest recorded
   - Check timestamps and agent_id
```

**Test Case 2: Notebook Recall Verification**
```
Test Steps:
1. Pre-populate notebook with entries about user preferences
2. User: "What notes have you taken about me?"
3. Agent should reference notebook content
4. Verify agent can:
   - Access own notebook entries
   - Synthesize information from notes
   - Not expose raw notebook format
5. User: "Do you remember what I told you about my hobbies?"
6. Verify response draws from notebook
```

**Test Case 3: Notebook Persistence Across Sessions**
```
Test Steps:
1. Session 1:
   - User shares personal information
   - Agent writes to notebook
   - End session
2. Session 2 (new conversation):
   - User: "What do you remember about me?"
   - Verify agent retrieves notebook entries
   - Information persists across sessions
```

## Programmatic Agent-to-Agent Testing

### Subjective System Integration Tests
**What it does**: *A test agent converses with the Kairix agent to verify end-to-end system functionality*

**Test Case 1: Agent Conversation Sanity Check**
```
Test Agent Configuration:
- Uses SRE agent or similar programmatic client
- Connects to dev environment Kairix instance
- Runs predefined conversation flows

Test Flow:
1. Test agent: "Hello, I'm running a system check"
2. Verify Kairix responds appropriately
3. Test agent: "Please remember that test_key_alpha is 42"
4. Test agent: "What is test_key_alpha?"
5. Verify Kairix recalls the information
6. Check backend for:
   - Conversation history created
   - Memory shards generated
   - Notebook entries if applicable
```

**Test Case 2: Memory Formation Verification**
```
Automated Test Sequence:
1. Test agent sends 25 messages about "Project Harmony"
2. Trigger reflection (exceeds summarization interval)
3. Test agent: "Summarize what you know about Project Harmony"
4. Verify response includes:
   - Key points from conversation
   - Evidence of memory formation
   - Semantic connections made
5. Backend checks:
   - Memory shard created
   - Embedding generated
   - Semantic graph updated
```

**Test Case 3: Multi-Turn Reasoning Test**
```
Test Conversation:
1. Test agent: "Alice works at TechCorp"
2. Test agent: "TechCorp is in San Francisco"  
3. Test agent: "Where does Alice work?"
4. Verify: "Alice works at TechCorp"
5. Test agent: "What city is Alice's workplace in?"
6. Verify inference: "San Francisco" (via semantic graph)
```

**Test Case 4: Environmental Context Integration**
```
Test Flow:
1. Test agent provides mock environment update:
   - Location: "Seattle"
   - Weather: "Rainy"
   - Time: "Evening"
2. Test agent: "Should I bring an umbrella?"
3. Verify Kairix uses context in response
4. Test agent: "What time of day is it?"
5. Verify environmental awareness
```

### Automated Test Execution

**Test Runner Configuration:**
```python
# Example test runner structure
class KairixIntegrationTest:
    def __init__(self):
        self.test_agent = SREAgent(
            endpoint="http://localhost:8000",
            api_key="test_key"
        )
    
    def run_sanity_checks(self):
        # Basic connectivity
        # Memory formation
        # Notebook functionality
        # Reflection triggers
        # Return pass/fail status
```

**Pre-Deployment Checklist:**
1. Run programmatic agent tests
2. Verify all subsystems responding
3. Check database writes occurring
4. Validate memory formation
5. Confirm reflection loops active
6. Green light for deeper automation tests
- Video recording for complex flows
- Run on real devices when possible (BrowserStack/Sauce Labs for CI)
- Clean state between tests
- Test in both light/dark modes if available