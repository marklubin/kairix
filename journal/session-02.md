# Session 2 - Date: 2025-11-22

## Goals
- [x] Explore project structure in detail
- [x] Understand Gradle configuration files and their purposes
- [x] Understand KMP source sets (commonMain, androidMain, iosMain)
- [x] Map out the Kotlin library ecosystem in the project
- [ ] Get IntelliJ navigation working (Cmd+Click)
- [ ] Run the app on simulators

## What We Covered
- **Project Structure**: Explored the composeApp module and its source sets (commonMain, androidMain, iosMain)
- **Gradle Configuration**: Learned the differences between settings.gradle.kts, build.gradle.kts, and gradle.properties
- **Gradle Concepts**: Understood Gradle's hierarchical nature, wrapper script, and sync vs build
- **Source Sets Architecture**: Deep dive into how KMP layers platform-specific code over shared code
- **Library Stack**: Complete overview of Compose MP, Ktor, Koin, Coil, and kotlinx.serialization
- **IntelliJ Navigation**: Troubleshooting Cmd+Click and learning IDE shortcuts

## Key Concepts Learned

1. **Gradle File Purposes**
   - `settings.gradle.kts`: Project structure ("what modules exist?")
   - `build.gradle.kts`: Build instructions ("how to build?", dependencies, plugins)
   - `gradle.properties`: Runtime configuration (JVM memory, feature flags)
   - `gradlew`: Generated wrapper script (never manually edit)

2. **Gradle Hierarchical Nature**
   - Unlike npm/uv which are mostly flat, Gradle uses parent → child inheritance
   - Root build.gradle.kts can configure all subprojects
   - Similar to Justfiles but more powerful for sharing configuration

3. **KMP Source Sets (The Key Insight!)**
   - Source sets are layered: `commonMain` (base) + `androidMain`/`iosMain` (platform overlays)
   - 87% of code in this project lives in `commonMain` (13/15 files)
   - Platform folders are just "entry points" - the on-ramp to shared code
   - Both platforms call the same `App()` composable from different starting points

4. **Execution Flow Pattern**
   - Android: `MainActivity.onCreate()` → `setContent { App() }` → shared `App.kt`
   - iOS: `MainViewController()` → `ComposeUIViewController { App() }` → shared `App.kt`
   - From that point forward, 100% of UI code is shared

5. **Why Platform Folders Exist**
   - Different entry points (ComponentActivity vs UIViewController)
   - Platform-specific APIs (expect/actual pattern)
   - Platform-specific dependencies (OkHttp for Android, Darwin for iOS)

6. **Kotlin Multiplatform Library Ecosystem**
   - **UI**: Compose Multiplatform 1.8.2 (Material 3, Navigation, Lifecycle)
   - **Networking**: Ktor 3.1.3 (cross-platform HTTP with platform-specific engines)
   - **Serialization**: kotlinx.serialization (built-in, type-safe JSON)
   - **Images**: Coil 3.2.0 (KMP-compatible image loading)
   - **DI**: Koin 4.1.0 (lightweight, no codegen)

7. **Gradle Sync vs Build**
   - Sync (IDE): IntelliJ reads build files to understand project structure
   - Build (compilation): Downloads dependencies, compiles code, packages app
   - Sync ≈ reading pyproject.toml; Build ≈ `uv sync` + `uv build`

8. **Build-time vs Runtime Configuration**
   - Gradle can inject gradle.properties into code via BuildConfig (Android) or BuildKonfig (KMP)
   - Gradle does dependency *management* (libraries), NOT dependency *injection* (runtime)
   - DI is handled by Koin at runtime, Gradle just provides the library

## What We Built
- Nothing new in this session - focused on understanding the existing template structure
- Deep exploration of all source files and configuration files

## Insights & Aha Moments
- **Platform folders as "launchers"**: The realization that `androidMain` and `iosMain` are just the front door to the shared house - minimal code that immediately hands off to `commonMain`
- **Gradle's hierarchical philosophy**: Understanding why Gradle has so many files - it's designed for multi-module projects with inheritance, unlike npm's independence model
- **Source set layering visual**: The Photoshop layers analogy clicked - each platform sees their layer + the common base layer underneath
- **Library ecosystem maturity**: KMP has a complete, modern stack (Ktor, Koin, Coil) that rivals platform-specific ecosystems

## Challenges & Solutions
- **Challenge**: Confusion about why platform folders exist if UI is "shared"
- **Solution**: Walked through execution flow from app launch to shared code, showing platform folders are just 13% of code (entry points only)

- **Challenge**: Understanding the relationship between multiple Gradle files
- **Solution**: Used table of contents / recipe / oven temperature analogy to clarify settings vs build vs properties

- **Challenge**: IntelliJ Cmd+Click navigation not working
- **Solution**: Identified likely causes (Gradle sync incomplete, project still indexing, KMP plugin issues). Suggested running `./gradlew build` and checking sync status.

## Next Steps
- [ ] Fix IntelliJ navigation (complete Gradle build: `./gradlew build`)
- [ ] Run app on Android emulator
- [ ] Run app on iOS simulator
- [ ] Make a small UI change and see it reflect on both platforms
- [ ] Explore expect/actual pattern for platform-specific code
- [ ] Deploy to physical iPhone (code signing setup)

## Questions/Blockers
- IntelliJ navigation still not working - need to complete Gradle build and verify indexing
- KMP plugin installation issues mentioned but not fully resolved
- Haven't verified Xcode command line tools are installed for iOS builds
