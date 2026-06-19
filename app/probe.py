#!/usr/bin/env python3
"""Krakow fleet probes — monitor devices that can't run the agent.

Reads app/data/nodes.json and, for every entry with kind == "probe", pings its
target (with a TCP-connect fallback for ICMP-filtered hosts like Windows) and
port-scans it, writing app/data/<id>.json. Runs on the monitor Pi via the
krakow-probes service. This is how the router and (optionally) the desktop get
onto the fleet view without installing anything on them.
"""

import json
import os
import re
import socket
import subprocess
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
NODES_FILE = os.path.join(DATA_DIR, "nodes.json")
HISTORY_POINTS = 40
SCAN_PORTS = (22, 53, 80, 443, 445, 3389, 8080, 8443)
FALLBACK_PORTS = (443, 80, 22, 445, 3389, 53)


def ping(target):
    """Return {status, latency_ms, packet_loss}. Falls back to a TCP connect if
    ICMP looks blocked, so firewalled hosts still register as online."""
    latency, loss = None, 100.0
    try:
        out = subprocess.run(
            ["ping", "-c", "2", "-i", "0.3", "-W", "1", target],
            capture_output=True, text=True, timeout=8,
        ).stdout
        m = re.search(r"(\d+(?:\.\d+)?)% packet loss", out)
        if m:
            loss = float(m.group(1))
        m = re.search(r"=\s*[\d.]+/([\d.]+)/", out)  # rtt min/avg/max/mdev
        if m:
            latency = float(m.group(1))
    except Exception:
        pass

    if loss < 100.0:
        return {"status": "online", "latency_ms": round(latency or 0, 1), "packet_loss": loss}

    # ICMP failed/blocked — try a TCP handshake to common ports.
    for port in FALLBACK_PORTS:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        t0 = time.time()
        try:
            if s.connect_ex((target, port)) == 0:
                return {"status": "online", "latency_ms": round((time.time() - t0) * 1000, 1), "packet_loss": 0.0}
        except Exception:
            pass
        finally:
            s.close()
    return {"status": "offline", "latency_ms": 0, "packet_loss": 100.0}


def scan_ports(target):
    res = []
    for port in SCAN_PORTS:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        try:
            if s.connect_ex((target, port)) == 0:
                res.append({"port": port, "status": "OPEN"})
        except Exception:
            pass
        finally:
            s.close()
    return res


def load_prev(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def atomic_write(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def main():
    try:
        with open(NODES_FILE) as f:
            nodes = json.load(f)
    except Exception:
        return

    now = time.time()
    for n in nodes:
        if n.get("kind") != "probe" or not n.get("target"):
            continue
        target = n["target"]
        out_path = os.path.join(DATA_DIR, n["id"] + ".json")
        prev = load_prev(out_path)

        result = ping(target)
        history = prev.get("history", [])
        history.append({"t": int(now), "latency": result["latency_ms"]})
        history = history[-HISTORY_POINTS:]

        atomic_write(out_path, {
            "timestamp": now,
            "node": {
                "id": n["id"],
                "label": n.get("label", n["id"]),
                "role": n.get("role", "device"),
                "kind": "probe",
            },
            "probe": {"target": target, **result},
            "scan_results": scan_ports(target) if result["status"] == "online" else [],
            "history": history,
        })


if __name__ == "__main__":
    main()
