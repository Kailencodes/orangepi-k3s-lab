#!/bin/bash
# Krakow scanner loop — runs scanner.py every 5 seconds.
#
# On the dashboard Pi it just writes app/data/<node-id>.json locally.
# On a remote node, set KRAKOW_PUSH_TARGET (e.g. user@dash-ip:/path/app/data/)
# and each cycle's JSON is rsync'd to the dashboard Pi so it appears on the
# fleet view. Env (KRAKOW_NODE_ID / LABEL / ROLE / PUSH_TARGET) comes from the
# systemd unit.
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
NODE_ID="${KRAKOW_NODE_ID:-$(hostname)}"

while true; do
    python3 "$APP_DIR/scanner.py"
    if [ -n "${KRAKOW_PUSH_TARGET:-}" ]; then
        rsync -az --timeout=8 "$APP_DIR/data/${NODE_ID}.json" "$KRAKOW_PUSH_TARGET" 2>/dev/null || true
    fi
    sleep 5
done
