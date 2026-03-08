import base64
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import yaml

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)


def render_report_html(text: str) -> str:
    """Convert synthesizer markdown-like output to styled HTML for PDF rendering."""
    import re
    from html import escape as esc

    def inline(s: str) -> str:
        s = esc(s)
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
        s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
        return s

    def parse_pipe_cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip('|').split('|')]

    def is_pipe_row(line: str) -> bool:
        s = line.strip()
        if not s:
            return False
        return s.startswith('|') or s.count('|') >= 2

    def is_md_separator(line: str) -> bool:
        s = line.strip()
        return bool(s) and bool(re.match(r'^[\|\ \-:]+$', s)) and '-' in s and '|' in s

    KV_KEYS = (
        'Action', 'Tool', 'Time to set up', 'Why now', 'Expected value',
        'One-time setup cost', 'Ongoing cost', 'Total setup time', 'Rating',
    )
    kv_pattern = re.compile(r'^(' + '|'.join(re.escape(k) for k in KV_KEYS) + r'):\s*(.*)')

    lines = text.split('\n')
    n = len(lines)
    out: list[str] = []
    i = 0

    while i < n:
        raw = lines[i]
        line = raw.strip()

        # ── horizontal separators (─────) ──────────────────────────────────
        if re.match(r'^[─\-]{4,}$', line):
            i += 1
            continue

        # ── markdown headings (## / ###) ───────────────────────────────────
        m = re.match(r'^(#{1,3})\s+(.+)', line)
        if m:
            lvl = min(len(m.group(1)) + 1, 4)
            out.append(f'<h{lvl}>{inline(m.group(2))}</h{lvl}>')
            i += 1
            continue

        # ── numbered section headings: "1. PROCESS OVERVIEW" ───────────────
        if re.match(r'^\d+\.\s+[A-Z][A-Z &]+$', line):
            out.append(f'<h2>{inline(line)}</h2>')
            i += 1
            continue

        # ── health rating line starting with colored circle ─────────────────
        if line and line[0] in '🟢🟡🔴':
            color_map = {'🟢': '#15803d', '🟡': '#b45309', '🔴': '#b91c1c'}
            col = color_map.get(line[0], '#374151')
            out.append(f'<p class="health" style="color:{col}">{inline(line)}</p>')
            i += 1
            continue

        # ── pipe table (collects rows + interleaved → recommendation lines) ─
        if is_pipe_row(raw) or is_md_separator(raw):
            # Collect contiguous block: table rows, separator rows, → rec lines
            rows: list[tuple[list[str], list[str]]] = []  # (cells, recs)
            header_cells: list[str] | None = None

            while i < n:
                l = lines[i]
                ls = l.strip()
                if is_md_separator(l):
                    # The previous row was the header
                    if rows:
                        header_cells = rows[-1][0]
                        rows = []
                    i += 1
                    continue
                if is_pipe_row(l):
                    rows.append((parse_pipe_cells(l), []))
                    i += 1
                    continue
                if ls.startswith('→ ') and rows:
                    rows[-1][1].append(ls[2:])
                    i += 1
                    continue
                break

            # Heuristic: if no explicit markdown separator, treat first row
            # as header when all its cells look like labels (no emojis, short)
            if header_cells is None and rows:
                first = rows[0][0]
                has_emoji = any(
                    any(ord(ch) > 0x25FF for ch in c) for c in first
                )
                if not has_emoji:
                    header_cells = first
                    rows = rows[1:]

            ncols = len(header_cells) if header_cells else (len(rows[0][0]) if rows else 1)

            tbl = ['<table><thead><tr>']
            for c in (header_cells or []):
                tbl.append(f'<th>{inline(c)}</th>')
            tbl.append('</tr></thead><tbody>')
            for cells, recs in rows:
                tbl.append('<tr>')
                for c in cells:
                    tbl.append(f'<td>{inline(c)}</td>')
                tbl.append('</tr>')
                if recs:
                    rec_html = ' &nbsp;·&nbsp; '.join(
                        f'<span class="rec-arrow">→</span> {inline(r)}' for r in recs
                    )
                    tbl.append(f'<tr class="rec-row"><td colspan="{ncols}">{rec_html}</td></tr>')
            tbl.append('</tbody></table>')
            out.append(''.join(tbl))
            continue

        # ── standalone → recommendation lines ──────────────────────────────
        if line.startswith('→ '):
            parts = []
            while i < n and lines[i].strip().startswith('→ '):
                parts.append(
                    f'<div class="rec-line">'
                    f'<span class="rec-arrow">→</span> {inline(lines[i].strip()[2:])}'
                    f'</div>'
                )
                i += 1
            out.append(f'<div class="rec">{"".join(parts)}</div>')
            continue

        # ── key: value definition lines ─────────────────────────────────────
        if kv_pattern.match(line):
            items = []
            while i < n:
                m2 = kv_pattern.match(lines[i].strip())
                if m2:
                    items.append(
                        f'<div class="kv">'
                        f'<span class="kv-key">{esc(m2.group(1))}</span>'
                        f'<span class="kv-val">{inline(m2.group(2))}</span>'
                        f'</div>'
                    )
                    i += 1
                else:
                    break
            out.append(f'<div class="kv-block">{"".join(items)}</div>')
            continue

        # ── bullet list (-, *, •) ───────────────────────────────────────────
        if re.match(r'^[-*•]\s', line):
            items = []
            while i < n and re.match(r'^[-*•]\s', lines[i].strip()):
                items.append(f'<li>{inline(lines[i].strip()[2:])}</li>')
                i += 1
            out.append(f'<ul>{"".join(items)}</ul>')
            continue

        # ── numbered list (not section headings) ────────────────────────────
        m = re.match(r'^(\d+)[.)]\s+(.+)', line)
        if m and not re.match(r'^\d+\.\s+[A-Z][A-Z &]+$', line):
            items = []
            while i < n:
                m2 = re.match(r'^\d+[.)]\s+(.+)', lines[i].strip())
                if m2 and not re.match(r'^\d+\.\s+[A-Z][A-Z &]+$', lines[i].strip()):
                    items.append(f'<li>{inline(m2.group(1))}</li>')
                    i += 1
                else:
                    break
            out.append(f'<ol>{"".join(items)}</ol>')
            continue

        # ── Verdicts legend line ─────────────────────────────────────────────
        if line.startswith('Verdicts:'):
            out.append(f'<p class="legend">{inline(line)}</p>')
            i += 1
            continue

        # ── empty line → spacing ─────────────────────────────────────────────
        if not line:
            out.append('<div class="vspace"></div>')
            i += 1
            continue

        # ── default: paragraph ───────────────────────────────────────────────
        out.append(f'<p>{inline(line)}</p>')
        i += 1

    return '\n'.join(out)
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id         TEXT PRIMARY KEY,
                name       TEXT,
                email      TEXT,
                subject    TEXT,
                message    TEXT,
                created_at TEXT
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


