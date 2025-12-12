# Learning Kotlin Multiplatform - Project Guide

## Learning Approach

This project follows a hands-on, collaborative learning approach:

### Philosophy
- **Learn by doing** - Build real features rather than just reading about concepts
- **Guided exploration** - Balance between teaching concepts and letting you discover
- **Incremental complexity** - Start simple, build up to advanced features
- **Real-world focus** - Work toward the actual goal (AI voice interface app)
- **Collaboration over automation** - You'll implement key design decisions; I'll handle boilerplate

### How We Work Together
1. **I provide context** - Explain what we're building and why it matters
2. **You make decisions** - Choose approaches for meaningful features (2-10 lines of key logic)
3. **I handle scaffolding** - Set up structure, boilerplate, and routine code
4. **We learn together** - Insights about patterns, architecture, and how things connect

### When to Request Your Input
I'll ask you to contribute code when:
- There are multiple valid approaches (error handling strategies, data structures)
- Business logic involves design decisions
- Key algorithms or interface definitions need to be written
- The decision teaches an important concept

---

## Journal Entry Format

At the end of each learning session (or when you say "journal this"), create an entry in **`./journal/session-XX.md`** following this format:

### Session Template
```markdown
---

## Session [N] - [Date: YYYY-MM-DD]

### Goals
- [ ] Goal 1
- [ ] Goal 2

### What We Covered
- Topic 1: Brief description
- Topic 2: Brief description

### Key Concepts Learned
1. **Concept Name**: Explanation
2. **Concept Name**: Explanation

### What We Built
- Feature/file created
- Code written (file paths and key changes)

### Insights & Aha Moments
- Important realization or pattern discovered
- Connection to previous knowledge

### Challenges & Solutions
- **Challenge**: Description
- **Solution**: How we resolved it

### Next Steps
- [ ] Next task to tackle
- [ ] Questions to explore

### Questions/Blockers
- Any unresolved questions or blockers to address next time
```

---

## Learning Journal

**Session entries are stored in the `./journal/` directory:**
- [Session 1](./journal/session-01.md) - KMP setup, project structure
- [Session 2](./journal/session-02.md) - Gradle, source sets
- [Session 3](./journal/session-03.md) - Xcode compatibility, iOS build
- [Session 4](./journal/session-04.md) - First Kotlin code, Compose state
- [Session 5](./journal/session-05.md) - Letta API, Ktor, coroutines
- [Session 6](./journal/session-06.md) - UI polish, state hoisting
- [Session 7](./journal/session-07.md) - expect/actual, speech recognition design
- [Session 8](./journal/session-08.md) - iOS speech recognition implementation
- [Session 9](./journal/session-09.md) - Python backend, FastAPI, WebSockets
- [Session 10](./journal/session-10.md) - Pydantic, Anthropic streaming
- [Session 11](./journal/session-11.md) - Letta provider, Podman
- [Session 12](./journal/session-12.md) - Pipecat voice pipeline
- [Session 13](./journal/session-13.md) - UserTurnAggregator state machine
- [Session 14](./journal/session-14.md) - KMP voice app rebuild
- [Session 15](./journal/session-15.md) - Protobuf, VoiceSession, end-to-end
- [Session 16](./journal/session-16.md) - Progressive summarization design
- [Session 17](./journal/session-17.md) - Session summarization implementation
- [Session 18](./journal/session-18.md) - Soft reset fix, Docker deployment
- [Session 19](./journal/session-19.md) - Python CLI voice client
- [Session 20](./journal/session-20.md) - Deepgram TTS, logging, stability testing
- [Session 21](./journal/session-21.md) - Postgres events, LISTEN/NOTIFY, Alembic
- [Session 22](./journal/session-22.md) - Redis pub/sub events, transcript consolidation
- [Session 23](./journal/session-23.md) - KMP event display UI, sealed interface pattern

---

# Topics to Revisit Later

These are concepts that came up during sessions but need deeper exploration when there's more time/energy:

1. **Threading + Asyncio interaction** (Session 12, 2025-11-30)
   - Why `asyncio.get_event_loop()` fails in background threads
   - How `call_soon_threadsafe()` bridges threads to the event loop
   - The pattern: capture loop reference in main thread, use from background thread
   - Related: Python 3.10+ deprecation of `get_event_loop()` in favor of `get_running_loop()`

2. **Audio feedback loop prevention** (Session 12, 2025-11-30)
   - Mic picks up speaker output, causing echo/feedback
   - Solution: mute mic during TTS playback
   - Pipecat may have built-in support for this (check `allow_interruptions` behavior)

3. **VAD tuning - still too aggressive** (Session 12, 2025-11-30)
   - Even with `stop_secs=1.5` and `utterance_end_ms=2000`, messages still fragment
   - Possible causes to investigate:
     - VAD `min_volume` threshold may need adjustment
     - Deepgram may have additional endpointing settings
     - Check if there's a max utterance length somewhere
     - May need to disable VAD entirely and rely only on Deepgram's utterance detection
   - Debug by watching logs for "User stopped speaking" timing vs actual speech

4. **Barge-in / interruption handling** (Session 14, 2025-12-01)
   - System AEC may not be enough - user might want to interrupt AI mid-speech
   - Don't want to mute mic during playback (kills natural conversation)
   - Need to investigate: how does Pipecat's `allow_interruptions=True` actually work?
   - May need server-side logic to detect "user is speaking over TTS" vs "echo"

5. **VAD tuning per input source** (Session 20, 2025-12-05)
   - Current config: `stop_secs=1.5`, defaults for everything else
   - Available params: `confidence` (0.7), `start_secs` (0.2), `stop_secs`, `min_volume` (0.6)
   - Different mics/speakers/environments need different tuning
   - Consider: calibration process, runtime config, or per-client settings
   - Smart Turn Detection (`LocalSmartTurnAnalyzerV3`) may help but needs transport compatibility check
