#!/bin/bash
# Krakow fleet probes loop — runs probe.py every 5 seconds on the monitor Pi.
# probe.py reads app/data/nodes.json and writes a JSON file for each kind=="probe"
# node (router, desktop, …) that can't run the agent itself.
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

while true; do
    python3 "$APP_DIR/probe.py"
    sleep 5
done
