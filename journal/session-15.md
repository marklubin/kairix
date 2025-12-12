# Session 15 - Date: 2025-12-01

## Goals
- [x] Complete PipecatCodec with protobuf serialization
- [x] Create VoiceSession WebSocket orchestrator
- [x] Wire UI to VoiceSession
- [x] Test end-to-end with Python backend on physical iPhone
- [x] Add endpoint selector UI

## What We Covered
- **kotlinx-serialization-protobuf**: Hand-coded data classes matching Pipecat proto schema
- **Protobuf oneof pattern**: Sealed interface with holder data classes for discriminated unions
- **Ktor WebSocket client**: Platform-specific engines (Darwin for iOS)
- **StateFlow for reactive state**: Observable state pattern for UI binding
- **CoroutineScope lifecycle**: Session-scoped scope cancelled on disconnect
- **iOS permissions & background audio**: Info.plist entries for mic and audio background mode
- **Kotlin language features**: Extension functions, `object` singletons, mixin patterns

## Key Concepts Learned

1. **StateFlow = Reactive Callbacks**
   - "Reactive" is fancy word for callbacks with conventions
   - StateFlow always has current value, broadcasts changes
   - `collectAsState()` bridges to Compose - UI recomposes on change
   - Under the hood: `publisher.onChange(callback)` with lifecycle management

2. **`scope.launch` for async in UI**
   - UI callbacks (onClick) are regular lambdas, not suspend
   - `scope.launch { }` starts coroutine, returns immediately
   - Non-blocking - UI stays responsive
   - Similar to `asyncio.create_task()` in Python

3. **Session-scoped CoroutineScope**
   - `CoroutineScope(SupervisorJob() + Dispatchers.Default)`
   - All coroutines tied to session lifetime
   - `scope.cancel()` on disconnect cleans up everything
   - Avoids orphan coroutine leaks

4. **pbandk vs kotlinx-serialization-protobuf**
   - pbandk: Generate Kotlin from .proto files
   - kotlinx-serialization: Hand-write data classes with `@ProtoNumber`
   - Hand-coded is fine for small, stable schemas
   - Risk: field number mismatch = silent data corruption

5. **Extension Functions**
   - Syntax sugar: `"hello".scream()` = `scream("hello")`
   - Can't override real members (member always wins)
   - Must import to use - no monkey-patching
   - Like C# extension methods, not C++ friends

6. **Kotlin `object` = Singleton**
   - `object PipecatCodec` creates single instance
   - Call directly: `PipecatCodec.encodeAudioFrame(...)`
   - Good for stateless utilities

7. **Business Logic Owns State**
   - VoiceSession owns connection state, UI observes
   - UI is "dumb terminal" rendering current state
   - State transitions live with logic that causes them
   - Prevents UI/service state getting out of sync

## What We Built

**Frames.kt** - Pipecat protobuf data classes:
- `TextFrame`, `AudioRawFrame`, `TranscriptionFrame`, `MessageFrame`
- Sealed interface `FrameType` with holder classes for oneof
- `@ProtoNumber` annotations matching proto schema

**PipecatCodec.kt** - Encode/decode utilities:
- `encodeAudioFrame()` - PCM bytes → protobuf Frame
- `decodeFrame()` - protobuf bytes → FrameType
- `extractAudio()`, `extractText()` - convenience extractors

**VoiceSession.kt** - WebSocket + audio orchestration:
- `connect(url)` - opens WS, starts AudioStream, launches receive loop
- `disconnect()` - cancels scope, stops audio, closes WS
- `state: StateFlow<ConnectionState>` - reactive state for UI
- `transcription: StateFlow<String>` - latest transcription text
- Session-scoped CoroutineScope for proper lifecycle

**App.kt** - Updated UI:
- `Endpoint` enum with label + URL
- `FilterChip` selector for Carrizo/Salinas endpoints
- Chips disabled when connected
- VoiceSession wired to mic button
- Transcription display

**Info.plist** - iOS permissions:
- `NSMicrophoneUsageDescription` - mic permission prompt
- `UIBackgroundModes: audio` - background audio capability

**build.gradle.kts / libs.versions.toml**:
- Added Ktor 3.0.3 (client-core, websockets, darwin)
- Added kotlinx-serialization-protobuf 1.8.0

## Insights & Aha Moments

- **"Reactive = callbacks with better ergonomics"**: Strip away abstractions and it's just `onChange(callback)` with lifecycle management
- **"scope.launch doesn't block"**: Returns immediately, coroutine runs interleaved on event loop
- **"Business logic owns state"**: UI observes, doesn't manage - prevents sync issues
- **"Extension functions can't override"**: Member always wins, safer than it looks
- **"Session scope prevents leaks"**: Cancel scope = cancel all child coroutines

## Challenges & Solutions

- **Challenge**: `@JvmInline value class` not available in KMP
- **Solution**: Changed to `data class` for FrameType holders

- **Challenge**: CoroutineScope leak - creating new scope per audio chunk
- **Solution**: Created session-scoped scope, cancelled on disconnect

- **Challenge**: Wrong WebSocket endpoint (/, /ws, /voice)
- **Solution**: Trial and error - server was on `/voice`

- **Challenge**: Wrong port (8765 vs 8000)
- **Solution**: Checked server config, corrected to 8000

- **Challenge**: IDE complaining about missing expect/actual
- **Solution**: Build passes - IDE just slow to sync, ignore

## Files Created/Modified

**New Files:**
- `composeApp/src/commonMain/kotlin/.../pipecat/Frames.kt`
- `composeApp/src/commonMain/kotlin/.../pipecat/PipecatCodec.kt`
- `composeApp/src/commonMain/kotlin/.../voice/VoiceSession.kt`

**Modified:**
- `composeApp/src/commonMain/kotlin/.../App.kt` - VoiceSession + endpoint selector
- `composeApp/build.gradle.kts` - Ktor dependencies
- `gradle/libs.versions.toml` - Ktor version catalog
- `iosApp/iosApp/Info.plist` - permissions + background audio

## Next Steps
- [ ] Permission denial handling (graceful error when mic denied)
- [ ] Reconnect logic (reset from ERROR state)
- [ ] Sample rate validation (verify server sends expected rate)
- [ ] Audio jitter buffering (if choppy on poor network)
- [ ] Android implementation (AudioRecord + Foreground Service)

## Questions/Blockers
- None - end-to-end working on physical iPhone!

## Session Victory

**End-to-end voice streaming working!**
- iOS app connects to Python backend via Tailscale
- Audio capture → protobuf → WebSocket → server
- Server → WebSocket → protobuf → audio playback
- Endpoint selector for multiple servers
- Background audio enabled

Built complete voice client in one session - from codec to UI to deployment!
