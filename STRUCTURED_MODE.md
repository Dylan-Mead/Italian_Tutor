# Structured Learning Mode

## Overview

The Italian Tutor now supports a **Structured Mode** that focuses on teaching one word at a time. This mode provides a more methodical, classroom-like approach to vocabulary learning, as opposed to the free-flowing conversational style of the default "Free Mode."

## Features

- **Single-word focus**: Paolo concentrates exclusively on teaching one Italian word per session
- **Comprehensive word breakdown**: Includes meanings, usage in different tenses, and grammatical contexts
- **Interactive drilling**: Users are prompted to construct sentences using the focus word
- **Proficiency-based word selection**: Words are picked using frequency weighting from the Italian word frequency list
- **Smart word rotation**: Tracks the last 10 words picked to avoid repeating recent words
- **Mode switching**: Seamlessly switch between Structured and Free modes during a session

## Getting Started

### Command Line

**Start in Structured Mode:**
```bash
python3 -m italian_tutor --structured
```

**Start in Free Mode (default):**
```bash
python3 -m italian_tutor
```

### During a Session

**Switch from Free to Structured Mode:**
```
You: /structured
```

**Switch from Structured to Free Mode:**
```
You: /free
```

**Move to the next focus word (Structured mode only):**
```
You: /next
# or
You: /prossimo
```

**Exit the session:**
```
You: /exit
# or
You: /quit
```

**Reset session:**
```
You: /reset
# or
You: /restart
```

## How Structured Mode Works

### 1. Word Selection
- A word is randomly selected from the Italian frequency list
- Selection is weighted by word frequency (more common words are more likely)
- The last 10 words picked in the session are tracked and avoided in new selections

### 2. Word Teaching
Paolo will:
1. Explain the word's meaning and primary usage
2. Show how the word changes in different tenses (for verbs) or forms (for nouns/adjectives)
3. Provide 3-5 contextual examples
4. Prompt you to write sentences using the word
5. Provide corrective feedback on your sentences
6. Continue drilling with varied prompts until you demonstrate competence

### 3. Progression
- You can request `/next` or `/prossimo` when ready to move to a new word
- Paolo guides you on when you're ready based on your demonstrated understanding
- Your progress is automatically saved

## System Prompts

### Default System Prompt (Free Mode)
- **File**: `default_system_prompt.json`
- **Style**: Empathetic, casual tutor
- **Focus**: Scaffolded learning with conversational flow
- **Character**: Paolo as a friendly tutor

### Structured System Prompt (Structured Mode)
- **File**: `structured_system_prompt.json`
- **Style**: Professional, classroom-like instruction
- **Focus**: Single-word mastery with rigorous drilling
- **Character**: Paolo as a high school language teacher

## File Structure

```
src/italian_tutor/
├── tutor.py                           # Main application with structured mode
├── default_system_prompt.json         # Free mode system prompt
├── structured_system_prompt.json      # Structured mode system prompt
└── ...

content/
├── word_list.csv                      # 1000 most common Italian words (with frequency data)
├── italian_words_frequency.csv        # Backup frequency list
├── scrape_italian_words.py            # Script to update word lists
├── pick_word.ipynb                    # Jupyter notebook with pick_word function
└── README.md                          # Content folder documentation
```

## Key Functions Added

### Word Selection Functions

```python
load_word_list(word_list_path=None)
    # Load the word frequency list from CSV

pick_word(word_list, excluded_words=None)
    # Pick a random word using frequency weighting

pick_next_word(word_list, recent_words)
    # Pick a new word, ensuring it's not in recent words

update_recent_words(recent_words, new_word, max_length=10)
    # Maintain a shift register of recently picked words
```

### Mode Control Functions

```python
main_structured()
    # Run the tutor in structured mode

main()
    # Run the tutor in free mode (default) with mode switching support
```

## Teaching Rules for Structured Mode

Structured mode activates the following teaching rules in the system prompt:

