#!/usr/bin/env bash
# First-time server setup. Run once as root on the droplet.
# Usage: bash deploy/setup.sh [domain]  (defaults to flownext.co)
set -euo pipefail

DOMAIN="${1:-flownext.co}"
APP_DIR="/srv/operations-audit"
REPO="${2:-}"  # optional: git remote URL

# ── System packages ────────────────────────────────────────────────
apt-get update -qq
apt-get install -y -qq \
    python3-pip python3-venv \
    nginx certbot python3-certbot-nginx \
    fonts-noto-color-emoji \
    git

# ── App directory ──────────────────────────────────────────────────
if [ -n "$REPO" ]; then
    git clone "$REPO" "$APP_DIR"
else
    echo "No repo URL given — assuming $APP_DIR already exists."
fi

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo ""
    echo "  !! Edit $APP_DIR/.env and fill in GEMINI_API_KEY and ADMIN_KEY before starting the service."
    echo ""
fi

chown -R www-data:www-data "$APP_DIR"

# ── Logs ───────────────────────────────────────────────────────────
mkdir -p /var/log/operations-audit
chown www-data:www-data /var/log/operations-audit

# ── systemd ────────────────────────────────────────────────────────
cp "$APP_DIR/deploy/operations-audit.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable operations-audit

# ── Nginx ─────────────────────────────────────────────────────────
sed "s/YOUR_DOMAIN/$DOMAIN/" "$APP_DIR/deploy/nginx.conf" \
    > /etc/nginx/sites-available/operations-audit
ln -sf /etc/nginx/sites-available/operations-audit \
       /etc/nginx/sites-enabled/operations-audit
nginx -t
systemctl reload nginx

# ── SSL ────────────────────────────────────────────────────────────
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    --email "admin@$DOMAIN" --redirect

# ── Start ──────────────────────────────────────────────────────────
systemctl start operations-audit

echo ""
echo "Done. App running at https://$DOMAIN"
echo "Admin panel: https://$DOMAIN/admin"
