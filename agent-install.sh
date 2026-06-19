#!/usr/bin/env bash
# Krakow — remote node agent installer.
#
# Run this ON the node you want to MONITOR (e.g. your test/recon Pi). It installs
# only the metrics scanner + a systemd service that pushes this node's stats to
# the dashboard Pi over SSH. It does NOT install K3s and won't touch your tools.
#
# Usage:
#   bash agent-install.sh <user@dashboard-ip> [node-id] ["Node Label"]
# Example:
#   bash agent-install.sh orangepi@192.168.8.135 recon "Recon — Test Node"
set -euo pipefail

DASH_HOST="${1:-}"
NODE_ID="${2:-$(hostname)}"
NODE_LABEL="${3:-$NODE_ID}"

if [ -z "$DASH_HOST" ]; then
  echo "Usage: bash agent-install.sh <user@dashboard-ip> [node-id] [\"Node Label\"]"
  echo "Example: bash agent-install.sh orangepi@192.168.8.135 recon \"Recon — Test Node\""
  exit 1
fi

REPO_URL="https://github.com/KailenCodes/orangepi-k3s-lab.git"
REPO_DIR="$HOME/orangepi-k3s-lab"
APP_DIR="$REPO_DIR/app"

echo ">> Installing dependencies (git, rsync, psutil)…"
sudo apt-get update -qq
sudo apt-get install -y git rsync python3-pip >/dev/null
pip3 install psutil --break-system-packages >/dev/null 2>&1 || pip3 install psutil >/dev/null

echo ">> Fetching the repo…"
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" pull --ff-only || true
else
  git clone "$REPO_URL" "$REPO_DIR"
fi

echo ">> Setting up a passwordless SSH key to the dashboard Pi ($DASH_HOST)…"
[ -f "$HOME/.ssh/id_ed25519" ] || ssh-keygen -t ed25519 -N "" -f "$HOME/.ssh/id_ed25519"
echo "   (you'll be asked for the dashboard Pi's password once)"
ssh-copy-id -o StrictHostKeyChecking=accept-new "$DASH_HOST" || true

# If this node previously had the full monitor installed by mistake, stop its
# local scanner so the agent is the only thing running here.
sudo systemctl disable --now krakow-scanner 2>/dev/null || true

echo ">> Installing the krakow-agent service…"
PUSH_TARGET="${DASH_HOST}:${REPO_DIR}/app/data/"
sudo tee /etc/systemd/system/krakow-agent.service >/dev/null <<EOF
[Unit]
Description=Krakow Monitor Agent ($NODE_ID)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
Environment=KRAKOW_NODE_ID=$NODE_ID
Environment=KRAKOW_NODE_LABEL=$NODE_LABEL
Environment=KRAKOW_NODE_ROLE=test
Environment=KRAKOW_PUSH_TARGET=$PUSH_TARGET
ExecStart=/bin/bash $APP_DIR/run_scanner.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now krakow-agent

echo ""
echo ">> Done. Node '$NODE_ID' is now pushing metrics to $DASH_HOST every 5s."
echo "   Make sure it's listed in app/data/nodes.json on the dashboard Pi:"
echo "       { \"id\": \"$NODE_ID\", \"label\": \"$NODE_LABEL\", \"role\": \"test\" }"
echo "   Check it with:  systemctl status krakow-agent"
