# Frontend Improvements Needed

## Features to Restore/Add

### 1. Environmental Context Panel
- The environmental context panel that used to be on the frontend is missing
- Need to restore this feature to show location, weather, time, etc.

### 2. Voice Configuration  
- 11 Labs voice configuration needs to be back on the main page
- Was previously available but is now missing

### 3. Chat Message Display
- Show assistant name and user name with each message
- Make the display more prominent than current implementation
- Names should be clearly visible in the chat dialogue

### 4. STT (Speech-to-Text) Feature
- Needs comprehensive testing
- Color/visual feedback during recording
- No clear button needed - keep interface minimal

### 5. Text Input Area
- Should start as single line
- Should expand automatically as user types more content
- Dynamic height adjustment based on content
- Standard behavior like most chat apps

## Testing Focus Areas

### STT Testing Requirements
- Test voice input functionality thoroughly
- Verify visual feedback during recording
- Test transcription accuracy
- Test browser permission handling
- Ensure works in both Chrome and Firefox

## Scope Notes

### Deferred to Fast Follow
- **SemanticGraphPerceptor** - Currently no configuration or update process
  - Needs entity extraction pipeline
  - Needs graph update mechanism
  - Will refine and include in next release

### Current Focus
- Self-summarization functionality
- Core chat experience
- Voice features (STT/TTS)
- Environmental context
- Notebook functionality