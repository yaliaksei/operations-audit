import base64
import json
import os
from functools import wraps
from pathlib import Path

import yaml

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from services.ai import invoke_agent, stream_chat
from services.db import get_session, init_db, list_sessions, save_contact, save_session
from services.pdf import build_pdf

load_dotenv()

app = Flask(__name__)
init_db()

SEO_DIR = Path(__file__).parent / "seo"


# ── Pages ──────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("landing.html", base_url=request.url_root.rstrip("/"))


@app.route("/app")
def index():
    return render_template("index.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/for/<slug>")
def for_page(slug):
    path = SEO_DIR / f"{slug}.yaml"
    if not path.exists():
        return "Page not found", 404
    page = yaml.safe_load(path.read_text())
    return render_template("for.html", page=page, slug=slug, base_url=request.url_root.rstrip("/"))


@app.route("/sitemap.xml")
def sitemap():
    base = request.host_url.rstrip("/")
    static_paths = ["/", "/app", "/terms", "/privacy", "/contact"]
    seo_slugs = [p.stem for p in SEO_DIR.glob("*.yaml")]

    urls = [f"  <url><loc>{base}{p}</loc></url>" for p in static_paths]
    urls += [f"  <url><loc>{base}/for/{s}</loc></url>" for s in sorted(seo_slugs)]

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return Response(xml, mimetype="application/xml")


# ── AI API ─────────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    """Streaming SSE endpoint for the interview agent."""
    data = request.json
    messages = data["messages"]
    agent = data.get("agent", "interviewer")
    business_type = data.get("business_type", "")

    def generate():
        try:
            for text in stream_chat(messages, agent, business_type):
                payload = json.dumps({"type": "content_block_delta", "delta": {"text": text}})
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
        text = invoke_agent(data["agent"], data["user_content"], data.get("max_tokens", 4000), data.get("business_type", ""))
        return jsonify({"text": text})
    except Exception as e:
        app.logger.exception("invoke error")
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf", methods=["POST"])
def generate_pdf():
    try:
        data = request.json
        pdf = build_pdf(
            diagram_asis=data.get("diagram_asis", ""),
            diagram_improved=data.get("diagram_improved", ""),
            report=data.get("report", ""),
            business_type=data.get("business_type", ""),
            process_name=data.get("process_name", ""),
        )
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=ops-assessment.pdf"},
        )
    except Exception as e:
        app.logger.exception("pdf error")
        return jsonify({"error": str(e)}), 500


# ── Session & contact ──────────────────────────────────────────────────────────

@app.route("/api/session", methods=["POST"])
def api_save_session():
    try:
        session_id = save_session(request.json)
        return jsonify({"session_id": session_id})
    except Exception as e:
        app.logger.exception("session save error")
        return jsonify({"error": str(e)}), 500


@app.route("/api/contact", methods=["POST"])
def api_save_contact():
    try:
        save_contact(request.json)
        return jsonify({"ok": True})
    except Exception as e:
        app.logger.exception("contact error")
        return jsonify({"error": str(e)}), 500


# ── Admin ──────────────────────────────────────────────────────────────────────

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
    return render_template("admin.html", sessions=list_sessions())


@app.route("/admin/<session_id>")
@require_admin
def admin_detail(session_id):
    row = get_session(session_id)
    if row is None:
        return "Session not found", 404
    return render_template("admin_session.html", s=row)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
