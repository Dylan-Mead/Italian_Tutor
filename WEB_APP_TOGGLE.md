# Web App Toggle Switch Implementation

## Overview
The structured mode toggle switch has been fully implemented in the web app. Users can now switch between "Free Mode" (casual learning) and "Structured Mode" (single-word focused learning) using a visual toggle switch in the header.

## Changes Made

### 1. Frontend - HTML (`src/italian_tutor/templates/chat.html`)
- Added toggle switch component in the header alongside the progress panel button
- Structure:
  ```html
  <div class="mode-toggle-container">
    <label class="mode-toggle">
      <input type="checkbox" id="structuredModeToggle">
      <span class="toggle-label">Structured Mode</span>
    </label>
  </div>
  ```

### 2. Frontend - CSS (`src/italian_tutor/static/style.css`)
- Added `.header-controls` flex container for header elements
- Styled toggle switch with:
  - Animated sliding indicator
  - Color change on checked state (uses CSS variables)
  - Smooth transitions
  - Checkbox hidden, showing only styled toggle
  - Responsive sizing

### 3. Frontend - JavaScript (`src/italian_tutor/static/app.js`)
- Added `structuredModeToggle` element reference
- Updated `setBusy()` to disable/enable the toggle during chat operations
- Implemented `change` event listener that:
  - Makes POST request to `/api/mode` endpoint
  - Handles success: displays mode switch confirmation with focus word
  - Handles failure: reverts toggle and shows error warning
  - Maintains UI responsiveness with busy state management

### 4. Backend - Flask Routes (`src/italian_tutor/webapp.py`)

#### New Endpoint: `/api/mode` (POST)
```python
@app.route("/api/mode", methods=["POST"])
def api_set_mode():
```

Functionality:
- Accepts JSON payload: `{"mode": "structured"}` or `{"mode": "free"}`
- Validates mode value
- Loads word list (if needed for structured mode)
- Picks new focus word using `pick_next_word()` with frequency weighting
- Updates recent_words shift register to prevent repetition
- Rebuilds system prompt with appropriate template:
  - **Free Mode**: `default_system_prompt.json` template
  - **Structured Mode**: `structured_system_prompt.json` template + focus_word
- Thread-safe with `TUTOR_LOCK` to prevent race conditions
- Returns: `{"mode": "...", "focus_word": "..." || null}`

#### Updated Conversation State
Enhanced `_new_conversation()` to include:
- `teaching_mode`: Current mode ("free" or "structured")
- `recent_words`: List tracking last 10 words (for rotation)
- `word_list`: Loaded word frequency data
- `focus_word`: Current focus word in structured mode

#### Updated `/api/chat` Endpoint
Added optional support for `/structured` and `/free` text commands (backward compatible with CLI usage):
- Allows users to switch modes via chat message
- Falls through to normal message handling otherwise

### 5. Integrated Functions (already implemented in `tutor.py`)
- `load_word_list()`: Loads CSV with frequency data
- `pick_next_word()`: Selects word with frequency weighting, avoids last 10
- `update_recent_words()`: Maintains FIFO shift register
- `build_system_prompt()`: Now accepts `template_path` and `focus_word` parameters

## User Experience Flow

1. **User opens web app** → Starts in Free Mode
2. **User toggles switch ON** → Structured Mode activates:
   - Backend loads word list and picks random word (weighted by frequency)
   - System prompt switches to teaching format
   - Focus word is highlighted in assistant message
   - User begins single-word lesson
3. **User toggles switch OFF** → Returns to Free Mode:
   - System prompt switches back to casual format
   - Focus word cleared
   - Free-form conversation resumes

## Mode Behavior

### Free Mode
- Uses `default_system_prompt.json` template
- Paolo acts as casual tutor
- Scaffolded, conversational learning
- No specific word focus
- Can discuss multiple topics

### Structured Mode
- Uses `structured_system_prompt.json` template
- Paolo acts as classroom teacher
- Focuses on single word at a time
- Teaches:
  - Word definition and usage
  - Grammatical contexts and tenses
  - Example sentences
  - Drills user on proper usage
- Commands available:
  - `/next` or `/prossimo` → Move to next word
  - `/free` → Switch back to free mode
- Smart word rotation:
  - No word repeats within last 10 selections
  - Frequency weighting (more common words more likely)

## Technical Details

### Thread Safety
- All mode switching operations protected by `TUTOR_LOCK`
- Timeout set to 60 seconds to prevent blocking
- Returns 503 if lock not acquired (Paolo busy)

### Error Handling
- Invalid mode values rejected with 400 status
- Lock acquisition failures return 503 (service busy)
- Toggle automatically reverted on API errors
- User sees warning message for any failures

### Performance
- Word list loaded once per conversation (cached in conversation state)
- No database round-trips, all in-memory
- System prompt rebuilt but messages history preserved
- Frequency weighting algorithm O(n) but runs infrequently

## Files Modified
1. `src/italian_tutor/templates/chat.html` - Added toggle HTML
2. `src/italian_tutor/static/style.css` - Added toggle styling
3. `src/italian_tutor/static/app.js` - Added toggle event handler
4. `src/italian_tutor/webapp.py` - Added `/api/mode` endpoint, updated conversation state

## Testing Checklist
- [ ] Start web app (port 5000)
- [ ] Open chat interface
- [ ] Verify toggle switch visible in header
- [ ] Toggle OFF → ON (should show "Structured Mode" message with focus word)
- [ ] Toggle ON → OFF (should show "Free Mode" message)
- [ ] Test mode switching during active conversation (message flow continues)
- [ ] Test rapid toggling (should not break or duplicate words)
- [ ] Test /next command in structured mode
- [ ] Test /free command to switch back programmatically
- [ ] Test with multiple browser sessions (should maintain separate modes)

## Browser Compatibility
- Works with all modern browsers (Chrome, Firefox, Safari, Edge)
- CSS uses standard flexbox and transitions
- JavaScript uses async/await (ES2017+)
- No external dependencies beyond Flask + Ollama

## Future Enhancements
- Persist mode preference across sessions (store in cookie or user_mem)
- Add mode indicator badge in header
- Animate mode switch in message area
- Add keyboard shortcut for mode toggle (e.g., Ctrl+M)
- Save statistics per mode (words learned in structured vs free)
