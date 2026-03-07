# Fractional COO — Process Analyzer

A Flask web app that runs a 7-stage AI pipeline to audit small business workflows. It interviews a business owner, extracts and evaluates process steps, renders flow diagrams, and produces a downloadable PDF report.

## How it works

1. **Setup** — enter business type, weekly volume, process name, tools/channels, and email
2. **Interview** — live AI-driven chat, or paste an existing transcript
3. **Extract** — AI parses the transcript into discrete process steps
4. **Classify** — each step is annotated with quality rating, failure modes, and automation potential
5. **Evaluate** — steps receive keep / improve / replace / automate verdicts with ROI estimates
6. **Diagrams** — two SVG flow diagrams rendered in the browser (as-is and improved)
7. **Report** — written assessment generated; download as a single A4 PDF

Sessions (transcript, diagrams, report, email) are saved automatically to a local SQLite database.

## Requirements

- Python 3.11+
- A [Gemini API key](https://aistudio.google.com/app/apikey) (free tier works)
- `fonts-noto-color-emoji` for emoji in PDFs (Debian/Ubuntu only)

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your GEMINI_API_KEY and ADMIN_KEY
flask run
```

Open `http://localhost:5000`.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Gemini API key from Google AI Studio |
| `ADMIN_KEY` | Yes | Password for the `/admin` panel |

## Admin panel

All completed sessions are accessible at `/admin`. The browser will prompt for HTTP Basic Auth — use any username and `ADMIN_KEY` as the password.

Each session shows the full interview transcript, both flow diagrams, and the assessment report.

## Deploying to a VPS (Digital Ocean, Hetzner, etc.)

### First-time setup

```bash
# On the server, as root:
bash deploy/setup.sh yourdomain.com https://github.com/yourrepo/operations-audit

# Fill in secrets:
nano /srv/operations-audit/.env

# Start the app:
systemctl start operations-audit
```

`setup.sh` installs system packages, creates a virtualenv, configures Nginx as a reverse proxy, and obtains a free SSL certificate via Certbot.

### Subsequent deploys

```bash
bash /srv/operations-audit/deploy/update.sh
```

Pulls latest code, reinstalls dependencies, and restarts the service.

### What's in `deploy/`

| File | Purpose |
|---|---|
| `setup.sh` | One-time server provisioning |
| `update.sh` | Pull + restart for future deploys |
| `operations-audit.service` | systemd unit (auto-restart on crash/reboot) |
| `nginx.conf` | Reverse proxy config; SSE buffering disabled for the interview stream |

## Architecture

```
templates/index.html   — single-page frontend (Tailwind CDN, vanilla JS)
app.py                 — Flask routes + SQLite session storage
agents/*.md            — system prompts for each pipeline stage
sessions.db            — SQLite database (created on first run)
```

### Routes

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Frontend |
| `/api/chat` | POST | SSE stream for the interview agent |
| `/api/invoke` | POST | Non-streaming pipeline agents |
| `/api/pdf` | POST | Generate PDF |
| `/api/session` | POST | Save a completed session |
| `/admin` | GET | Session list (Basic Auth) |
| `/admin/<id>` | GET | Session detail (Basic Auth) |
