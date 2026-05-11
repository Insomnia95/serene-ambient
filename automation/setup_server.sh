#!/bin/bash
# Calm Veritas — Server Setup Script
# Run once on DigitalOcean server to set up full automation
# Usage: bash automation/setup_server.sh YOUR_FREESOUND_TOKEN

set -e

REPO_DIR="/root/serene"
FREESOUND_TOKEN="${1:-}"

echo "=== Calm Veritas Server Setup ==="

# ── 1. Environment variables ──────────────────────────────────────────────────
echo "[1/4] Setting environment variables..."
cat >> /etc/environment << EOF
FREESOUND_TOKEN=${FREESOUND_TOKEN}
CALM_VERITAS_REPO=${REPO_DIR}
SERENE_TOKEN=/root/serene_token.json
SERENE_SECRETS=/root/client_secrets.json
EOF
export FREESOUND_TOKEN="${FREESOUND_TOKEN}"
export CALM_VERITAS_REPO="${REPO_DIR}"
export SERENE_TOKEN="/root/serene_token.json"
export SERENE_SECRETS="/root/client_secrets.json"
echo "  ✓ Environment variables set"

# ── 2. Install dependencies ───────────────────────────────────────────────────
echo "[2/4] Installing dependencies..."
apt-get install -y ffmpeg python3 python3-pip git -q
pip3 install google-api-python-client google-auth-oauthlib --break-system-packages -q
echo "  ✓ Dependencies installed"

# ── 3. Create systemd service for daemon ─────────────────────────────────────
echo "[3/4] Creating systemd service..."
cat > /etc/systemd/system/calm-veritas.service << EOF
[Unit]
Description=Calm Veritas Server Daemon
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${REPO_DIR}
Environment="FREESOUND_TOKEN=${FREESOUND_TOKEN}"
Environment="CALM_VERITAS_REPO=${REPO_DIR}"
Environment="SERENE_TOKEN=/root/serene_token.json"
Environment="SERENE_SECRETS=/root/client_secrets.json"
ExecStart=/usr/bin/python3 ${REPO_DIR}/automation/server_daemon.py
Restart=always
RestartSec=30
StandardOutput=append:/var/log/calm-veritas.log
StandardError=append:/var/log/calm-veritas.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable calm-veritas
systemctl start calm-veritas
echo "  ✓ Service installed and started"

# ── 4. Set up daily git pull (so daemon sees new queue items from GitHub) ─────
echo "[4/4] Setting up hourly git pull cron..."
(crontab -l 2>/dev/null; echo "*/30 * * * * cd ${REPO_DIR} && git pull --rebase --autostash >> /var/log/calm-veritas-pull.log 2>&1") | crontab -
echo "  ✓ Cron set (git pull every 30 min)"

echo ""
echo "=== Setup complete ==="
echo "  Daemon status: systemctl status calm-veritas"
echo "  Live logs:     journalctl -u calm-veritas -f"
echo "  Or:            tail -f /var/log/calm-veritas.log"
