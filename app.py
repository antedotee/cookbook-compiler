"""Local web server for the Digital Cookbook Compiler. Run: python app.py, then open http://127.0.0.1:8000"""

import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, request

from compiler import compile_recipe
from compiler.kitchen import vocab

ROOT = Path(__file__).parent
EXAMPLES = ROOT / "examples"
MAX_SOURCE = 20_000

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 200_000


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/vocab")
def get_vocab():
    return jsonify(vocab())


@app.get("/api/examples")
def get_examples():
    examples = []
    for path in sorted(EXAMPLES.glob("*.ck")):
        source = path.read_text(encoding="utf-8")
        first = source.splitlines()[0] if source else ""
        title = first.lstrip("# ").strip() if first.startswith("#") else path.stem
        examples.append({"id": path.stem, "title": title, "source": source})
    return jsonify(examples)


@app.post("/api/compile")
def post_compile():
    body = request.get_json(silent=True)
    source = body.get("source") if isinstance(body, dict) else None
    if not isinstance(source, str):
        return jsonify({"error": "send JSON like {\"source\": \"RECIPE CAKE; ...\"}"}), 400
    if len(source) > MAX_SOURCE:
        return jsonify({"error": f"recipe is longer than {MAX_SOURCE} characters"}), 413
    return jsonify(compile_recipe(source))


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    url = f"http://127.0.0.1:{port}"
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            sys.exit(f"Port {port} is already in use. Close the other program, or run with PORT=8001.")
    if "--open" in sys.argv:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    print(f"Digital Cookbook Compiler running at {url}  (Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
