# Structured Mode - Quick Reference

## CLI Commands

### Start Application
```bash
# Free Mode (default, conversational)
python3 -m italian_tutor

# Structured Mode (single-word focus)
python3 -m italian_tutor --structured
```

## In-Session Commands

### Mode Switching
| Command | Mode | Effect |
|---------|------|--------|
| `/structured` | Free → Structured | Switch to structured mode with a focus word |
| `/free` | Structured → Free | Switch to casual, conversational mode |

### Word Progression (Structured Mode Only)
| Command | Effect |
|---------|--------|
| `/next` | Move to next focus word |
| `/prossimo` | Move to next focus word (Italian) |

### Session Management (Both Modes)
| Command | Effect |
|---------|--------|
| `/reset` or `/restart` | Save progress, clear session history, start fresh |
| `/exit` or `/quit` | Save progress and exit |

## Example Structured Session

```
$ python3 -m italian_tutor --structured

--- Welcome back! Loaded proficiency: Beginner (A1) ---
--- STRUCTURED MODE - Focus Word: casa ---
Paolo: Ciao! Siamo in modalità 'strutturata'. Ci focalizziamo su una parola alla volta.

Paolo: Perfetto! La parola di oggi è "casa" (house/home). È un sostantivo femminile.
Impariamo come usarla in diversi contesti...

You: [provide responses]

You: /next
--- New Focus Word: amore ---

You: /free
--- Switching to FREE mode ---

You: /exit
[Session saved and exited]
```

## Files & Structure

| File | Purpose |
|------|---------|
| `structured_system_prompt.json` | Instructions for Paolo in structured mode |
| `default_system_prompt.json` | Instructions for Paolo in free mode |
| `word_list.csv` | Database of 1000+ Italian words with frequency data |
| `STRUCTURED_MODE.md` | Complete documentation |

## Key Features

✨ **Structured Mode**:
- Focuses on ONE word per session phase
- Teaches word meaning, usage, tenses, grammar
- Prompts you to construct sentences
- Drills until competence shown
- Professional, classroom-like tone

✨ **Free Mode** (Default):
- Casual, conversational learning
- Natural dialogue flow
- Scaffolded lessons
- Empathetic tutor approach

## Word Selection

- Words are picked from a frequency-weighted list (most common words first)
- Recent 10 words are tracked to avoid repetition
- Each `/next` command picks a new word (ensuring variety)
- Words are from Italian movie/TV subtitles database

## Tips

1. **For beginners**: Start in Free Mode to get comfortable
2. **For focused learning**: Use Structured Mode to deeply master vocabulary
3. **Mix approaches**: Switch between modes during a session
4. **Track progress**: Your vocabulary and proficiency level are saved automatically
5. **Italian commands**: Use `/prossimo` instead of `/next` to practice!

## Troubleshooting

**"word_list.csv not found"**
- Make sure the file is in `content/` folder
- Run scraper if needed: `python3 content/scrape_italian_words.py`

**"pandas not installed"**
- Install: `pip install pandas`

**Mode switch not working**
- Use exact command: `/structured` or `/free`
- Check spelling and leading slash

**Can't move to next word**
- You must be in Structured Mode
- Use `/next` or `/prossimo` (case-insensitive)

## More Information

See `STRUCTURED_MODE.md` for complete documentation including:
- Detailed feature descriptions
- Teaching methodology
- Integration guide for web app
- Architecture and design details
