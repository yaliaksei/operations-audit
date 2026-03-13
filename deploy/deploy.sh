#!/usr/bin/env bash
# Push local changes and deploy to the droplet.
# Usage: bash deploy/deploy.sh
set -euo pipefail

REMOTE="${1:-origin}"
BRANCH="${2:-main}"
HOST="root@flownext.co"

git push "$REMOTE" "$BRANCH"
ssh "$HOST" 'bash /srv/operations-audit/deploy/update.sh'
