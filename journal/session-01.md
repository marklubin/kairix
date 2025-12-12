# Session 1 - Date: 2025-11-22

## Goals
- [x] Set up development environment (IntelliJ, plugins)
- [x] Understand KMP vs Compose Multiplatform conceptual difference
- [x] Download and open Shared UI template project
- [ ] Explore project structure
- [ ] Run the app on simulators
- [ ] Deploy to physical iPhone

## What We Covered
- **IntelliJ Setup**: Installed Kotlin Multiplatform plugin, selected Java 21
- **KMP Concepts**: Understood the distinction between Kotlin Multiplatform (code-sharing platform) and Compose Multiplatform (UI framework)
- **Jetpack Compose vs Compose MP**: Learned that Compose MP is based on Jetpack Compose but extended to work cross-platform
- **Project Template Selection**: Chose "Shared UI Multiplatform App" template for maximum learning value

## Key Concepts Learned

1. **KMP vs Compose MP**
   - KMP = Code-sharing platform (the foundation)
   - Compose MP = UI framework built on KMP (shares UI code across platforms)
   - On Android: Compose MP uses Jetpack Compose under the hood
   - On iOS: Compose MP uses native rendering (Skia/Skiko)

2. **Jetpack Compose vs Compose Multiplatform**
   - Jetpack Compose = Android-only (by Google)
   - Compose MP = Cross-platform (by JetBrains), based on Jetpack Compose
   - ~95% API compatibility - most Jetpack Compose examples work in Compose MP

3. **Java/JVM Version Relationship**
   - IDE JDK: What IntelliJ uses to run Gradle and build tools
   - Gradle JVM Toolchain: What JVM version your code compiles to target
   - These can differ but best practice is to match them (using Java 21 for both)
   - Even iOS code needs JVM because the Kotlin compiler runs on JVM

4. **Why Templates Over Bare Projects**
   - Templates show "correct" project structure to learn from
   - Hardest part of KMP is build configuration, not code
   - Working example lets you reverse-engineer and understand conventions

## What We Built
- Repository: Cloned JetBrains Shared UI Multiplatform App template
- Environment: Set up IntelliJ with Kotlin Multiplatform plugin and Java 21
- Documentation: Created this CLAUDE.md learning journal

## Insights & Aha Moments
- **Agent indirection realization**: Discovered that using a separate learning-guide agent created unnecessary back-and-forth. Better to work directly for conversational learning (agents work better for discrete, delegatable tasks like code review).
- **Plugin vs Library**: Compose MP is a library (added via Gradle), not an IDE plugin. IDE support comes from the Kotlin plugin recognizing Compose APIs.
- **Java background advantage**: Coming from Java, Kotlin will feel familiar. KMP is like having a shared library that compiles to different targets (similar to how GWT compiled Java to JS, but more sophisticated).

## Challenges & Solutions
- **Challenge**: Understanding the relationship between Jetpack Compose and Compose Multiplatform
- **Solution**: Clarified that Compose MP extends Jetpack Compose to multiple platforms, maintaining ~95% API compatibility

- **Challenge**: Confusion about whether a separate Compose plugin is needed
- **Solution**: Understood that Compose support is built into the Kotlin plugin; Compose MP is just a library dependency

## Next Steps
- [x] Finish opening project in IntelliJ (in progress - Gradle sync)
- [ ] Explore project structure (folders: composeApp/, iosApp/, etc.)
- [ ] Understand source sets and how shared code works
- [ ] Run app on Android emulator
- [ ] Run app on iOS simulator
- [ ] Understand the build system (Gradle configuration)
- [ ] Deploy to physical iPhone (requires code signing setup)

## Questions/Blockers
- What is the Gradle JVM toolchain version in the template? (Check build.gradle.kts after project loads)
- Need to verify Xcode command line tools are installed for iOS builds
- Will need to set up Apple Developer account for physical device deployment
