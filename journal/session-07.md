# Session 7 - Date: 2025-11-25

## Goals
- [x] Understand Letta API performance issues
- [x] Research local storage options for KMP
- [x] Learn expect/actual pattern for platform-specific code
- [x] Create SpeechRecognizer interface with expect/actual
- [x] Build dummy platform implementations
- [x] Add recording modal UI
- [x] Wire up Flow collection to update UI
- [x] Add iOS permission declarations
- [ ] Implement real iOS speech recognition (deferred to next session)

## What We Covered
- **Letta Performance**: Diagnosed slow API responses (25k token context)
- **Local Storage**: Surveyed SQLDelight, Multiplatform Settings, Okio, DataStore
- **expect/actual Pattern**: KMP's compile-time platform abstraction mechanism
- **Flow Basics**: Cold streams, callbackFlow, collecting in coroutines
- **Compose Dialogs**: AlertDialog for recording modal
- **iOS Permissions**: Info.plist entries for mic and speech recognition
- **Material Icons**: Extended icon set, AutoMirrored icons for RTL support

## Key Concepts Learned

1. **expect/actual Pattern**
   - `expect` in commonMain = "this must exist, implementation varies"
   - `actual` in each platform = "here's the real implementation"
   - Resolved at compile time, not runtime (unlike interfaces)
   - Can expect: class, fun, object, val

2. **Letta Context Limitations**
   - Can't configure message count separately from context window
   - Large core memory requires large context window
   - Forces tradeoff: big memory = slow responses
   - May need custom orchestration layer for fine control

3. **KMP Local Storage Options**
   | Use Case | Library |
   |----------|---------|
   | Key-value (settings) | Multiplatform Settings |
   | Structured data | SQLDelight |
   | File caching | Okio |
   - All storage code lives in commonMain (100% shared)
   - Platform-specific implementations wired automatically

4. **Flow for Streaming Data**
   - `flow { emit(value) }` creates cold stream
   - `callbackFlow { }` bridges callbacks to Flow
   - `.collect { }` consumes (suspend function, needs coroutine)
   - `awaitClose { }` handles cleanup when collection stops

5. **Closeable Gotcha**
   - `java.io.Closeable` is JVM-only, doesn't exist in Kotlin/Native
   - Options: define own interface, use kotlinx.io, or just use `stop()`
   - Simpler to avoid Java interfaces in common code

6. **iOS Speech Recognition Architecture**
   ```
   Mic → AVAudioEngine → Buffer → SFSpeechRecognizer → Text
   ```
   - Requires two permissions: microphone + speech recognition
   - Must declare in Info.plist AND request at runtime
   - Without plist entry → instant crash

7. **Material Icons**
   - Basic set included with compose.material3
   - Extended set: `compose.materialIconsExtended` (~2000 icons)
   - AutoMirrored variants flip for RTL languages
   - `Icon()` composable renders, `Icons.Filled.Mic` is just data

8. **Token to Text Ratio**
   - ~750 words per 1,000 tokens
   - 25k tokens ≈ 19,000 words ≈ 38 pages

## What We Built

**SpeechRecognizer.kt (commonMain)**
```kotlin
expect class SpeechRecognizer() {
    val output: Flow<String>
    fun stop()
}
```

**SpeechRecognizer.ios.kt** - Dummy implementation with iOS-biased opinions
**SpeechRecognizer.android.kt** - Dummy implementation with Android-biased opinions

**App.kt Updates:**
- Added recording state management (`inRecordingState`, `speechRecognizer`, `recordedTextBuffer`)
- `startRecording()` creates SpeechRecognizer, launches Flow collection
- `stopRecording()` stops recognition, re-enables button
- AlertDialog shows live transcript during recording
- Mic button using Material Icons

**Info.plist:**
- Added `NSMicrophoneUsageDescription`
- Added `NSSpeechRecognitionUsageDescription`

## Insights & Aha Moments

- **"Platform folders are just entry points"**: expect/actual keeps platform code minimal
- **"Letta's limitation is real"**: Can't separate memory size from context window - may need custom solution
- **"Declarative UI requires constant refactoring"**: The complexity tax is ongoing, not one-time
- **"Don't over-refactor"**: Build first, clean up when it hurts, not before
- **"Closeable is Java baggage"**: Simple `stop()` method is cleaner for KMP

## Challenges & Solutions

- **Challenge**: `java.io.Closeable` doesn't exist in Kotlin/Native
- **Solution**: Dropped interface, used simple `stop()` method instead

- **Challenge**: expect class needs explicit constructor
- **Solution**: Add `()` to declaration: `expect class SpeechRecognizer()`

- **Challenge**: Icon not showing in button
- **Solution**: Was using `Icons.Filled.Send` directly instead of wrapping in `Icon()` composable

- **Challenge**: IntelliJ running slow
- **Solution**: Fixed `idea.vmoptions` - had `-Xmx8192` (bytes!) instead of `-Xmx4096m` (megabytes)

- **Challenge**: Flow not updating UI
- **Solution**: Launch coroutine in `startRecording()` to collect from `output` Flow

## Next Steps

**Continue Speech Recognition:**
- [ ] Implement real iOS SpeechRecognizer using SFSpeechRecognizer
- [ ] Handle runtime permission requests
- [ ] Test on real device (simulator mic is limited)
- [ ] Add error handling for permission denied

**After STT Works:**
- [ ] Add text-to-speech for AI responses
- [ ] Local storage with SQLDelight
- [ ] Custom context orchestration layer

## Questions/Blockers
- Real iOS implementation deferred to next session
- Need real device to properly test speech recognition
- May need to handle permission denied gracefully in UI

## Key Decisions Made

- **Skip DI for now**: Not enough complexity to justify Koin setup yet
- **Simple `stop()` over Closeable**: Avoid Java interface complications
- **Request permissions on mic tap**: Better UX than requesting on app launch
- **Dummy implementation first**: Validate UI flow before real platform code
- **Keep Android dummy for now**: Focus on iOS first, Android later

## Technical Notes

**Architecture:**
- expect/actual provides compile-time platform abstraction
- Flow bridges platform callbacks to reactive streams
- State hoisting keeps recording state in App.kt
- Dialog controlled by boolean state (`inRecordingState`)

**Files Modified:**
- `SpeechRecognizer.kt` (commonMain) - expect declaration
- `SpeechRecognizer.ios.kt` - dummy actual
- `SpeechRecognizer.android.kt` - dummy actual
- `App.kt` - recording UI and state
- `Info.plist` - iOS permissions
- `build.gradle.kts` - added materialIconsExtended
- `idea.vmoptions` - fixed JVM heap settings

## Philosophical Insights

- **"Declarative UI = continuous refactoring tax"**: Unlike imperative where you hack and accumulate debt, declarative forces you to pay complexity costs upfront and continuously
- **"Don't over-refactor"**: Wait until code is copy-pasted 3+ times or you can't find where to add features
- **"Make it work → make it right → make it fast"**: Most people oscillate between 1 and 2 forever
- **"Every platform has permissions theatre"**: iOS requires both plist AND runtime request - belt and suspenders

## Session Victory

**First expect/actual implementation!** Built the full pattern:
- Common interface in shared code
- Platform-specific (hilarious) dummy implementations
- UI that consumes the Flow and updates live
- iOS permissions configured and ready

The architecture is in place - next session we swap dummy for real iOS speech recognition!
