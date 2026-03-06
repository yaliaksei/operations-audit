# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Flask web app ("Fractional COO") that runs a 7-stage AI pipeline to audit small business workflows. It interviews a business owner, extracts process steps, classifies and evaluates them, produces flow diagrams, and generates a downloadable PDF report.

## Running It

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# copy .env.example to .env and fill in GEMINI_API_KEY
flask run
```

Then open `http://localhost:5000`.

For production: `gunicorn app:app -w 4 -k gevent --worker-connections 50`

## Architecture

### Files

- `app.py` — Flask app with three routes: `/`, `/api/chat` (SSE streaming), `/api/invoke` (JSON), `/api/pdf`
- `templates/index.html` — single-page frontend (Tailwind CDN, vanilla JS)
- `agents/*.md` — system prompts for each pipeline agent

### API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Serve the frontend |
| `/api/chat` | POST | SSE stream for interview agent. Body: `{messages, agent}` |
| `/api/invoke` | POST | Non-streaming agent call. Body: `{agent, user_content, max_tokens}` |
| `/api/pdf` | POST | Generate PDF. Body: `{diagram_asis, diagram_improved, report, business_type, process_name}` |

### Agent Prompts (`agents/`)

| File | Role | Output |
|------|------|--------|
| `interviewer.md` | Socratic interview of the business owner | Conversational text |
| `extractor.md` | Parses transcript into discrete steps | JSON array |
| `classifier.md` | Annotates each step (quality, failure modes, automation potential, etc.) | JSON array |
| `evaluator.md` | Produces keep/improve/replace/automate verdicts with ROI math | JSON array |
| `synthesizer.md` | Writes the final assessment report | Plain text |
| `diagram-as-is.md` | Converts extracted steps to a graph for rendering | JSON `{nodes, edges}` |
| `diagram-improved.md` | Same as above but annotated with verdicts | JSON `{nodes, edges}` |

### Pipeline Stages (in order)

1. **Setup** — user fills in business context (type, volume, process name, tools/channels)
2. **Interview** — live chat with interviewer agent, or paste a transcript
3. **Extract** — extractor parses transcript → JSON steps
4. **Classify** — classifier annotates each step
5. **Evaluate** — evaluator produces verdicts and ROI estimates
6. **Diagrams** — two SVG flow diagrams rendered client-side (as-is and improved)
7. **Report** — synthesizer writes the assessment; **Download PDF** button combines both diagrams + report into a single A4 PDF via WeasyPrint

### PDF Generation

`POST /api/pdf` receives the SVG strings of both diagrams (extracted from the DOM) and the report text, builds an HTML document, and renders it to PDF with WeasyPrint. Emoji rendering requires `fonts-noto-color-emoji` on Debian/Ubuntu.

### Gemini Integration

- Model: `gemini-2.5-flash` (set via `MODEL` constant in `app.py`)
- `invoke` endpoint disables thinking (`thinking_budget=0`) since all pipeline agents need structured JSON output
- `chat` endpoint streams SSE in the same `{type: "content_block_delta", delta: {text}}` format the frontend already expects from the original Anthropic integration

## Key Conventions

- Agent prompts are the source of truth — pipeline logic passes agent names (e.g. `'extractor'`) to the backend, which loads `agents/<name>.md` at request time.
- The classifier and evaluator must output **only valid JSON arrays** (no markdown fences). The synthesizer outputs plain text.
- The evaluator uses `$0.25/min` time valuation and a 26-week payback threshold to decide whether to recommend paid tools.
- The interview opening question is generated dynamically from `state.processName` in `sendFirstQuestion()` — it is not in `interviewer.md`.
