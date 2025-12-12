---

## Session 24 - 2025-12-07

### Goals
- [x] Add SQLDelight for local event persistence
- [x] Load last 20 events on app startup
- [x] Fix timestamp display to show date for historical events
- [x] Handle event deduplication at DB level
- [x] Fix various edge cases (disconnection, parse errors, resource cleanup)
- [x] Update session_boundary event schema

### What We Covered
- SQLDelight integration in Kotlin Multiplatform
- expect/actual pattern for platform-specific database drivers
- iOS static framework linking requirements
- xcconfig files for declarative Xcode build settings

### Key Concepts Learned

1. **SQLDelight Setup for KMP**: SQLDelight generates Kotlin code from `.sq` files. Requires:
   - Plugin in build.gradle.kts
   - SQL schema files in `src/commonMain/sqldelight/`
   - Platform-specific drivers (NativeSqliteDriver for iOS)

2. **expect/actual for Database Driver**:
   ```kotlin
   // commonMain
   expect class DriverFactory() {
       fun createDriver(): SqlDriver
   }

   // iosMain
   actual class DriverFactory {
       actual fun createDriver(): SqlDriver {
           return NativeSqliteDriver(KairixDatabase.Schema, "kairix_events.db")
       }
   }
   ```

3. **iOS Static Framework Linking**: When using a static framework (`isStatic = true`), the consuming iOS app must link any native libraries the framework uses. SQLDelight's native driver uses SQLite, so the iOS app needs `-lsqlite3` linker flag.

4. **xcconfig for Declarative Build Settings**: Instead of manually adding frameworks in Xcode GUI, use `Config.xcconfig`:
   ```
   OTHER_LDFLAGS = $(inherited) -lsqlite3
   PRODUCT_NAME = $(TARGET_NAME)
   ```
   The project already referenced `Configuration/Config.xcconfig` - we just created the file.

5. **DB-Level Deduplication**: Using `INSERT OR IGNORE` with primary key prevents duplicate events:
   ```sql
   INSERT OR IGNORE INTO AgentEventEntity(id, ...) VALUES (?, ...);
   ```
   Combined with `eventExists` check for explicit feedback on whether insert happened.

### What We Built

**New Files:**
- `composeApp/src/commonMain/sqldelight/org/kairix/kairix_app/db/AgentEvent.sq`
  - Table schema, indexes, queries for event persistence

- `composeApp/src/commonMain/kotlin/org/kairix/kairix_app/db/DriverFactory.kt`
  - expect class for SqlDriver creation

- `composeApp/src/iosMain/kotlin/org/kairix/kairix_app/db/DriverFactory.ios.kt`
  - actual iOS implementation using NativeSqliteDriver

- `composeApp/src/commonMain/kotlin/org/kairix/kairix_app/db/EventRepository.kt`
  - Repository pattern with `insertEvent()`, `loadRecentEvents()`, `eventExists()`
  - All operations on `Dispatchers.IO`

- `iosApp/Configuration/Config.xcconfig`
  - Declarative linker flags for sqlite3

**Modified Files:**
- `gradle/libs.versions.toml` - Added SQLDelight 2.0.2 deps
- `composeApp/build.gradle.kts` - SQLDelight plugin, linkerOpts
- `EventSession.kt` - Repository injection, persistence, deduplication
- `EventModels.kt` - Added `ParseErrorEvent`, updated `session_boundary` schema
- `App.kt` - Repository creation, combined load+connect in LaunchedEffect
- `EventCard.kt` - Timestamp now shows "Dec 7 14:30" format

### Insights & Aha Moments

- **Static vs Dynamic frameworks**: Static frameworks embed code but not library dependencies - those must be resolved by the final app. Dynamic frameworks resolve their own dependencies.

- **xcconfig quirks**: If an xcconfig file is referenced but missing, Xcode ignores it. Once created, it overrides settings - we had to add `PRODUCT_NAME = $(TARGET_NAME)` to preserve the default.

- **SQLDelight query class naming**: The generated queries class name comes from the `.sq` filename, not the table name. `AgentEvent.sq` → `agentEventQueries`, not `agentEventEntityQueries`.

### Challenges & Solutions

- **Challenge**: iOS build failed with undefined sqlite3 symbols
- **Solution**: Static frameworks require explicit linking. Added `linkerOpts("-lsqlite3")` in Gradle, but that only affects the framework build. iOS app also needs it via xcconfig.

- **Challenge**: xcconfig not being picked up
- **Solution**: Project expected file at `iosApp/Configuration/Config.xcconfig`, not `iosApp/Config.xcconfig`

- **Challenge**: xcconfig cleared PRODUCT_NAME
- **Solution**: xcconfig overrides, not merges. Added `PRODUCT_NAME = $(TARGET_NAME)` to preserve default.

### Architecture Update

```
App Startup                          Runtime
┌─────────────────────────────┐     ┌─────────────────────────────┐
│ LaunchedEffect(endpoint)    │     │ WebSocket Frame             │
│   ├─ disconnect()           │     │   ├─ Parse AgentEvent       │
│   ├─ loadPersistedEvents()  │     │   ├─ Check displayedEventIds│
│   │    └─ DB: SELECT last 20│     │   ├─ DB: INSERT OR IGNORE   │
│   └─ connect(eventsUrl)     │     │   └─ Add to StateFlow       │
└─────────────────────────────┘     └─────────────────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ UI: LazyColumn  │
                                    │ EventCard(event)│
                                    └─────────────────┘
```

### Next Steps
- [ ] Test persistence across app restarts
- [ ] Verify deduplication works when switching endpoints
- [ ] Consider adding event cleanup/pruning for old events
- [ ] Add connection status indicator for events WebSocket

### Questions/Blockers
- Xcode 26 beta has SwiftUICore compatibility issues - may affect future builds
- Consider whether to add Android SQLite driver for cross-platform testing
