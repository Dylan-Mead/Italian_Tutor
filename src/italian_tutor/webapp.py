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
import secrets
import socket
import threading
import uuid

import ollama
from flask import Flask, Response, jsonify, render_template, request, session, stream_with_context

from italian_tutor.tutor import (
    MODEL_NAME,
    build_system_prompt,
    finalize_session,
    is_input_safe,
    load_memory,
)

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
# cookie: {"user_mem": {...}, "messages": [...]}. This lives in memory only -
# restarting the server just starts new conversations; saved progress in
# tutor_memory.json is unaffected.
CONVERSATIONS = {}


def _new_conversation():
    user_mem = load_memory()
    return {
        "user_mem": user_mem,
        "messages": [{"role": "system", "content": build_system_prompt(user_mem)}],
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
    conv = get_conversation()
    return render_template("chat.html", history=_history_for_display(conv["messages"]))


@app.route("/api/memory")
def api_memory():
    conv = get_conversation()
    return jsonify(conv["user_mem"])


@app.route("/api/chat", methods=["POST"])
def api_chat():
    conv = get_conversation()
    user_input = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Empty message."}), 400

    if not TUTOR_LOCK.acquire(timeout=LOCK_TIMEOUT_SECONDS):
        return jsonify({"error": "Paolo is busy with another conversation right now. Please try again shortly."}), 503

    try:
        is_safe, verdict = is_input_safe(user_input)
    except Exception:
        TUTOR_LOCK.release()
        raise

    if not is_safe:
        TUTOR_LOCK.release()
        return jsonify({"blocked": True, "verdict": verdict})

    conv["messages"].append({"role": "user", "content": user_input})

    def generate():
        assistant_response = ""
        try:
            response = ollama.chat(model=MODEL_NAME, messages=conv["messages"], stream=True)
            for chunk in response:
                content = chunk["message"]["content"]
                assistant_response += content
                yield content
        finally:
            conv["messages"].append({"role": "assistant", "content": assistant_response})
            TUTOR_LOCK.release()

    return Response(stream_with_context(generate()), mimetype="text/plain")


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
        conv["messages"][0] = {"role": "system", "content": build_system_prompt(merged)}
    return jsonify(merged)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Equivalent of the CLI's /reset: save progress, then start a brand new
    conversation built from the freshly merged memory."""
    conv = get_conversation()
    with TUTOR_LOCK:
        merged = finalize_session(conv["user_mem"], conv["messages"])
        conv["user_mem"] = merged
        conv["messages"] = [{"role": "system", "content": build_system_prompt(merged)}]
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
    print("Starting Italian Tutor web UI...")
    print(f"  Local:   http://127.0.0.1:{port}")
    print(f"  Network: http://{lan_ip}:{port}  (open this from other devices on your home network)")
    app.run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    main()
