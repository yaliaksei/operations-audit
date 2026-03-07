#!/usr/bin/env bash
# Pull latest code and restart. Run from any directory.
set -euo pipefail

APP_DIR="/srv/operations-audit"

cd "$APP_DIR"
git pull
"$APP_DIR/.venv/bin/pip" install -q -r requirements.txt
systemctl restart operations-audit
echo "Deployed. Status:"
systemctl status operations-audit --no-pager -l
