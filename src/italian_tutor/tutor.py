import csv
import io
import json
import re
import sys
import random
from importlib import resources
from pathlib import Path
import readline  # noqa: F401 - enables GNU readline line editing (arrow keys, history) for input()
import ollama
import pandas as pd

# tutor_memory.json is mutable, per-user state, so it's anchored to the project
# root (parent of src/italian_tutor/) rather than bundled as package data -
# that keeps it writable and stable no matter where this script is launched
# from, while staying independent of any editor/package install state.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_FILE = PROJECT_ROOT / "tutor_memory.json"

MODEL_NAME = "qwen3:8b"  # Your 8GB optimized model
FIREWALL_MODEL_NAME = "prompt-firewall"  # Classifies input as SAFE or INJECTION
CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

def load_memory():
    if MEMORY_FILE.exists():
        with MEMORY_FILE.open('r') as f:
            return json.load(f)
    return {"proficiency_level": "Beginner (A1)", "learned_vocabulary": [], "struggled_vocabulary": [], "grammar_concepts_mastered": [], "session_notes": "Fresh start."}

def load_cefr_descriptions():
    """Load the CEFR level descriptions used to ground the model's end-of-session
    proficiency assessment. CEFR_Levels.csv is bundled as package data (loaded via
    importlib.resources) so it's found correctly whether running from an editable
    checkout or an installed wheel. Returns an empty string if it's missing."""
    try:
        csv_text = resources.files("italian_tutor").joinpath("CEFR_Levels.csv").read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    reader = csv.DictReader(io.StringIO(csv_text))
    return "\n".join(f"{row['Level']}: {row['Description']}" for row in reader)

def extract_cefr_code(level_text):
    """Pull a bare CEFR code (A1-C2) out of a level string, e.g. 'Beginner (A1)' -> 'A1'.
    Returns None if no recognizable code is found."""
    if not level_text:
        return None
    match = re.search(r'\b(A1|A2|B1|B2|C1|C2)\b', level_text.upper())
    return match.group(1) if match else None

def higher_cefr_level(old_level, new_level):
    """Return whichever of old_level/new_level is the higher CEFR level, so a
    short/simple session can never knock the user's recorded level down."""
    old_code = extract_cefr_code(old_level)
    new_code = extract_cefr_code(new_level)
    if new_code is None:
        return old_level
    if old_code is None or CEFR_ORDER.index(new_code) >= CEFR_ORDER.index(old_code):
        return new_level
    return old_level


def load_word_list(word_list_path=None):
    """Load the word frequency list for structured mode.
    
    Args:
        word_list_path: Path to word_list.csv. If None, tries to load from content folder.
    
    Returns:
        pd.DataFrame: Word list with columns [rank, word, frequency, cumulative frequency]
    """
    if word_list_path is None:
        # Try to load from content folder
        content_path = PROJECT_ROOT / "content" / "word_list.csv"
        if content_path.exists():
            word_list_path = content_path
        else:
            raise FileNotFoundError("word_list.csv not found in content folder")
    
    return pd.read_csv(word_list_path)


def pick_word(word_list, excluded_words=None):
    """Pick a random word from the word list using cumulative frequency weighting.
    
    More common words are more likely to be picked.
    
    Args:
        word_list (pd.DataFrame): Word list with cumulative frequency column
        excluded_words (list): Words to exclude from selection (e.g., recently picked words)
    
    Returns:
        str: A word from the list
    """
    if excluded_words is None:
        excluded_words = []
    
    # Filter out excluded words
    available = word_list[~word_list['word'].isin(excluded_words)]
    
    if len(available) == 0:
        # If all words are excluded, just pick from the full list
        available = word_list
    
    total = available['cumulative frequency'].iloc[-1]
    r = random.randint(1, int(total))
    picked = available[available['cumulative frequency'] >= r].iloc[0]['word']
    
    return picked


def pick_next_word(word_list, recent_words):
    """Pick a new word, ensuring it's not in the recent_words shift register.
    
    Args:
        word_list (pd.DataFrame): Word list
        recent_words (list): List of recently picked words (max 10)
    
    Returns:
        str: The new word
    """
    attempts = 0
    max_attempts = 50
    
    while attempts < max_attempts:
        word = pick_word(word_list, recent_words)
        if word not in recent_words:
            return word
        attempts += 1
    
    # Fallback: just return the picked word even if in recent
    return word


