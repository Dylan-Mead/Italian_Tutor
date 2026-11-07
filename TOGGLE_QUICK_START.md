# Toggle Switch - Quick Start Guide

## What's New?

A toggle switch in the web app header lets you switch between two teaching modes:

- **Free Mode** (OFF): Casual, conversational learning with Paolo
- **Structured Mode** (ON): Single-word focused learning like a classroom teacher

## How to Use

### Starting the Web App
```bash
python3 -m italian_tutor.webapp
```
Then open: `http://127.0.0.1:5000`

### Using the Toggle

1. **Look in the header** - You'll see a toggle switch labeled "Structured Mode"
2. **Click to toggle** - ON for structured, OFF for free
3. **See the confirmation** - Paulo messages confirm the mode switch + focus word
4. **Chat normally** - Everything works as before, just different teaching style

### In Structured Mode

Once in structured mode, you can:

- **Learn a word** - Paolo picks a word and teaches it
- **Move to next word** - Type `/next` or `/prossimo`
- **Ask questions** - Ask about how to use the word
- **Return to free mode** - Toggle OFF or type `/free`

## Example Workflow

```
1. Start web app
2. Click toggle ON
3. See: "Switched to Structured mode. Now teaching: **casa**"
4. Ask: "How do I use casa?"
5. Paulo explains definition, examples, grammatical contexts
6. You practice: "Io vado a casa"
7. Type "/next" to move to next word
8. See: "Now teaching: **amore**"
9. Toggle OFF to return to free mode
```

## What Changed Behind the Scenes

### Files Modified
- `templates/chat.html` - Added toggle HTML
- `static/style.css` - Added toggle styling
- `static/app.js` - Added toggle event handler
- `webapp.py` - Added `/api/mode` API endpoint

### New API Endpoint
- **POST** `/api/mode` - Switch teaching modes

### Enhanced Features
- Frequency-weighted word selection (common words more likely)
- Smart rotation (no word repeats in last 10)
- Thread-safe mode switching
- Seamless integration with existing chat

## Verification

To verify the toggle is working:

```bash
# 1. Start the app
python3 -m italian_tutor.webapp

# 2. In browser, open http://127.0.0.1:5000

# 3. Look in header - you should see the toggle switch

# 4. Click it and confirm messages appear
```

## Technical Details (If You're Curious)

### How Word Selection Works
1. Load `content/word_list.csv` (982 Italian words)
2. Each word has a frequency score
3. Generate random number weighted by frequency
4. Pick word - more common words more likely
5. Reject if picked in last 10 words (prevent repeats)
6. Return selected word

### System Prompt Switching
- **Free Mode**: Uses `default_system_prompt.json`
- **Structured Mode**: Uses `structured_system_prompt.json` + focus word
- Sistema prompts control Paolo's teaching style

### Thread Safety
- All mode switches protected by lock
- 60-second timeout prevents blocking
- Works safely with multiple users

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Toggle not visible | Clear browser cache, restart webapp |
| Mode switch fails | Wait 60s, restart webapp |
| Focus word not showing | Check `content/word_list.csv` exists |
| JavaScript errors | Check browser console for details |

## Next Steps

1. **Try it out** - Toggle between modes and see the difference
2. **Use in structured mode** - Pick a word and learn it thoroughly
3. **Combine modes** - Switch back and forth as needed
4. **Report feedback** - How's the word selection? Teaching quality?

## Command Reference

| Command | Effect |
|---------|--------|
| `/next` | Move to next word (structured mode) |
| `/prossimo` | Same as `/next` (Italian version) |
| `/free` | Switch to free mode (from structured) |
| `/structured` | Switch to structured mode (from free) |
| (toggle in UI) | Quickest way to switch modes |

---

**Enjoy learning with your new teaching modes!** 🇮🇹
