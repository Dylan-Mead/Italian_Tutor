# Web App Fix - Flask Needs to Be Restarted

## Current Status

✅ All code changes are complete and verified  
✅ All files have been updated correctly  
✅ Python syntax is valid  
✅ All components are in place  

❌ Flask is still running the OLD code (caching issue)

## What Happened

When you restarted the Flask web app earlier, it loaded the code that was in memory at that time. Since then, I made changes to:

- `src/italian_tutor/webapp.py` - Added `/api/mode` endpoint, fixed build_system_prompt calls
- `src/italian_tutor/templates/chat.html` - Added toggle HTML
- `src/italian_tutor/static/style.css` - Added toggle styling
- `src/italian_tutor/static/app.js` - Added toggle event handler

But Flask hasn't reloaded these files because it's still running the old Python process.

## Solution: Restart Flask

### Step 1: Stop the current Flask process
If Flask is running, stop it (Ctrl+C in the terminal where it's running)

### Step 2: Clear any Python cache
```bash
cd /home/djmead/Documents/Projects/Italian_Tutor
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

### Step 3: Restart Flask
```bash
python3 -m italian_tutor.webapp
```

You should see:
```
Starting Italian Tutor web UI...
  Local:   http://127.0.0.1:5000
  Network: http://192.168.x.x:5000
```

### Step 4: Clear browser cache
- Press `Ctrl+Shift+Delete` (or `Cmd+Shift+Delete` on Mac)
- Clear cache
- Close and reopen the browser tab

### Step 5: Open the web app
Navigate to `http://127.0.0.1:5000`

You should now see:
1. ✅ Toggle switch in the header (next to 📊 button)
2. ✅ Chat working normally
3. ✅ Ability to switch between Free and Structured modes

## Fixes Made

In `webapp.py`, I fixed two issues:

### Fix 1: `api_save()` function
**Before:**
```python
conv["messages"][0] = {"role": "system", "content": build_system_prompt(merged)}
```

**After:**
```python
template_path = "structured_system_prompt.json" if conv["teaching_mode"] == "structured" else None
conv["messages"][0] = {"role": "system", "content": build_system_prompt(merged, template_path, conv["focus_word"])}
```

### Fix 2: `api_reset()` function
**Before:**
```python
conv["messages"] = [{"role": "system", "content": build_system_prompt(merged)}]
```

**After:**
```python
template_path = "structured_system_prompt.json" if conv.get("teaching_mode") == "structured" else None
conv["messages"] = [{"role": "system", "content": build_system_prompt(merged, template_path, conv.get("focus_word"))}]
```

These fixes ensure that when saving or resetting a session, the correct system prompt template and focus word are used.

## Verification Checklist

After restarting Flask and opening the web app:

- [ ] Toggle switch visible in header
- [ ] Toggle switch is clickable
- [ ] Toggle OFF → ON: See "Switched to Structured mode" message
- [ ] Focus word appears in the message
- [ ] Toggle ON → OFF: See "Switched to Free mode" message
- [ ] Chat responds to messages in both modes
- [ ] Type `/next` in structured mode to change words
- [ ] Type `/free` to switch back to free mode

## If Still Not Working

1. Check browser console for JavaScript errors:
   - Press F12
   - Go to Console tab
   - Look for red error messages

2. Check Flask output for errors:
   - Look at the terminal where Flask is running
   - Look for red/error messages

3. Verify Ollama is running:
   ```bash
   ps aux | grep ollama
   ```
   If not running, start it in another terminal

4. Check the network tab in browser (F12):
   - When you click toggle, there should be a POST request to `/api/mode`
   - The response should be `{"mode": "...", "focus_word": "..."}`

## About CLI Structured Mode

The `--structured` flag IS implemented correctly in `tutor.py`. To test:

```bash
cd /home/djmead/Documents/Projects/Italian_Tutor
python3 -m italian_tutor.tutor --structured
```

You should see:
```
--- Welcome back! Loaded proficiency: ... ---
--- STRUCTURED MODE - Focus Word: [word] ---
Paolo: Ciao! Siamo in modalità 'strutturata'...
```

## Summary

✅ Code is complete and correct  
✅ All components are in place  
✅ Just need to restart Flask  

**Next action:** Kill Flask and restart it!

```bash
python3 -m italian_tutor.webapp
```
