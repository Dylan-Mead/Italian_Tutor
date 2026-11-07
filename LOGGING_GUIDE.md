# Logging Guide - Debug the Web App

I've added comprehensive logging to `webapp.py` to help track exactly where requests get stuck.

## How to See the Logs

When you run the Flask app, all logging output will appear in the **terminal**:

```bash
python3 -m italian_tutor.webapp
```

You'll see output like:

```
Starting Italian Tutor web UI...
  Local:   http://127.0.0.1:5000
  Network: http://192.168.x.x:5000
2026-11-07 11:43:47,123 - italian_tutor.webapp - INFO - ========================
2026-11-07 11:43:47,124 - italian_tutor.webapp - INFO - STARTING ITALIAN TUTOR WEB UI
2026-11-07 11:43:47,125 - italian_tutor.webapp - INFO - ========================
```

## What to Look For

### When You Load the Page
You should see:
```
INFO - Index route accessed
INFO - Conversation created/retrieved: 1 messages
```

### When You Send a Message
You should see:
```
INFO - === /api/chat endpoint called ===
INFO - User input received: 'ciao'
INFO - Attempting to acquire TUTOR_LOCK...
INFO - TUTOR_LOCK acquired
INFO - Checking if input is safe...
INFO - Safety check result: is_safe=True, verdict=None
INFO - Regular message, appending to conversation history
INFO - Message count in conversation: 2
INFO - === Starting generate() ===
INFO - Preparing to call Ollama with model: neural-chat
INFO - Message count before Ollama call: 2
INFO - Calling ollama.chat()...
```

### If It Hangs Here
If you see:
```
INFO - Calling ollama.chat()...
```
...but nothing after that, then **Ollama is not responding** or **not running**.

Check if Ollama is running:
```bash
ps aux | grep ollama | grep -v grep
```

If it's not running, you need to start it in another terminal.

### If It Works
You should eventually see:
```
INFO - ollama.chat() returned successfully, streaming response...
INFO - Chunk 1: 45 chars received
INFO - Chunk 2: 32 chars received
...
INFO - Streaming complete: 15 chunks, total: 452 chars
INFO - Appending assistant response (452 chars) to conversation
INFO - Releasing TUTOR_LOCK
INFO - === generate() complete ===
```

## What Each Log Message Means

| Log Message | What It Means |
|-------------|---------------|
| `/api/chat endpoint called` | Request reached the Flask endpoint |
| `User input received: 'xyz'` | Message was successfully parsed |
| `Attempting to acquire TUTOR_LOCK` | Waiting for lock to be available |
| `TUTOR_LOCK acquired` | Lock acquired, processing can continue |
| `Checking if input is safe` | Checking if input passes safety filter |
| `Safety check result: is_safe=True` | Safety check passed |
| `Calling ollama.chat()` | About to call the LLM |
| `ollama.chat() returned successfully` | LLM responded, now streaming |
| `Chunk N: X chars received` | Receiving response data |
| `Streaming complete: N chunks, total: X chars` | LLM response finished |
| `Appending assistant response` | Saving response to conversation |
| `Releasing TUTOR_LOCK` | Releasing lock for next request |

## Common Issues and Diagnostics

### Issue: "Calling ollama.chat()..." then hangs
**Diagnosis:** Ollama is either:
1. Not running
2. Not responding
3. The model isn't loaded

**Check:**
```bash
ps aux | grep ollama
```

**Solution:** Start Ollama in another terminal

### Issue: Safety check never completes
**Diagnosis:** The `is_input_safe()` function is hanging

**Log to look for:**
```
INFO - Checking if input is safe...
(nothing after this)
```

**Solution:** This suggests an issue with the safety check function

### Issue: Response never comes back
**Diagnosis:** Ollama is running but not responding or very slow

**Log to look for:**
```
INFO - Calling ollama.chat()...
(hangs here for a long time, then timeout)
```

**Solution:** 
- Check Ollama is running: `ps aux | grep ollama`
- Restart Ollama: `killall ollama` then restart

### Issue: Lock timeout
**Log to look for:**
```
ERROR - Failed to acquire TUTOR_LOCK within timeout
```

**Diagnosis:** Previous request is still processing after 60 seconds

**Solution:** One of the earlier steps is hanging

## Steps to Debug

1. **Start Flask with logging:**
   ```bash
   python3 -m italian_tutor.webapp
   ```

2. **Open the web app:**
   ```
   http://127.0.0.1:5000
   ```

3. **Send a simple message like "ciao"**

4. **Watch the logs in the terminal**

5. **Look for where it stops:**
   - Stops at `User input received`? → Input parsing problem
   - Stops at `Checking if input is safe`? → Safety check problem
   - Stops at `Calling ollama.chat()`? → Ollama not running/responding
   - Stops after `Chunk N`? → Streaming stopped unexpectedly

6. **Share with me:**
   - The exact log messages you see
   - Where it stops
   - How long you waited after the last message

## Example: Full Successful Flow

```
2026-11-07 11:47:19,456 - italian_tutor.webapp - INFO - === /api/chat endpoint called ===
2026-11-07 11:47:19,457 - italian_tutor.webapp - INFO - User input received: 'ciao'
2026-11-07 11:47:19,458 - italian_tutor.webapp - INFO - Attempting to acquire TUTOR_LOCK...
2026-11-07 11:47:19,459 - italian_tutor.webapp - INFO - TUTOR_LOCK acquired
2026-11-07 11:47:19,460 - italian_tutor.webapp - INFO - Checking if input is safe...
2026-11-07 11:47:19,465 - italian_tutor.webapp - INFO - Safety check result: is_safe=True, verdict=None
2026-11-07 11:47:19,466 - italian_tutor.webapp - INFO - Regular message, appending to conversation history
2026-11-07 11:47:19,467 - italian_tutor.webapp - INFO - Message count in conversation: 2
2026-11-07 11:47:19,468 - italian_tutor.webapp - INFO - Returning Response stream
2026-11-07 11:47:19,469 - italian_tutor.webapp - INFO - === Starting generate() ===
2026-11-07 11:47:19,470 - italian_tutor.webapp - INFO - Preparing to call Ollama with model: neural-chat
2026-11-07 11:47:19,471 - italian_tutor.webapp - INFO - Message count before Ollama call: 2
2026-11-07 11:47:19,472 - italian_tutor.webapp - INFO - Calling ollama.chat()...
2026-11-07 11:47:22,534 - italian_tutor.webapp - INFO - ollama.chat() returned successfully, streaming response...
2026-11-07 11:47:22,535 - italian_tutor.webapp - DEBUG - Chunk 1: 45 chars received
2026-11-07 11:47:22,545 - italian_tutor.webapp - DEBUG - Chunk 2: 38 chars received
2026-11-07 11:47:22,556 - italian_tutor.webapp - DEBUG - Chunk 3: 52 chars received
2026-11-07 11:47:22,575 - italian_tutor.webapp - INFO - Streaming complete: 3 chunks, total: 135 chars
2026-11-07 11:47:22,576 - italian_tutor.webapp - INFO - Appending assistant response (135 chars) to conversation
2026-11-07 11:47:22,577 - italian_tutor.webapp - INFO - Releasing TUTOR_LOCK
2026-11-07 11:47:22,578 - italian_tutor.webapp - INFO - === generate() complete ===
```

This shows a successful request from start to finish!

## Next Steps

1. Restart the web app with the new logging
2. Try sending a message
3. Watch where it stops in the logs
4. Share the logs with me and we'll figure out the exact issue
