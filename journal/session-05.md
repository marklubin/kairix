# Session 5 - Date: 2025-11-24

## Goals
- [x] Add real Letta API integration (replace MockLLMService)
- [x] Learn Ktor HTTP client library
- [x] Deep dive into Kotlin coroutines and Flow
- [x] Understand kotlinx.serialization
- [x] Handle streaming API responses (SSE)
- [x] Filter message types in UI
- [x] Deploy to physical iPhone

## What We Covered
- **Gradle Dependencies**: Added Ktor (HTTP client) and kotlinx.serialization
- **Letta API Integration**: Built custom streaming client from scratch
- **Coroutines Deep Dive**: suspend functions, Flow, rememberCoroutineScope(), continuations
- **Serialization**: @Serializable, @SerialName, polymorphic JSON parsing
- **Server-Sent Events (SSE)**: Manual parsing of streaming HTTP responses
- **Message Filtering**: Using nullable types and .let pattern to filter UI
- **iOS Deployment**: Successfully deployed to physical iPhone (code signing, trust certificates)

## Key Concepts Learned

1. **Ktor HTTP Client**
   - Cross-platform HTTP client for KMP
   - Platform-specific engines: OkHttp (Android), Darwin (iOS)
   - Install plugins: ContentNegotiation for JSON serialization
   - Configured with `HttpClient { }` builder DSL

2. **kotlinx.serialization**
   - Compile-time JSON serialization (no reflection)
   - `@Serializable` annotation on data classes
   - `@SerialName` maps JSON fields to properties (e.g., `message_type` → `messageType`)
   - `Json { ignoreUnknownKeys = true }` for lenient parsing
   - Manual polymorphic parsing: read discriminator field, deserialize to specific type

3. **Kotlin Coroutines (The Big One!)**
   - **Coroutines ≠ threads**: Lightweight async abstraction, many coroutines on one thread
   - **suspend functions**: Functions that can pause and resume without blocking
   - **Continuations**: How suspension works (compiler generates state machines)
   - **Event loop**: Single thread handles many coroutines via async I/O (epoll/kqueue)
   - **Structured concurrency**: Coroutines tied to scopes, auto-cancel on cleanup
   - `rememberCoroutineScope()`: Lifecycle-bound scope for Compose
   - `launch { }`: Fire-and-forget coroutine
   - **Not blocking**: `suspend` means "I might yield control", not "I'm on another thread"

