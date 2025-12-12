# Session 14 - Date: 2025-12-01

## Goals
- [x] Rebuild KMP voice app from scratch (previous project lost)
- [x] Set up proper multiplatform project structure
- [x] Create custom theme
- [x] Build basic connection toggle UI
- [x] Design audio streaming architecture

## What We Covered
- **Project Setup**: Fixed IntelliJ's nested folder structure, created proper commonMain/iosMain split
- **expect/actual Pattern**: Refresher on KMP's compile-time platform abstraction
- **Custom Theme**: Generated vibrant color scheme using Material Theme Builder
- **UI Components**: FloatingActionButton, Icons, Box layout, conditional rendering
- **Audio Architecture**: Designed separation between platform audio and shared WebSocket/framing code
- **iOS vs Android Background**: Fundamental differences in app lifecycle for background audio
- **Pipecat Protocol**: Reviewed protobuf frame format (AudioRawFrame, TextFrame, etc.)

## Key Concepts Learned

1. **Platform Audio Boundary**
   - Platform layer: Pure audio I/O (knows nothing about Pipecat/WebSocket)
   - Shared layer: PipecatCodec (protobuf) + VoiceSession (WebSocket lifecycle)
   - Clean separation means swapping Pipecat later only changes codec

2. **Asymmetric Audio Flow**
   - Mic → Server: Platform emits chunks, VoiceSession controls send timing
   - Server → Speaker: Play immediately as frames arrive (no buffering needed)

3. **iOS vs Android Background Audio**
   - iOS: App process stays alive, just enable background mode in plist
   - Android: Activity gets killed, need Foreground Service (separate component that survives)
   - iOS treats background as privilege; Android treats foreground as exception

4. **System AEC (Echo Cancellation)**
   - iOS: `AVAudioSession` with `.playAndRecord` + `.voiceChat` mode
   - Android: `AudioRecord` with `VOICE_COMMUNICATION` source
   - Platform configures this - it's a setup flag, not custom DSP

5. **AVAudioEngine Architecture** (refresher from Session 8)
   - `AVAudioSession` = policy layer ("I want to record with AEC")
   - `AVAudioEngine` = data layer (inputNode → tap → outputNode)
   - Must configure session BEFORE starting engine

6. **Buffer Conversion**
   - iOS gives `AVAudioPCMBuffer` with float32 samples (-1.0 to 1.0)
   - Server expects Int16 PCM bytes (-32768 to 32767)
   - Need conversion: `(floatSample * 32767).toShort()`

## What We Built

**Project Structure:**
```
kairix-app/
├── composeApp/src/
│   ├── commonMain/kotlin/org/kairix/kairix_app/
│   │   ├── App.kt                 # Main UI with mic toggle
│   │   ├── ConnectionState.kt     # Enum: DISCONNECTED, CONNECTING, CONNECTED, ERROR
│   │   ├── audio/
│   │   │   └── AudioStream.kt     # expect class for platform audio
│   │   └── theme/
│   │       └── Theme.kt           # Custom vibrant colors
│   └── iosMain/kotlin/org/kairix/kairix_app/
│       ├── MainViewController.kt  # iOS entry point
│       └── audio/
│           └── AudioStream.ios.kt # actual class (scaffold, not implemented)
└── iosApp/                        # Xcode wrapper
```

**UI:**
- Large FloatingActionButton at bottom center
- Mic/MicOff icons based on connection state
- Status text at top ("Ready" / "Listening...")
- Custom theme with lime green primary, cyan secondary

**AudioStream Interface:**
```kotlin
expect class AudioStream(sampleRateIn: Int, sampleRateOut: Int) {
    fun startCapture(onAudioChunk: (ByteArray) -> Unit)
    fun stopCapture()
    fun playAudio(data: ByteArray)
    fun stopPlayback()
}
```

## Insights & Aha Moments

- **"Platform code should be Pipecat-agnostic"**: Keep platform layer as pure audio I/O, shared layer handles protocol specifics
- **"iOS background is trivial, Android is architecture"**: iOS just keeps your app alive; Android requires rethinking where code lives
- **"Interruption matters"**: Decided against mute-during-playback approach; natural conversation needs barge-in support

## Challenges & Solutions

- **Challenge**: IntelliJ created nested `kairix-app/kairix-app/` structure
- **Solution**: Manually moved files up one level, fixed paths

- **Challenge**: Build failed after restructure - missing Platform.kt expect declaration
- **Solution**: Removed unused Platform.ios.kt (Greeting demo code not needed)

- **Challenge**: Where should audio chunking decisions live?
- **Solution**: Platform emits continuously; VoiceSession controls send cadence

## Next Steps
- [ ] Implement iOS AudioStream (AVAudioEngine capture + playback)
- [ ] Add iOS background audio capability (Info.plist entry)
- [ ] Create PipecatCodec (protobuf encode/decode in commonMain)
- [ ] Create VoiceSession (WebSocket lifecycle + orchestration)
- [ ] Wire toggle button to VoiceSession
- [ ] Test end-to-end with Python backend

## Questions/Blockers
- Need to implement AVAudioPCMBuffer → ByteArray conversion
- Playback side: use AVAudioPlayerNode or separate playback engine?
- Sample rate mismatch: input 16kHz, output 22050Hz - how to handle in single engine?

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      commonMain                              │
│  ┌──────────────┐    ┌────────────────┐    ┌─────────────┐  │
│  │ VoiceSession │───▶│ PipecatCodec   │───▶│ Ktor WS     │  │
│  │ (orchestrator)│    │ (frame encode/ │    │ Client      │  │
│  │              │    │  decode)       │    │             │  │
│  └──────────────┘    └────────────────┘    └─────────────┘  │
│         │                                                    │
│         │ ByteArray in/out                                   │
│         ▼                                                    │
│  ┌──────────────┐                                           │
│  │ AudioStream  │  ◄── expect class                         │
│  │ (interface)  │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                   ┌───────────────┐
                   │   iosMain     │
                   │               │
                   │ AVAudioEngine │
                   │ + AEC config  │
                   └───────────────┘
```
