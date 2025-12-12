# Session 8 - Date: 2025-11-26

## Goals
- [x] Understand iOS speech recognition APIs
- [x] Learn Kotlin/Native iOS interop
- [x] Implement real SpeechRecognizer for iOS
- [x] Bridge iOS callbacks to Kotlin Flow
- [x] Test on real device

## What We Covered
- **iOS Audio Architecture**: AVAudioSession (policy) vs AVAudioEngine (data)
- **Speech Recognition Pipeline**: Audio tap → buffer → recognition request → callback
- **Kotlin/Native Interop**: Calling Objective-C APIs from Kotlin
- **callbackFlow Pattern**: Bridging callback-based APIs to reactive Flow
- **Kotlin Syntax Gotchas**: Lambda creation, labeled returns, receivers

## Key Concepts Learned

1. **callbackFlow**
   - Bridges callback-based APIs to Kotlin Flow
   - `trySend()` = thread-safe emit from any thread (vs `emit()` which is same-coroutine only)
   - `awaitClose { }` = keeps flow alive, runs cleanup when flow ends
   - Store `scope = this` to call `close()` from outside

2. **iOS Audio Stack**
   ```
   AVAudioSession (policy) → AVAudioEngine (data) → Recognition Request → Callback
   ```
   - Session = tell iOS what you want (record, measurement mode)
   - Engine = actual audio capture pipeline
   - Must configure session BEFORE starting engine (implicit ordering)

3. **Speech Recognition Components**
   - `SFSpeechRecognizer` - the speech-to-text engine
   - `SFSpeechAudioBufferRecognitionRequest` - receives audio, bridges to recognizer
   - `recognitionTaskWithRequest()` - registers callback for transcription results
   - `inputNode.installTapOnBus()` - captures mic audio in buffers

4. **Kotlin/Native iOS Interop**
   - Binds to Objective-C, not Swift
   - Verbose enum names: `SFSpeechRecognizerAuthorizationStatusAuthorized`
   - C-style error pointers: `setCategory(x, null)`
   - Requires `@OptIn(ExperimentalForeignApi::class)`

5. **Lambda vs Code Block Gotcha**
   - `{ }` always creates a lambda in Kotlin
   - `callback { { x } }` = nested lambda, inner never runs (BUG!)
   - `callback { x }` = code runs directly (CORRECT)

6. **`return@label` Syntax**
   - Bare `return` inside lambda exits enclosing FUNCTION
   - `return@lambdaName` exits just the lambda
   - Kotlin quirk - other languages don't have this

7. **`this` in Receiver Lambdas**
   - `callbackFlow { }` has a receiver of type `ProducerScope`
   - Inside it, `this` = the ProducerScope
   - `trySend()` is really `this.trySend()`

8. **Flow Emission Pattern**
   - iOS emits full transcript each time, not deltas
   - "Hello" → "Hello world" → "Hello world how are you"
   - UI just replaces text, no concatenation needed

## What We Built

**SpeechRecognizer.ios.kt** - Full iOS implementation:
- Permission request with `SFSpeechRecognizer.requestAuthorization`
- Audio session configuration (Record category, Measurement mode)
- Recognition request with partial results enabled
- Tap on audio input node feeding buffers to request
- Result callback sending transcription to Flow via `trySend()`
- Cleanup in `awaitClose` (stop engine, remove tap, end request)
- `stop()` function closing the flow scope

## Insights & Aha Moments

- **"callbackFlow is the callback→generator bridge"**: Same as using asyncio.Queue in Python to bridge callbacks to async generators
- **"Extra braces = silent failure"**: `{ { code } }` creates nested lambda that never runs - subtle bug
- **"iOS interop is ugly but works"**: Objective-C bindings through Kotlin, then hidden inside actual class
- **"Implicit ordering is Apple's style"**: Session before engine, no enforcement, just fails mysteriously if wrong

## Challenges & Solutions

- **Challenge**: `trySend` not found
- **Solution**: Must be inside `callbackFlow { }` block - it's a method on ProducerScope

- **Challenge**: Lambda code not running
- **Solution**: Had extra `{ }` braces creating nested lambda that was never invoked

- **Challenge**: Understanding `awaitClose`
- **Solution**: It suspends forever keeping flow alive, runs cleanup block when flow closes

- **Challenge**: How to close flow from `stop()` function
- **Solution**: Store `scope = this` in callbackFlow, call `scope?.close()` from stop()

- **Challenge**: When iOS ends recognition, flow stays open
- **Solution**: Check `error != null` in callback, call `close()` to end flow

## Next Steps

- [ ] Add Android speech recognition implementation
- [ ] Add text-to-speech for AI responses
- [ ] Polish recording UI (loading state, better feedback)
- [ ] Local storage with SQLDelight
- [ ] Custom LLM context orchestration

## Questions/Blockers
- iOS auto-ends recognition after ~2-3 seconds of silence (may need restart logic later)
- Android implementation still uses dummy (hilarious opinions)

## Key Decisions Made

- **Simple permission handling**: Request inside callbackFlow, close if denied
- **No error pointer handling**: Pass null, assume success for v1
- **Full transcript replacement**: iOS emits cumulative text, UI just replaces
- **"Listening..." feedback**: One-line addition for immediate user feedback

## Technical Notes

**Architecture:**
```
User taps mic → SpeechRecognizer() created → output Flow collected
    → callbackFlow starts → permission requested → audio configured
    → recognition task registered → tap installed → engine starts
    → iOS sends transcriptions → trySend() → UI updates
    → User taps stop → scope.close() → awaitClose runs → cleanup
```

**Files Modified:**
- `SpeechRecognizer.ios.kt` - complete rewrite with real iOS implementation

## Philosophical Insights

- **"Every language has WTFs"**: Kotlin's `{ }` ambiguity, `return@label`, magic imports - but you learn them once
- **"Questioning is healthy"**: Doubting the tool choice is part of learning, persistence pays off
- **"Ship then polish"**: Got it working first, can add loading states and polish later

## Session Victory

**Real speech recognition working!** Built complete iOS implementation:
- Kotlin calling native iOS Speech framework
- Live transcription updating in real-time
- Proper cleanup on stop
- All from shared Kotlin code

Late night session but pushed through the complexity to a working feature!
