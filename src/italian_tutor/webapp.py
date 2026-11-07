"""Flask web UI for the Italian tutor.

Lets you chat with "Paolo" from a browser on any device on your home
network, instead of only the command line.

Run with:
    tutor-web
or:
    python -m italian_tutor.webapp

Then visit the printed "Network" URL from any device on the same
network (e.g. a phone or tablet), or http://127.0.0.1:5000 locally.
"""
import copy
import logging
import secrets
import socket
import threading
import uuid
from importlib import resources

import ollama
from flask import Flask, Response, jsonify, render_template, request, session, stream_with_context

from italian_tutor.tutor import (
    MODEL_NAME,
    build_system_prompt,
    finalize_session,
    is_input_safe,
    load_memory,
    load_word_list,
    pick_next_word,
    update_recent_words,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# A fresh random secret each process start is fine here: it only signs the
# session cookie that carries a per-browser conversation id, not anything
# sensitive, and losing it on restart just starts everyone on a fresh
# conversation (tutor_memory.json itself is untouched).
app.secret_key = secrets.token_hex(32)

# Every ollama call (firewall check, chat turn, session finalization) and
# every read/write of the shared tutor_memory.json file go through this lock.
# There's one local GPU running one model at a time, and tutor_memory.json is
# a single shared profile, so serializing everything keeps things correct
# even if several devices use the web UI at once.
TUTOR_LOCK = threading.Lock()
LOCK_TIMEOUT_SECONDS = 60

# Per-browser conversation state, keyed by an id stored in the session
# cookie: {"user_mem": {...}, "messages": [...], "teaching_mode": "free", "recent_words": [], "word_list": ...}.
# This lives in memory only - restarting the server just starts new conversations; saved progress in
# tutor_memory.json is unaffected.
CONVERSATIONS = {}


def get_template_path(mode):
    """Get the full path to a system prompt template."""
    if mode == "structured":
        return str(resources.files("italian_tutor").joinpath("structured_system_prompt.json"))
    return None


def has_valid_word_list(word_list):
    """Check if word_list is loaded and not empty."""
    if word_list is None or isinstance(word_list, list) and len(word_list) == 0:
        return False
    # For pandas DataFrames, check if not empty
    if hasattr(word_list, 'empty'):
        return not word_list.empty
    return True


def _new_conversation():
    user_mem = load_memory()
    template_path = None
    focus_word = None
    
    return {
        "user_mem": user_mem,
        "teaching_mode": "free",
        "recent_words": [],
        "word_list": None,
        "focus_word": None,
        "messages": [{"role": "system", "content": build_system_prompt(user_mem, template_path, focus_word)}],
    }


def get_conversation():
    """Fetch (creating if necessary) the conversation tied to this browser's
    session cookie."""
    conv_id = session.get("conv_id")
    if conv_id is None or conv_id not in CONVERSATIONS:
        conv_id = uuid.uuid4().hex
        session["conv_id"] = conv_id
        CONVERSATIONS[conv_id] = _new_conversation()
    return CONVERSATIONS[conv_id]


def _history_for_display(messages):
    """Drop the system prompt; the client only needs to render user/assistant turns."""
    return [m for m in messages if m["role"] in ("user", "assistant")]


@app.route("/")
def index():
    logger.info("Index route accessed")
    conv = get_conversation()
    logger.info(f"Conversation created/retrieved: {len(conv['messages'])} messages")
    return render_template("chat.html", history=_history_for_display(conv["messages"]))


@app.route("/api/memory")
def api_memory():
    conv = get_conversation()
    return jsonify(conv["user_mem"])


@app.route("/api/chat", methods=["POST"])
def api_chat():
    logger.info("=== /api/chat endpoint called ===")
    conv = get_conversation()
    user_input = (request.get_json(silent=True) or {}).get("message", "").strip()
    logger.info(f"User input received: '{user_input}'")
    
    if not user_input:
        logger.warning("Empty message received")
        return jsonify({"error": "Empty message."}), 400

    logger.info("Attempting to acquire TUTOR_LOCK...")
    if not TUTOR_LOCK.acquire(timeout=LOCK_TIMEOUT_SECONDS):
        logger.error("Failed to acquire TUTOR_LOCK within timeout")
        return jsonify({"error": "Paolo is busy with another conversation right now. Please try again shortly."}), 503

    logger.info("TUTOR_LOCK acquired")
    try:
        logger.info("Checking if input is safe...")
        is_safe, verdict = is_input_safe(user_input)
        logger.info(f"Safety check result: is_safe={is_safe}, verdict={verdict}")
    except Exception as e:
        logger.error(f"Exception during safety check: {e}", exc_info=True)
        TUTOR_LOCK.release()
        raise

    if not is_safe:
        logger.warning(f"Input blocked: {verdict}")
        TUTOR_LOCK.release()
        return jsonify({"blocked": True, "verdict": verdict})

    # Handle mode switching commands
    if user_input.lower() in ("/structured", "/free"):
        logger.info(f"Mode switch command detected: {user_input.lower()}")
        conv["messages"].append({"role": "user", "content": user_input})
        new_mode = "structured" if user_input.lower() == "/structured" else "free"
        conv["teaching_mode"] = new_mode
        
        # Load word list and pick first word for structured mode
        if new_mode == "structured":
            if conv["word_list"] is None:
                try:
                    conv["word_list"] = load_word_list()
                except Exception as e:
                    logger.warning(f"Failed to load word list: {e}")
                    conv["word_list"] = []
            
            if has_valid_word_list(conv["word_list"]):
                conv["focus_word"] = pick_next_word(conv["word_list"], conv["recent_words"])
                update_recent_words(conv["recent_words"], conv["focus_word"])
        else:
            conv["focus_word"] = None
        
        # Rebuild system prompt with new mode
        template_path = get_template_path(new_mode)
        conv["messages"][0] = {
            "role": "system",
            "content": build_system_prompt(conv["user_mem"], template_path, conv["focus_word"])
        }
        
        mode_name = "Structured" if new_mode == "structured" else "Free"
        assistant_response = f"Switched to {mode_name} mode. {('Now teaching the word: ' + conv['focus_word']) if new_mode == 'structured' else ''}"
        conv["messages"].append({"role": "assistant", "content": assistant_response})
        logger.info(f"Mode switched to {mode_name}")
        
        TUTOR_LOCK.release()
        return Response(assistant_response, mimetype="text/plain")

    logger.info("Regular message, appending to conversation history")
    conv["messages"].append({"role": "user", "content": user_input})
    logger.info(f"Message count in conversation: {len(conv['messages'])}")

    def generate():
        logger.info("=== Starting generate() ===")
        logger.info(f"Preparing to call Ollama with model: {MODEL_NAME}")
        logger.info(f"Message count before Ollama call: {len(conv['messages'])}")
        assistant_response = ""
        try:
            logger.info("Calling ollama.chat()...")
            response = ollama.chat(model=MODEL_NAME, messages=conv["messages"], stream=True)
            logger.info("ollama.chat() returned successfully, streaming response...")
            chunk_count = 0
            for chunk in response:
                chunk_count += 1
                content = chunk["message"]["content"]
                logger.debug(f"Chunk {chunk_count}: {len(content)} chars received")
                assistant_response += content
                yield content
            logger.info(f"Streaming complete: {chunk_count} chunks, total: {len(assistant_response)} chars")
        except Exception as e:
            logger.error(f"Exception in generate(): {e}", exc_info=True)
            yield f"\n[ERROR: {e}]"
        finally:
            logger.info(f"Appending assistant response ({len(assistant_response)} chars) to conversation")
            conv["messages"].append({"role": "assistant", "content": assistant_response})
            logger.info("Releasing TUTOR_LOCK")
            TUTOR_LOCK.release()
            logger.info("=== generate() complete ===")

    logger.info("Returning Response stream")
    return Response(stream_with_context(generate()), mimetype="text/plain")


@app.route("/api/mode", methods=["POST"])
def api_set_mode():
    """Switch between free and structured teaching modes."""
    conv = get_conversation()
    mode = (request.get_json(silent=True) or {}).get("mode", "free").lower()
    
    if mode not in ("free", "structured"):
        return jsonify({"error": "Invalid mode. Use 'free' or 'structured'."}), 400
    
    if not TUTOR_LOCK.acquire(timeout=LOCK_TIMEOUT_SECONDS):
        return jsonify({"error": "Paolo is busy with another conversation right now. Please try again shortly."}), 503

    try:
        conv["teaching_mode"] = mode
        
        # Load word list and pick first word for structured mode
        if mode == "structured":
            if conv["word_list"] is None:
                try:
                    conv["word_list"] = load_word_list()
                except Exception:
                    conv["word_list"] = []
            
            if has_valid_word_list(conv["word_list"]):
                conv["focus_word"] = pick_next_word(conv["word_list"], conv["recent_words"])
                update_recent_words(conv["recent_words"], conv["focus_word"])
        else:
            conv["focus_word"] = None
        
        # Rebuild system prompt with new mode
        template_path = get_template_path(mode)
        conv["messages"][0] = {
            "role": "system",
            "content": build_system_prompt(conv["user_mem"], template_path, conv["focus_word"])
        }
        
        return jsonify({"mode": mode, "focus_word": conv["focus_word"]})
    finally:
        TUTOR_LOCK.release()


@app.route("/api/save", methods=["POST"])
def api_save():
    """Checkpoint progress into tutor_memory.json without interrupting the
    current conversation."""
    conv = get_conversation()
    with TUTOR_LOCK:
        # finalize_session mutates the list it's given (it appends a hidden
        # summary-request message), so hand it a copy to keep the live
        # conversation clean.
        merged = finalize_session(conv["user_mem"], copy.copy(conv["messages"]))
        conv["user_mem"] = merged
        template_path = get_template_path(conv["teaching_mode"])
        conv["messages"][0] = {"role": "system", "content": build_system_prompt(merged, template_path, conv["focus_word"])}
    return jsonify(merged)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Equivalent of the CLI's /reset: save progress, then start a brand new
    conversation built from the freshly merged memory."""
    conv = get_conversation()
    with TUTOR_LOCK:
        merged = finalize_session(conv["user_mem"], conv["messages"])
        conv["user_mem"] = merged
        template_path = get_template_path(conv.get("teaching_mode"))
        conv["messages"] = [{"role": "system", "content": build_system_prompt(merged, template_path, conv.get("focus_word"))}]
    return jsonify(merged)


def _detect_lan_ip():
    """Best-effort guess at this machine's LAN-facing IP address, for
    printing a convenient URL to open from other devices. Uses a UDP
    "connect" (which only consults the routing table and sends no packets)
    rather than relying on /etc/hosts, which often just maps the hostname to
    127.0.1.1 on Linux."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    port = 5000
    lan_ip = _detect_lan_ip()
    logger.info("=" * 80)
    logger.info("STARTING ITALIAN TUTOR WEB UI")
    logger.info("=" * 80)
    print("Starting Italian Tutor web UI...")
    print(f"  Local:   http://127.0.0.1:{port}")
    print(f"  Network: http://{lan_ip}:{port}  (open this from other devices on your home network)")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Port: {port}")
    logger.info("Ready to accept connections")
    app.run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    main()