def update_recent_words(recent_words, new_word, max_length=10):
    """Add a word to the shift register, removing oldest if needed.
    
    Args:
        recent_words (list): Current list of recent words
        new_word (str): Word to add
        max_length (int): Maximum length of the list
    
    Returns:
        list: Updated list with new word added (oldest removed if at max length)
    """
    recent_words.append(new_word)
    if len(recent_words) > max_length:
        recent_words.pop(0)
    return recent_words


def save_memory(memory):
    with MEMORY_FILE.open('w') as f:
        json.dump(memory, f, indent=2)


def merge_memory(old_mem, new_mem):
    """Combine this session's results with previously saved memory instead of
    overwriting it, so vocabulary/concepts accumulate across sessions."""
    merged = dict(old_mem)
    # Never let a short/simple session knock the recorded level down - keep the higher of the two.
    merged['proficiency_level'] = higher_cefr_level(
        old_mem.get('proficiency_level'), new_mem.get('proficiency_level')
    )

    for key in ('learned_vocabulary', 'struggled_vocabulary', 'grammar_concepts_mastered'):
        combined = old_mem.get(key, []) + new_mem.get(key, [])
        seen = set()
        deduped = []
        for item in combined:
            item = item.strip()
            norm = item.lower()
            if norm and norm not in seen:
                seen.add(norm)
                deduped.append(item)
        merged[key] = deduped

    # Drop words from "struggled" once they've been marked as learned.
    learned_norm = {w.lower() for w in merged['learned_vocabulary']}
    merged['struggled_vocabulary'] = [w for w in merged['struggled_vocabulary'] if w.lower() not in learned_norm]

    # Keep a running log of session notes rather than discarding past summaries.
    history = list(old_mem.get('session_history', []))
    new_note = new_mem.get('session_notes', '').strip()
    if new_note:
        history.append(new_note)
    merged['session_history'] = history
    merged['session_notes'] = new_note or old_mem.get('session_notes', '')

    return merged

def load_system_prompt_template(template_path=None):
    """Load the system prompt template from a JSON file. If template_path is not
    provided, uses the default_system_prompt.json bundled with the package."""
    if template_path is None:
        try:
            template_text = resources.files("italian_tutor").joinpath("default_system_prompt.json").read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError("default_system_prompt.json not found in package data")
    else:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_text = f.read()
    return json.loads(template_text)

def build_system_prompt(user_mem, template_path=None, focus_word=None):
    """Build the system prompt that injects the current persistent memory state.
    Loads the prompt template from a JSON file (default_system_prompt.json by default)
    and substitutes user memory values into it.
    
    Args:
        user_mem (dict): User memory state
        template_path (str): Path to custom template JSON (None = default)
        focus_word (str): For structured mode, the word to focus on teaching
    """
    template = load_system_prompt_template(template_path)
    
    prompt_lines = [
        f"You are \"{template['character']}\", an empathetic Italian tutor. You use a scaffolded learning methodology.",
        ""
    ]
    
    user_state = template['user_state_section']
    prompt_lines.append(user_state['title'])
    
    for field in user_state['fields']:
        label = field['label']
        key = field['key']
        value = user_mem.get(key, "")
        
        if field.get('format') == 'comma_joined':
            value = ', '.join(value) if isinstance(value, list) else str(value)
        
        prompt_lines.append(f"- {label}: {value}")
    
    prompt_lines.append("")
    
    # For structured mode, add focus word and structured rules
    if focus_word and 'structured_teaching_rules' in template:
        prompt_lines.append("CURRENT FOCUS WORD:")
        prompt_lines.append(f"The focus word for this session is: {focus_word}")
        prompt_lines.append("")
        prompt_lines.append("TEACHING RULES - STRUCTURED MODE:")
        for i, rule in enumerate(template['structured_teaching_rules'], 1):
            prompt_lines.append(f"{i}. {rule}")
    else:
        prompt_lines.append("TEACHING RULES:")
        rules = template.get('teaching_rules', template.get('structured_teaching_rules', []))
        for i, rule in enumerate(rules, 1):
            prompt_lines.append(f"{i}. {rule}")
    
    return "\n    ".join(prompt_lines)

