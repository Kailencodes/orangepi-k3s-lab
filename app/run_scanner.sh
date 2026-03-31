#!/bin/bash
# Krakow scanner loop — runs scanner.py every 5 seconds
while true; do
    python3 /home/orangepi/orangepi-k3s-lab/app/scanner.py
    sleep 5
done
