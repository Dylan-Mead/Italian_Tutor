# Italian_Tutor

An AI Italian tutor ("Paolo") backed by local [Ollama](https://ollama.com) models, with a
command-line interface and a Flask-based web UI.

## Setup

```sh
pip install -e .
```

This installs the `tutor` (CLI) and `tutor-web` (web UI) commands, along with the
dependencies listed in `requirements.txt`. Make sure Ollama is running locally with the
`qwen3:8b` and `prompt-firewall` models available (see `prompt_firewall` for the firewall
model's `Modelfile`).

## Command-line usage

```sh
tutor
```

Chat with Paolo directly in the terminal. Type `/exit` to save progress and quit, or
`/reset` to save progress and start a fresh conversation.

## Web UI

```sh
tutor-web
```

This starts a Flask server bound to `0.0.0.0:5000`, printing both a local URL and a
network URL (e.g. `http://192.168.1.23:5000`). Open the network URL from any phone,
tablet, or computer on the same home network to chat with Paolo in the browser - the
page shows your current proficiency level, learned/struggled vocabulary, and mastered
grammar concepts alongside the chat.

Use the **Save Progress** button to checkpoint your proficiency to `tutor_memory.json`
without losing the current conversation, and **New Conversation** to save and start a
fresh chat (equivalent to the CLI's `/reset`).

Notes:
- `tutor_memory.json` is a single shared profile - if you chat from two devices at the
  same time, saving/resetting on one may not include vocabulary learned concurrently on
  the other until the conversations are reconciled, since each merges from the memory
  state it last loaded.
- The built-in Flask server is fine for personal/home use but is not a production WSGI
  server; only expose it on your trusted home network.
- If your OS firewall blocks LAN connections, allow inbound TCP traffic on port 5000.