4. **Flow (Kotlin's Async Streams)**
   - Cold async stream for multiple values over time
   - Like Python generators or JavaScript async iterators
   - `flow { emit(value) }` creates flow
   - `.collect { }` consumes flow (suspend function)
   - Perfect for streaming HTTP responses
   - Each collector gets its own stream (cold = restarts on collection)

5. **Server-Sent Events (SSE)**
   - W3C standard for HTTP streaming (`text/event-stream`)
   - Server sends multiple events over single connection
   - Format: `data: {json}\n\n` with optional `[DONE]`
   - Letta API uses SSE for streaming responses
   - Manual parsing: read lines, strip `data:` prefix, parse JSON

6. **Nullable Types (String?)**
   - Kotlin's type-safe null handling (like Option/Maybe)
   - `String?` can be null, `String` cannot
   - `.let { }` only executes if not null
   - Used for filtering: map to `String?`, only add non-null values

7. **Sealed Interfaces**
   - Exhaustive type hierarchy (like Rust enums)
   - All subtypes known at compile time
   - Perfect for API response types
   - `when` expression checks all cases

8. **Gradle Version Catalogs**
   - `gradle/libs.versions.toml` centralizes dependency versions
   - `[versions]`, `[libraries]`, `[plugins]` sections
   - Reference via `libs.ktor.client.core`
   - Reduces duplication, single source of truth

9. **Platform-Specific Dependencies**
   - `androidMain.dependencies { }`: OkHttp for Android
   - `iosMain.dependencies { }`: Darwin for iOS
   - `commonMain.dependencies { }`: Shared Ktor core
   - Each platform gets its native HTTP engine

10. **iOS Code Signing & Deployment**
    - Bundle identifier format: `com.domain.appname` (no underscores)
    - Config.xcconfig holds bundle ID and team ID
    - Apple's multi-step security: Trust Computer, Developer Mode, Trust Certificate
    - "Fetching debug symbols" = downloading debugging info (5-15 min first time)
    - Settings → General → VPN & Device Management → Trust Developer

## What We Built

**gradle/libs.versions.toml**:
- Added Ktor 3.0.3 and kotlinx-serialization 1.8.0 versions
- Defined 6 new libraries (ktor-client-core, content-negotiation, serialization, platform engines)
- Added kotlinxSerialization plugin

**composeApp/build.gradle.kts**:
- Applied kotlinxSerialization plugin
- Added platform-specific Ktor engines (OkHttp for Android, Darwin for iOS)
- Added common Ktor and serialization dependencies

**LettaTypes.kt** (93 lines):
- `LettaStreamingResponse` sealed interface
- 8 message types: SystemMessage, UserMessage, AssistantMessage, ReasoningMessage, Ping, ErrorMessage, StopReason, UsageStatistics
- `LettaMessageRequest` for API requests
- Full `@Serializable` annotations with `@SerialName` mappings

**LettaClient.kt** (89 lines):
- `streamMessages()` returns `Flow<LettaStreamingResponse>`
- POST to `/v1/agents/{agentId}/messages/stream`
- Manual SSE parsing: read lines from ByteReadChannel
- `parseMessage()` for polymorphic deserialization based on `message_type` field
- Lenient JSON parsing with `ignoreUnknownKeys = true`

**App.kt** (updated):
- Replaced MockLLMService with LettaClient
- Added coroutine scope: `rememberCoroutineScope()`
- `scope.launch { }` for async API calls
- `.collect { }` to consume streaming Flow
- Message filtering: only show AssistantMessage, ReasoningMessage, ErrorMessage
- Button disable/enable during API call
- Hardcoded API key and agent ID for now

**iosApp/Configuration/Config.xcconfig**:
- Fixed invalid bundle ID from `org.kairix.kmp_scaffold.kmp_scaffold` to `org.kairix.kmpscaffold`

## Insights & Aha Moments

- **Coroutines ≠ threads clicked**: Understanding suspension as "yielding control" not "spawning thread" was huge
- **Event loop analogy**: Node.js/JavaScript event loop made Kotlin coroutines click
- **Flow is cold streams**: Each collect() restarts the stream (vs hot channels that broadcast)
- **Gradle abstinence**: User said "I don't care about Gradle right now, just do it" - pragmatic!
- **Manual polymorphism is fine**: kotlinx.serialization's automatic polymorphism was overkill, manual parsing is clearer
- **Token streaming doesn't work**: Letta's `stream_tokens` parameter doesn't actually stream tokens, accepted step-level streaming
- **Apple's security theater**: Multiple steps to run on physical device felt excessive but completed
- **Real API on real device!**: Huge milestone - chatting with Letta AI on physical iPhone

## Challenges & Solutions

- **Challenge**: Gradle dependency management overwhelming (multiple files to update)
- **Solution**: User prioritized learning, delegated Gradle busywork. Updated libs.versions.toml and build.gradle.kts quickly.

- **Challenge**: Serialization error "Class discriminator was missing"
- **Solution**: Implemented manual polymorphic parsing in `parseMessage()` - read `message_type` field, use when statement to deserialize to specific type.

- **Challenge**: Understanding coroutines vs threads
- **Solution**: Deep dive into suspension mechanics, event loops, continuations. Used Node.js analogy. Clicked that suspend ≠ blocking.

- **Challenge**: Button re-enabled too early (timing bug)
- **Solution**: User placed `isButtonEnabled = true` outside `launch { }`. Moved inside after `.collect` completes.

- **Challenge**: Token streaming not working despite `stream_tokens: true`
- **Solution**: Tested both endpoints, confirmed Letta doesn't actually stream tokens. Accepted step-level streaming (reasoning, assistant, stop, usage as separate chunks) as sufficient.

- **Challenge**: Invalid bundle identifier preventing iOS deployment
- **Solution**: Changed Config.xcconfig from `org.kairix.kmp_scaffold.kmp_scaffold$(TEAM_ID)` to `org.kairix.kmpscaffold` (no underscores allowed).

- **Challenge**: Apple's multi-step security process
- **Solution**: Walked through: Trust Computer → Enable Developer Mode → iPhone restart → Wait for debug symbols → Trust Developer Certificate in Settings.

## Next Steps

**Completed This Session:**
- [x] Real LLM integration with Letta API
- [x] Streaming responses working
- [x] Coroutines and Flow learned
- [x] Deployed to physical iPhone

**Future Enhancements:**
- [ ] Move API key to secure storage (not hardcoded)
- [ ] Error handling UI (show errors gracefully)
- [ ] Style message bubbles (colors, rounded corners, alignment)
- [ ] Add loading indicators during API calls
- [ ] Auto-scroll to latest message
- [ ] Explore component libraries (Compose Cupertino for iOS look)
- [ ] Test on Android device
- [ ] Add text-to-speech (audio features)
- [ ] Explore expect/actual pattern for platform-specific code

## Questions/Blockers
- Token-level streaming doesn't work in Letta API (accepted step-level)
- Logging requires third-party library (no KMP stdlib logger) - using println() for now
- Haven't tested on Android device yet
- Need to explore secure key storage for production

## Key Decisions Made

- **Build own Letta client**: Chose to learn Ktor/coroutines rather than use SDK
- **Manual polymorphic parsing**: Clearer than automatic serialization magic
- **Step-level streaming sufficient**: Don't need token-by-token, reasoning steps are enough
- **Nullable types for filtering**: `String?` with `.let { }` pattern is idiomatic Kotlin
- **println() for logging**: No KMP stdlib logger, third-party libraries overkill for learning
- **Hardcoded credentials**: Fine for learning, will move to secure storage later
- **Trust Apple's process**: Frustrating but necessary for iOS development

## Technical Notes

**Architecture:**
- 100% shared code in `commonMain` (UI + networking)
- Platform-specific HTTP engines via source sets
- Coroutines for async work
- Flow for streaming responses
- State management with mutableStateOf and mutableStateListOf

**Performance:**
- Streaming responses work (step-level granularity)
- LazyColumn handles growing message list efficiently
- Coroutines are lightweight (no thread creation)

**iOS Deployment:**
- Successfully ran on physical iPhone
- App works identically to simulator
- Real-time chat with Letta AI working

**Frustrations:**
- Gradle's complexity (many files for dependencies)
- Letta's token streaming doesn't actually work
- Apple's multi-step security process ("permissions theatre")
- But: all overcome, app works!

## Philosophical Insights

- **"I don't care about Gradle right now"**: Pragmatic learning - focus on what matters (Kotlin/Compose), delegate boilerplate
- **"Why have an API called streaming then?"**: Questioning API design when behavior doesn't match name (Letta's streaming ambiguity)
- **"Apple makes all this permissions theatre so annoying"**: Frustration with security theater vs actual security
- **Persistence pays off**: Pushed through complexity, frustration, and tooling issues to get real working app on real device

## Session Victory

**From mock to real in one session!** Started with MockLLMService, ended with:
- Real Letta API integration
- Streaming responses working
- Running on physical iPhone
- Understanding coroutines, Flow, serialization, HTTP clients

This is a massive milestone - a real cross-platform AI chat app built from scratch in KMP!
