import base64
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

AGENTS_DIR = Path(__file__).parent / "agents"
MODEL = "gemini-2.5-flash"
DB_PATH = Path(__file__).parent / "sessions.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id               TEXT PRIMARY KEY,
                email            TEXT,
                business_type    TEXT,
                process_name     TEXT,
                transcript       TEXT,
                diagram_asis     TEXT,
                diagram_improved TEXT,
                report           TEXT,
                created_at       TEXT
            )
        """)
        conn.commit()


init_db()


def load_agent(name: str) -> str:
    path = AGENTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Agent prompt not found: {name}")
    return path.read_text()


def to_gemini_messages(messages: list) -> list:
    """Convert {role: user/assistant, content: str} to Gemini format."""
    converted = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        converted.append({"role": role, "parts": [{"text": m["content"]}]})
    return converted


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Streaming SSE endpoint for the interview agent."""
    data = request.json
    messages = data["messages"]
    agent = data.get("agent", "interviewer")
    system_prompt = load_agent(agent)

    def generate():
        try:
            for chunk in client.models.generate_content_stream(
                model=MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=2000,
                ),
                contents=to_gemini_messages(messages),
            ):
                if chunk.text:
                    payload = json.dumps(
                        {"type": "content_block_delta", "delta": {"text": chunk.text}}
                    )
                    yield f"data: {payload}\n\n"
        except Exception as e:
            payload = json.dumps({"type": "error", "error": str(e)})
            yield f"data: {payload}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/invoke", methods=["POST"])
def invoke():
    """Non-streaming endpoint for pipeline agents."""
    try:
        data = request.json
        agent = data["agent"]
        user_content = data["user_content"]
        max_tokens = data.get("max_tokens", 4000)
        system_prompt = load_agent(agent)

        response = client.models.generate_content(
            model=MODEL,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
            contents=user_content,
        )
        return jsonify({"text": response.text})
    except Exception as e:
        app.logger.exception("invoke error")
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf", methods=["POST"])
def generate_pdf():
    try:
        from weasyprint import HTML

        data = request.json
        diagram_asis = data.get("diagram_asis", "")
        diagram_improved = data.get("diagram_improved", "")
        report = data.get("report", "")
        business_type = data.get("business_type", "")
        process_name = data.get("process_name", "")

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  @page {{ size: A4; margin: 1.5cm; }}
  body {{ font-family: DejaVu Sans, sans-serif; font-size: 10.5pt; line-height: 1.5; color: #1f2937; margin: 0; }}
  h1 {{ font-size: 18pt; color: #1e1b4b; margin: 0 0 4pt; }}
  .meta {{ color: #6b7280; font-size: 10pt; margin-bottom: 24pt; }}
  h2 {{ font-size: 12pt; color: #4338ca; margin: 24pt 0 8pt; border-bottom: 1px solid #e0e7ff; padding-bottom: 4pt; }}
  .diagram {{ margin: 8pt 0 16pt; page-break-inside: avoid; }}
  .diagram svg {{ max-width: 100%; height: auto; display: block; }}
  pre {{ white-space: pre-wrap; font-family: DejaVu Sans Mono, monospace; font-size: 9pt;
         line-height: 1.6; background: #f9fafb; padding: 14pt; border-radius: 4pt;
         border: 1px solid #e5e7eb; margin: 0; }}
</style></head><body>
  <h1>Operational Assessment</h1>
  <div class="meta">{business_type}{' · ' + process_name if process_name else ''}</div>

  <h2>Current Process Flow</h2>
  <div class="diagram">{diagram_asis if diagram_asis else '<p style="color:#9ca3af">No diagram available.</p>'}</div>

  <h2>Improved Process Flow</h2>
  <div class="diagram">{diagram_improved if diagram_improved else '<p style="color:#9ca3af">No diagram available.</p>'}</div>

  <h2>Assessment Report</h2>
  <pre>{report}</pre>
</body></html>"""

        pdf = HTML(string=html).write_pdf()
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=ops-assessment.pdf"},
        )
    except Exception as e:
        app.logger.exception("pdf error")
        return jsonify({"error": str(e)}), 500


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_key = os.environ.get("ADMIN_KEY", "")
        if not admin_key:
            return "ADMIN_KEY not set in environment", 403
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                _, password = base64.b64decode(auth[6:]).decode().split(":", 1)
                if password == admin_key:
                    return f(*args, **kwargs)
            except Exception:
                pass
        return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Admin"'})
    return decorated


@app.route("/admin")
@require_admin
def admin_list():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, email, business_type, process_name, created_at FROM sessions ORDER BY created_at DESC"
        ).fetchall()
    return render_template("admin.html", sessions=rows)


@app.route("/admin/<session_id>")
@require_admin
def admin_detail(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        return "Session not found", 404
    return render_template("admin_session.html", s=row)


@app.route("/api/session", methods=["POST"])
def save_session():
    try:
        data = request.json
        session_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO sessions
                   (id, email, business_type, process_name,
                    transcript, diagram_asis, diagram_improved, report, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    data.get("email", ""),
                    data.get("business_type", ""),
                    data.get("process_name", ""),
                    data.get("transcript", ""),
                    data.get("diagram_asis", ""),
                    data.get("diagram_improved", ""),
                    data.get("report", ""),
                    created_at,
                ),
            )
            conn.commit()
        return jsonify({"session_id": session_id})
    except Exception as e:
        app.logger.exception("session save error")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