SEO_DIR = Path(__file__).parent / "seo"


def load_seo_page(slug: str) -> dict | None:
    path = SEO_DIR / f"{slug}.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text())


@app.route("/for/<slug>")
def for_page(slug):
    page = load_seo_page(slug)
    if page is None:
        return "Page not found", 404
    return render_template("for.html", page=page, slug=slug, base_url=request.url_root.rstrip("/"))


@app.route("/sitemap.xml")
def sitemap():
    base = request.host_url.rstrip("/")
    static_paths = ["/", "/app", "/terms", "/privacy", "/contact"]
    seo_slugs = [p.stem for p in SEO_DIR.glob("*.yaml")]

    urls = []
    for path in static_paths:
        urls.append(f"  <url><loc>{base}{path}</loc></url>")
    for slug in sorted(seo_slugs):
        urls.append(f"  <url><loc>{base}/for/{slug}</loc></url>")

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return Response(xml, mimetype="application/xml")


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


JSON_AGENTS = {"extractor", "classifier", "evaluator", "diagram-as-is", "diagram-improved"}


def repair_json_response(text: str) -> str:
    """Strip markdown fences and repair malformed JSON from model output."""
    import re
    from json_repair import repair_json

    text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    return repair_json(text, return_objects=False)


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
        text = response.text
        if agent in JSON_AGENTS:
            text = repair_json_response(text)
        return jsonify({"text": text})
    except Exception as e:
        app.logger.exception("invoke error")
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf", methods=["POST"])
def generate_pdf():
    try:
        from weasyprint import HTML

        import re

        data = request.json
        diagram_asis = data.get("diagram_asis", "")
        diagram_improved = data.get("diagram_improved", "")
        report = data.get("report", "")
        business_type = data.get("business_type", "")
        process_name = data.get("process_name", "")

        def normalize_svg(svg):
            """Strip fixed width/height so CSS can control the size."""
            if not svg:
                return svg
            svg = re.sub(r'\s+width="[^"]*"', '', svg, count=1)
            svg = re.sub(r'\s+height="[^"]*"', '', svg, count=1)
            if 'preserveAspectRatio' not in svg:
                svg = svg.replace('<svg', '<svg preserveAspectRatio="xMidYMid meet"', 1)
            return svg

        diagram_asis = normalize_svg(diagram_asis)
        diagram_improved = normalize_svg(diagram_improved)

        report_html = render_report_html(report)

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  @page {{ size: A4; margin: 1.5cm; }}
  @page diagram {{ size: A4 landscape; margin: 1cm; }}

  /* ── base ─────────────────────────────────────────────────── */
  body {{
    font-family: DejaVu Sans, sans-serif;
    font-size: 10pt;
    line-height: 1.55;
    color: #1f2937;
    margin: 0;
  }}

  /* ── cover / diagram pages ────────────────────────────────── */
  h1 {{ font-size: 18pt; color: #1e1b4b; margin: 0 0 4pt; }}
  .meta {{ color: #6b7280; font-size: 10pt; margin-bottom: 24pt; }}
  .diagram-page {{ page: diagram; }}
  .diagram-page svg {{ width: 100%; height: 190mm; display: block; }}
  .diagram-page h2 {{ font-size: 12pt; color: #4338ca; margin: 0 0 8pt;
                      border-bottom: 1px solid #e0e7ff; padding-bottom: 4pt; }}

  /* ── report section headings ──────────────────────────────── */
  .report-body h2 {{
    font-size: 11pt;
    font-weight: 700;
    color: #4338ca;
    margin: 18pt 0 5pt;
    padding-bottom: 3pt;
    border-bottom: 1px solid #e0e7ff;
    page-break-after: avoid;
  }}
  .report-body h3 {{
    font-size: 10.5pt;
    font-weight: 600;
    color: #374151;
    margin: 12pt 0 4pt;
    page-break-after: avoid;
  }}
  .report-body h4 {{
    font-size: 10pt;
    font-weight: 600;
    color: #374151;
    margin: 8pt 0 3pt;
    page-break-after: avoid;
  }}
  .report-body p {{
    margin: 0 0 6pt;
  }}
  .report-body code {{
    font-family: DejaVu Sans Mono, monospace;
    font-size: 8.5pt;
    background: #f3f4f6;
    padding: 1pt 3pt;
    border-radius: 2pt;
  }}

  /* ── tables ───────────────────────────────────────────────── */
  .report-body table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 9pt;
    margin: 6pt 0 10pt;
    page-break-inside: auto;
  }}
  .report-body th {{
    background: #4338ca;
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    padding: 5pt 7pt;
    border: 1px solid #4338ca;
  }}
  .report-body td {{
    padding: 4pt 7pt;
    border: 1px solid #e5e7eb;
    vertical-align: top;
  }}
  .report-body tr:nth-child(even) td {{
    background: #f9fafb;
  }}
  .report-body tr.rec-row td {{
    background: #f0fdf4;
    color: #166534;
    font-size: 8.5pt;
    padding: 3pt 7pt 3pt 14pt;
    border-top: none;
  }}
  .rec-arrow {{
    color: #16a34a;
    font-weight: 700;
  }}

  /* ── standalone → recommendation blocks ──────────────────── */
  .rec {{
    background: #f0fdf4;
    border-left: 3pt solid #16a34a;
    padding: 5pt 8pt;
    margin: 4pt 0 8pt;
    font-size: 9pt;
    color: #166534;
  }}
  .rec-line {{ margin: 1pt 0; }}

  /* ── key-value definition blocks (Action / Tool / etc.) ──── */
  .kv-block {{
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 4pt;
    padding: 7pt 10pt;
    margin: 6pt 0 10pt;
    font-size: 9.5pt;
  }}
  .kv {{ display: block; margin: 2pt 0; }}
  .kv-key {{
    font-weight: 700;
    color: #374151;
    min-width: 110pt;
    display: inline-block;
  }}
  .kv-val {{ color: #1f2937; }}

  /* ── health rating ────────────────────────────────────────── */
  .health {{
    font-size: 11pt;
    font-weight: 700;
    margin: 4pt 0 8pt;
  }}

  /* ── lists ────────────────────────────────────────────────── */
  .report-body ul, .report-body ol {{
    margin: 4pt 0 8pt 16pt;
    padding: 0;
  }}
  .report-body li {{ margin: 2pt 0; }}

  /* ── legend / verdicts line ───────────────────────────────── */
  .legend {{
    font-size: 8.5pt;
    color: #6b7280;
    margin: 2pt 0 6pt;
  }}

  /* ── vertical spacing ─────────────────────────────────────── */
  .vspace {{ height: 6pt; }}

</style></head><body>
  <h1>Operational Assessment</h1>
  <div class="meta">{business_type}{' · ' + process_name if process_name else ''}</div>

  <div class="diagram-page">
    <h2>Current Process Flow</h2>
    {diagram_asis if diagram_asis else '<p style="color:#9ca3af">No diagram available.</p>'}
  </div>

  <div class="diagram-page">
    <h2>Improved Process Flow</h2>
    {diagram_improved if diagram_improved else '<p style="color:#9ca3af">No diagram available.</p>'}
  </div>

  <div class="report-body">
    {report_html}
  </div>
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


@app.route("/api/contact", methods=["POST"])
def save_contact():
    try:
        data = request.json
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO contact_messages (id, name, email, subject, message, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    data.get("name", ""),
                    data.get("email", ""),
                    data.get("subject", ""),
                    data.get("message", ""),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        app.logger.exception("contact error")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