def is_input_safe(user_input):
    """Screen user input through the prompt-firewall model before it reaches
    the tutor model. Returns (is_safe, verdict) where is_safe is True only
    when the firewall explicitly returns "SAFE"; "INJECTION", any other
    verdict, or a failed firewall call are all treated as unsafe."""
    try:
        res = ollama.chat(
            model=FIREWALL_MODEL_NAME,
            messages=[{"role": "user", "content": user_input}],
        )
        verdict = res['message']['content'].strip().upper()
    except Exception as e:
        return False, f"ERROR ({e})"
    return verdict != "INJECTION", verdict

def finalize_session(user_mem, messages):
    """Ask the model to summarize the conversation so far, merge the result into
    the existing memory, and persist it to disk. Returns the merged memory dict,
    or the original memory unchanged if the model's output could not be parsed."""
    print("\nSaving your progress to memory...")
    cefr_descriptions = load_cefr_descriptions()
    update_prompt = f"""
    Analyze the session history above. Review the user's demonstrated Italian
    proficiency against the official CEFR level descriptions below, and choose
    the single CEFR code (A1, A2, B1, B2, C1, or C2) that best matches their
    performance in this session.

    CEFR LEVEL DESCRIPTIONS:
    {cefr_descriptions}

    Provide a valid JSON update matching this schema exactly. For learned_vocabulary and struggled_vocabulary, include only Italian words:
    {{
      "proficiency_level": "A1|A2|B1|B2|C1|C2",
      "learned_vocabulary": ["list", "of", "words"],
      "struggled_vocabulary": ["words"],
      "grammar_concepts_mastered": ["concepts"],
      "session_notes": "one sentence summary of progress"
    }}
    Do not output any markdown formatting, only raw JSON text.
    """
    messages.append({"role": "user", "content": update_prompt})

    res = ollama.chat(model=MODEL_NAME, messages=messages)
    raw_content = res['message']['content']
    try:
        raw_json = raw_content.strip().replace("```json", "").replace("```", "")
        updated_data = json.loads(raw_json)
        merged_data = merge_memory(user_mem, updated_data)
        save_memory(merged_data)
        print(f"Progress saved! Current level updated to: {merged_data['proficiency_level']}")
        return merged_data
    except Exception as e:
        print(f"Failed to auto-update memory structure due to parsing error: {e}")
        print(f"Raw model output was: {raw_content!r}")
        print("History kept as is.")
        return user_mem

