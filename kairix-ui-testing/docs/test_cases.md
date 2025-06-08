# Kairix Memory Pipeline UI Test Cases (UI-Only Focus)

## Overview
These test cases focus exclusively on UI behavior, interactions, and visual feedback. No backend logic or business rules are tested.

## 1. Import Tab UI Tests

### Test Case 1.1: `test_import_streaming_display`
**Purpose**: Verify text streams into output box character by character
**Steps**:
1. Select a file in FileExplorer
2. Click "Start" button
3. Observe output textbox
**Verify**:
- Text appears progressively (not all at once)
- Output box shows each new line as it arrives
- Scrollbar appears when content exceeds visible area
- Latest content is visible (auto-scroll behavior)

### Test Case 1.2: `test_import_button_state_during_operation`
**Purpose**: Verify button disabled during operation
**Steps**:
1. Select file and click "Start"
2. Try clicking "Start" again immediately
**Verify**:
- Button becomes disabled/unclickable during operation
- Button re-enables after operation completes
- No duplicate operations triggered

### Test Case 1.3: `test_import_file_explorer_interaction`
**Purpose**: Test file selection UI component
**Steps**:
1. Click on FileExplorer
2. Navigate folders
3. Select different files
**Verify**:
- Can navigate directory tree
- File selection highlights selected file
- Selected file path updates in component
- Can deselect and reselect files

### Test Case 1.4: `test_import_output_persistence`
**Purpose**: Verify output remains visible after operation
**Steps**:
1. Run an import operation
2. Wait for completion
3. Interact with other UI elements
**Verify**:
- Output text remains in textbox
- Can select and copy text from output
- Output doesn't clear when clicking elsewhere

### Test Case 1.5: `test_import_long_output_scrolling`
**Purpose**: Test output box with extensive content
**Mock Config**: Set high conversation count for lots of output
**Steps**:
1. Run import that generates many lines
2. Try scrolling during operation
**Verify**:
- Can manually scroll up while content streams
- New content doesn't force scroll position if user scrolled up
- Can scroll to top/bottom smoothly
- Scrollbar size reflects content amount

## 2. Synthesis Tab UI Tests

### Test Case 2.1: `test_synthesis_input_fields`
**Purpose**: Test text input interactions
**Steps**:
1. Click on Agent Name field
2. Type text
3. Tab to Run ID field
4. Type text
**Verify**:
- Fields accept text input
- Can tab between fields
- Can clear and re-enter text
- Placeholder text visible when empty

### Test Case 2.2: `test_synthesis_output_appears_at_once`
**Purpose**: Verify batch output behavior (not streaming)
**Steps**:
1. Fill in agent name and run ID
2. Click "Start"
3. Observe output textbox
**Verify**:
- Output area stays empty during processing
- All text appears simultaneously when complete
- No progressive/streaming display

### Test Case 2.3: `test_synthesis_button_with_empty_fields`
**Purpose**: Test button behavior with empty inputs
**Steps**:
1. Leave one or both fields empty
2. Click "Start" button
**Verify**:
- Button remains clickable
- Operation executes (even with empty fields)
- Output shows some response

### Test Case 2.4: `test_synthesis_field_values_during_operation`
**Purpose**: Verify input fields during processing
**Steps**:
1. Enter values and start operation
2. Try to edit fields during processing
**Verify**:
- Fields remain editable during operation
- Values don't get cleared
- Can type but changes don't affect running operation

### Test Case 2.5: `test_synthesis_output_formatting`
**Purpose**: Test text display formatting
**Steps**:
1. Run synthesis operation
2. Examine output formatting
**Verify**:
- Line breaks display correctly
- Special characters (✅, ❌) render properly
- Indentation/spacing preserved
- Monospace font used for output

## 3. Cross-Tab UI Behavior Tests

### Test Case 3.1: `test_tab_switching`
**Purpose**: Test tab navigation
**Steps**:
1. Click between Import and Synthesis tabs repeatedly
2. Perform operations in each tab
**Verify**:
- Tab switches immediately
- Content in each tab persists
- No visual glitches during switch
- Active tab clearly indicated

### Test Case 3.2: `test_simultaneous_operations_ui`
**Purpose**: Test UI during concurrent operations
**Steps**:
1. Start import operation
2. Switch to synthesis tab
3. Try to start synthesis
**Verify**:
- Both operations can be triggered
- Tab switching works during operations
- Each tab's output updates independently

### Test Case 3.3: `test_window_resize_behavior`
**Purpose**: Test responsive layout
**Steps**:
1. Resize browser window
2. Make window very narrow/wide
**Verify**:
- Layout adjusts appropriately
- Text boxes remain usable
- No content gets cut off
- Scrollbars appear as needed

### Test Case 3.4: `test_theme_rendering`
**Purpose**: Verify theme displays correctly
**Steps**:
1. Load the UI
2. Check visual styling
**Verify**:
- "calm_seafoam" theme colors applied
- Consistent styling across components
- Good contrast for readability
- Button hover states work

### Test Case 3.5: `test_page_refresh_ui_state`
**Purpose**: Test UI after browser refresh
**Steps**:
1. Run some operations
2. Refresh the page (F5)
**Verify**:
- UI returns to initial state
- FileExplorer shows default value
- All text fields empty
- Output areas cleared

## UI Element Verification Checklist

### Import Tab
- [ ] FileExplorer displays with root directory
- [ ] Default file "test-convos.json" selected
- [ ] "Start" button is blue/primary styled
- [ ] Output box has placeholder text
- [ ] Output box has 20 lines height

### Synthesis Tab  
- [ ] Two text input fields present
- [ ] Labels show "Agent Name" and "Run ID"
- [ ] "Start" button is blue/primary styled
- [ ] Output box matches import tab styling

### General UI
- [ ] Title shows "Kairix Memory Architecture Pipeline"
- [ ] Tab labels are "Import ChatGPT Export" and "Summarize Memories"
- [ ] Theme colors applied consistently
- [ ] No JavaScript console errors