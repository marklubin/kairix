# Kairix Voice App - Build Plan

## Goal
Build a simple KMP voice client with an on/off toggle for streaming audio to/from the Python backend.

---

## Phase 1: Project Setup & Concept Refresh

### 1.1 Verify KMP Project Structure
Once IntelliJ creates the project, verify we have:
```
kairix-app/
├── composeApp/
│   └── src/
│       ├── commonMain/kotlin/    # Shared UI + logic (where 90% of code lives)
│       ├── androidMain/kotlin/   # Android entry point
│       └── iosMain/kotlin/       # iOS entry point
├── iosApp/                       # Xcode project wrapper
├── build.gradle.kts              # Root build config
└── gradle/libs.versions.toml     # Dependency versions
```

### 1.2 Concept Refresh (from Sessions 1-6)

**KMP Source Sets** - Remember the layering model:
- `commonMain` = base layer (shared code)
- `androidMain`/`iosMain` = platform overlays (entry points + platform APIs)
- Platform folders are just "on-ramps" to shared code

**Compose State Management** - The core patterns:
- `remember { }` = persist across recompositions
- `mutableStateOf()` = observable state (triggers UI updates)
- State hoisting = parent owns state, children receive props

**expect/actual Pattern** (Session 7-8):
- `expect` in commonMain = "this must exist"
- `actual` in each platform = "here's the implementation"
- Resolved at compile time, not runtime

---

## Phase 2: Simple UI - On/Off Toggle

### 2.1 What We're Building
A single screen with:
- Large toggle button (tap to connect/disconnect)
- Connection status indicator (Disconnected → Connecting → Connected)
- Visual feedback when streaming (pulse animation or similar)

### 2.2 State Model
```kotlin
enum class ConnectionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    ERROR
}

// In App.kt
var connectionState by remember { mutableStateOf(ConnectionState.DISCONNECTED) }
```

### 2.3 UI Components to Build

**MainScreen.kt** (commonMain):
- Root composable with centered toggle
- Uses `connectionState` to show appropriate UI
- Passes `onToggle: () -> Unit` callback up

**ConnectionToggle.kt** (commonMain):
- Large circular button
- Different colors/icons per state
- Animation for "connecting" state (optional)

**StatusIndicator.kt** (commonMain):
- Text label showing current state
- Color-coded (gray/yellow/green/red)

### 2.4 Key Compose Concepts to Apply

**Modifier chains** (Session 6):
```kotlin
Modifier
    .size(120.dp)
    .clip(CircleShape)
    .background(color)
    .clickable { onToggle() }
```

**Conditional rendering**:
```kotlin
when (connectionState) {
    DISCONNECTED -> Icon(Icons.Filled.Mic, "Start")
    CONNECTING -> CircularProgressIndicator()
    CONNECTED -> Icon(Icons.Filled.MicOff, "Stop")
    ERROR -> Icon(Icons.Filled.Error, "Error")
}
```

---

## Phase 3: Audio Streaming Infrastructure (No Implementation Yet)

### 3.1 Architecture Overview
```
┌─────────────────────────────────────────────────────────┐
│                    commonMain                           │
│  ┌─────────────┐    ┌─────────────┐    ┌────────────┐  │
│  │   App.kt    │───▶│VoiceSession │───▶│ expect     │  │
│  │  (UI state) │    │ (interface) │    │AudioStream │  │
│  └─────────────┘    └─────────────┘    └────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   ┌───────────┐       ┌───────────┐       ┌───────────┐
   │ androidMain│       │  iosMain  │       │  Backend  │
   │ actual     │       │ actual    │       │ (Python)  │
   │AudioStream │       │AudioStream│       │           │
   └───────────┘       └───────────┘       └───────────┘
```

### 3.2 Interfaces to Define (commonMain)

**VoiceSession** - High-level connection manager:
```kotlin
interface VoiceSession {
    val state: StateFlow<ConnectionState>
    suspend fun connect(serverUrl: String)
    suspend fun disconnect()
}
```

**AudioStream** - Platform-specific audio capture/playback:
```kotlin
expect class AudioStream() {
    fun startCapture(onAudioData: (ByteArray) -> Unit)
    fun stopCapture()
    fun playAudio(data: ByteArray)
}
```

### 3.3 Platform Implementation Notes

**iOS (from Session 8)**:
- AVAudioEngine for capture
- AVAudioSession configuration (record category, measurement mode)
- Must configure session BEFORE starting engine

**Android**:
- AudioRecord for capture
- AudioTrack for playback
- Requires RECORD_AUDIO permission

### 3.4 WebSocket Connection (from Sessions 9-10)
- Ktor WebSocket client (already learned in Session 5)
- Binary frames for audio data
- JSON frames for control messages (start/stop/status)

---

## Phase 4: Wire It Together

### 4.1 Connection Flow
```
User taps toggle
    → connectionState = CONNECTING
    → VoiceSession.connect(serverUrl)
        → Open WebSocket
        → Start AudioStream capture
        → Begin sending audio frames
    → connectionState = CONNECTED

User taps again
    → VoiceSession.disconnect()
        → Stop AudioStream
        → Close WebSocket
    → connectionState = DISCONNECTED
```

### 4.2 Error Handling
- WebSocket connection failure → ERROR state
- Audio permission denied → ERROR state with message
- Network timeout → Auto-reconnect or ERROR

---

## Implementation Order

1. **[NOW]** Wait for IntelliJ to create project structure
2. **[Phase 2]** Build UI components (toggle, status)
3. **[Phase 2]** Wire up state management
4. **[Phase 3]** Define interfaces (VoiceSession, AudioStream)
5. **[Phase 3]** Create dummy implementations (no real audio yet)
6. **[Phase 4]** Implement iOS AudioStream (AVAudioEngine)
7. **[Phase 4]** Implement Android AudioStream
8. **[Phase 4]** Add Ktor WebSocket client
9. **[Phase 4]** Test end-to-end with Python backend

---

## Learning Checkpoints

### After Phase 2 (UI):
- [ ] Can explain how `remember` and `mutableStateOf` work together
- [ ] Understand state hoisting pattern
- [ ] Know how to use `when` for conditional UI

### After Phase 3 (Interfaces):
- [ ] Understand expect/actual pattern
- [ ] Can explain why platform code is minimal
- [ ] Know the difference between interface and expect class

### After Phase 4 (Integration):
- [ ] Understand coroutine scopes in Compose
- [ ] Can explain Ktor WebSocket basics
- [ ] Know how iOS/Android audio APIs differ

---

## Questions to Discuss

1. **Sample rate**: What sample rate should we use? (16kHz for STT compatibility?)
2. **Audio format**: PCM 16-bit mono? Match what Deepgram expects?
3. **WebSocket protocol**: Binary frames for audio, JSON for control?
4. **Reconnection strategy**: Auto-reconnect on disconnect?

---

## Files We'll Create

```
composeApp/src/commonMain/kotlin/com/kairix/app/
├── App.kt                    # Root composable, state management
├── ui/
│   ├── MainScreen.kt         # Main screen layout
│   ├── ConnectionToggle.kt   # Big toggle button
│   └── StatusIndicator.kt    # Connection status text
├── voice/
│   ├── VoiceSession.kt       # Connection manager interface
│   └── AudioStream.kt        # expect class for audio
└── theme/
    └── Theme.kt              # Custom colors (vibrant like before!)

composeApp/src/iosMain/kotlin/com/kairix/app/voice/
└── AudioStream.ios.kt        # actual implementation

composeApp/src/androidMain/kotlin/com/kairix/app/voice/
└── AudioStream.android.kt    # actual implementation
```
