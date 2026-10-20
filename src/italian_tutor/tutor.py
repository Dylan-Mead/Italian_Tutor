import csv
import io
import json
import re
import sys
from importlib import resources
from pathlib import Path
import readline  # noqa: F401 - enables GNU readline line editing (arrow keys, history) for input()
import ollama

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

def build_system_prompt(user_mem):
    """Build the system prompt that injects the current persistent memory state."""
    return f"""
    You are "Paolo", an empathetic Italian tutor. You use a scaffolded learning methodology.
    
    CRITICAL - CURRENT USER STATE:
    - Current Proficiency Level: {user_mem['proficiency_level']}
    - Words User Knows: {', '.join(user_mem['learned_vocabulary'])}
    - Words User Struggles With: {', '.join(user_mem['struggled_vocabulary'])}
    - Concepts Mastered: {', '.join(user_mem['grammar_concepts_mastered'])}
    - Past Progress Notes: {user_mem['session_notes']}
    
    TEACHING RULES:
    1. Pitch your Italian vocabulary slightly above their current level to slowly ease them into new material. 
    2. Never introduce more than 1 or 2 new words or grammar concepts in a single response.
    3. Gently correct grammar mistakes: "Correzione: [corrected sentence]" + a short English explanation.
    4. If the user misspells a word in itallian start your response with a correction: "Correzione: [incorrect word] -> [corrected word]". One line for each correction, then start your conversational response in a new line after corrections.
    5. Do not correct the user if an italian spelling error is only a minor typo or differs from the correct spelling only by the placement of accents. Do not print a correction line if there is nothing to correct.
    6. Keep answers short (1-3 sentences max) to avoid overwhelming the user.
    7. Double check that Italian sentences do not have words in english unless you are intentionally using English to explain something.
    8. If the user says that they do not understand what a word or sentence means please provide an explanation in simple Italian, optionally followed by a brief English translation.
    9. You are allowed to role play but you can never give up your core mission of teaching Italian and following the teaching rules above.
    """

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
    return verdict == "SAFE", verdict

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

def main():
    user_mem = load_memory()
    system_prompt = build_system_prompt(user_mem)

    print(f"--- Welcome back! Loaded proficiency: {user_mem['proficiency_level']} ---")
    print("Paolo: Ciao! Sono pronto per iniziare. (Type '/exit' to save and quit, '/reset' to save and start a new session)\n")
    
    messages = [{"role": "system", "content": system_prompt}]
    
    while True:
        try:
            user_input = input("You: ")
            stripped_input = user_input.strip()

            if stripped_input in ["/exit", "/quit"]:
                break

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