def main_structured():
    """Run the tutor in structured mode, focusing on one word at a time."""
    user_mem = load_memory()
    
    # Load word list
    try:
        word_list = load_word_list()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Falling back to free mode...")
        return main()
    
    # Get the structured template
    structured_template = None
    try:
        structured_template = str(Path(__file__).parent / "structured_system_prompt.json")
    except Exception:
        print("Warning: Could not find structured_system_prompt.json")
    
    # Pick the first word
    recent_words = []
    focus_word = pick_next_word(word_list, recent_words)
    recent_words = update_recent_words(recent_words, focus_word)
    
    system_prompt = build_system_prompt(user_mem, template_path=structured_template, focus_word=focus_word)
    
    print(f"--- Welcome back! Loaded proficiency: {user_mem['proficiency_level']} ---")
    print(f"--- STRUCTURED MODE - Focus Word: {focus_word} ---")
    print("Paolo: Ciao! Siamo in modalità 'strutturata'. Ci focalizziamo su una parola alla volta. (Type '/free' to switch to free mode, '/exit' to quit)\n")
    
    messages = [{"role": "system", "content": system_prompt}]
    
    while True:
        try:
            user_input = input("You: ")
            stripped_input = user_input.strip().lower()

            if stripped_input in ["/exit", "/quit", "exit", "quit"]:
                break

            if stripped_input in ["/free"]:
                # Switch to free mode
                print("\n--- Switching to FREE mode ---")
                finalize_session(user_mem, messages)
                user_mem = load_memory()
                return main()

            if stripped_input in ["/next", "/prossimo"]:
                # Move to next word
                focus_word = pick_next_word(word_list, recent_words)
                recent_words = update_recent_words(recent_words, focus_word)
                system_prompt = build_system_prompt(user_mem, template_path=structured_template, focus_word=focus_word)
                messages = [{"role": "system", "content": system_prompt}]
                print(f"\n--- New Focus Word: {focus_word} ---\n")
                continue

            if stripped_input in ["/reset", "/restart"]:
                # Save and reset session
                finalize_session(user_mem, messages)
                user_mem = load_memory()
                recent_words = []
                focus_word = pick_next_word(word_list, recent_words)
                recent_words = update_recent_words(recent_words, focus_word)
                system_prompt = build_system_prompt(user_mem, template_path=structured_template, focus_word=focus_word)
                messages = [{"role": "system", "content": system_prompt}]
                print(f"\n--- Session reset! Loaded proficiency: {user_mem['proficiency_level']} ---")
                print(f"--- Focus Word: {focus_word} ---\n")
                continue

            is_safe, verdict = is_input_safe(user_input)
            if not is_safe:
                print(f"\n⚠️  Message blocked by prompt-firewall (verdict: {verdict}). Please rephrase and try again.\n")
                continue

            messages.append({"role": "user", "content": user_input})
            
            response = ollama.chat(model=MODEL_NAME, messages=messages, stream=True)
            
            print("Paolo: ", end="", flush=True)
            assistant_response = ""
            for chunk in response:
                content = chunk['message']['content']
                print(content, end="", flush=True)
                assistant_response += content
            print("\n")
            
            messages.append({"role": "assistant", "content": assistant_response})
            
        except KeyboardInterrupt:
            break

    finalize_session(user_mem, messages)


def main():
    """Main CLI entry point - supports --structured flag."""
    # Check for --structured flag
    structured_mode = "--structured" in sys.argv
    
    if structured_mode:
        return main_structured()
    
    # Otherwise run in free mode
    user_mem = load_memory()
    system_prompt = build_system_prompt(user_mem)

    print(f"--- Welcome back! Loaded proficiency: {user_mem['proficiency_level']} ---")
    print("Paolo: Ciao! Sono pronto per iniziare. (Type '/exit' to save and quit, '/reset' to save and start a new session, '/structured' for structured mode)\n")
    
    messages = [{"role": "system", "content": system_prompt}]
    
    while True:
        try:
            user_input = input("You: ")
            stripped_input = user_input.strip().lower()

            if stripped_input in ["/exit", "/quit", "exit", "quit"]:
                break

            if stripped_input in ["/structured"]:
                # Switch to structured mode
                print("\n--- Switching to STRUCTURED mode ---")
                finalize_session(user_mem, messages)
                return main_structured()

            if stripped_input in ["/reset", "/restart"]:
                # Save/merge this session's progress exactly as if closing, then
                # reload from disk so the model drops any role-play context
                # (e.g. "barista and customer") and starts a clean conversation.
                finalize_session(user_mem, messages)
                user_mem = load_memory()
                system_prompt = build_system_prompt(user_mem)
                messages = [{"role": "system", "content": system_prompt}]
                print(f"\n--- Session reset! Loaded proficiency: {user_mem['proficiency_level']} ---")
                print("Paolo: Ciao di nuovo! Ricominciamo. (Type '/exit' to save and quit, '/reset' to save and start a new session)\n")
                continue

            is_safe, verdict = is_input_safe(user_input)
            if not is_safe:
                print(f"\n⚠️  Message blocked by prompt-firewall (verdict: {verdict}). Please rephrase and try again.\n")
                continue

            messages.append({"role": "user", "content": user_input})
            
            # Request response streaming from your RTX A1000
            response = ollama.chat(model=MODEL_NAME, messages=messages, stream=True)
            
            print("Paolo: ", end="", flush=True)
            assistant_response = ""
            for chunk in response:
                content = chunk['message']['content']
                print(content, end="", flush=True)
                assistant_response += content
            print("\n")
            
            messages.append({"role": "assistant", "content": assistant_response})
            
        except KeyboardInterrupt:
            break

    # --- SESSION COOLDOWN & UPDATE MEMORY ---
    finalize_session(user_mem, messages)

if __name__ == "__main__":
    main()