1. Focus exclusively on the designated focus word
2. Define the word clearly with translation and part of speech
3. Explain usage across different tenses and grammatical contexts
4. Provide multiple contextual examples
5. Prompt the user to construct sentences
6. Give supportive, corrective feedback
7. Continue drilling with varied prompts
8. Only move forward when competence is demonstrated
9. Keep responses concise and focused
10. Maintain a professional, classroom-like tone

## Example Structured Session

```
--- STRUCTURED MODE - Focus Word: gatto ---

Paolo: Ciao! Siamo in modalità 'strutturata'. Ci focalizziamo su una parola alla volta.

Paolo: Perfetto! Iniziamo con la parola: **gatto** (cat)

È un sostantivo maschile che significa "cat". In italiano, il plurale è "gatti".

Esempi di utilizzo:
1. "Mio gatto è nero." (My cat is black.)
2. "I gatti sono animali domestici." (Cats are domestic animals.)
3. "Il gatto dorme sul divano." (The cat sleeps on the sofa.)

Ora, prova a scrivere una frase usando la parola "gatto". Puoi descrivere un gatto che conosci!

You: Il mio gatto si chiama Fluffy e ama dormire.

Paolo: Ottimo! La tua frase è corretta. Bene, hai usato l'articolo possessivo e il verbo "si chiama" 
perfettamente. 

Ora prova a usare "gatto" in una frase al passato. Ad esempio, descrivere cosa faceva il gatto ieri.

You: Ieri il gatto ha mangiato molto.

Paolo: Perfetto! Hai usato il passato prossimo correttamente. Molto bene!

Adesso prova con una domanda: "Dov'è il gatto?" Modificala per fare una domanda personale sul tuo gatto.

You: Dove ha dormito il mio gatto questa notte?

Paolo: Eccellente! Hai costruito una domanda al passato prossimo con "il mio gatto" molto bene. 
Penso che sei pronto a passare alla prossima parola!

Se sei d'accordo, digita /next o /prossimo per continuare!

You: /next

--- New Focus Word: amore ---
```

## Integration with Web App

For the web app (webapp.py), you can add a toggle switch:

```html
<!-- Toggle between Structured and Free modes -->
<div class="mode-toggle">
  <label>
    <input type="checkbox" id="structuredModeToggle">
    Structured Mode
  </label>
</div>
```

JavaScript to handle mode switching:
```javascript
document.getElementById('structuredModeToggle').addEventListener('change', function() {
    const mode = this.checked ? 'structured' : 'free';
    // Send mode preference to backend
    fetch('/api/set-mode', {
        method: 'POST',
        body: JSON.stringify({mode: mode})
    });
});
```

## Dependencies

- **pandas**: For loading and filtering the word list
- **ollama**: For model inference (already required)
- **requests**, **beautifulsoup4**: For scraping word lists (already in content folder)

Install pandas if not already available:
```bash
pip install pandas
```

## Troubleshooting

**"word_list.csv not found"**
- The word_list.csv file must be in the `content/` folder
- Run `python3 content/scrape_italian_words.py` to generate it from italian_words_frequency.csv

**"structured_system_prompt.json not found"**
- The file should be in `src/italian_tutor/`
- If missing, structured mode will output a warning but still attempt to function

**"ModuleNotFoundError: No module named 'pandas'"**
- Install pandas: `pip install pandas`

**Words repeating too often**
- The shift register is limited to 10 words
- If more words are in the list, restart the session or the 11th unique word will cycle out oldest picks

## Future Enhancements

- [ ] Web UI with toggle switch for mode selection
- [ ] Progress tracking for words learned in structured mode
- [ ] Custom word lists per proficiency level
- [ ] Statistics on words mastered vs. struggling
- [ ] Spaced repetition system for structured mode
- [ ] Export vocabulary lists from structured sessions
- [ ] Audio pronunciation guides for focused words

## See Also

- `default_system_prompt.json` - Free mode system prompt
- `content/word_list.csv` - The word frequency database
- `content/scrape_italian_words.py` - Script to update word lists
- `content/example_usage.py` - Examples of using the word list
