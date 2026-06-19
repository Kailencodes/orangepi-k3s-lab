#!/usr/bin/env python3
"""Krakow node scanner.

Runs once per invocation (driven by run_scanner.sh on a 5s loop) and writes a
single JSON snapshot for THIS node into app/data/<node-id>.json. Every probe is
wrapped so a failure in one section never blocks the others, and the file is
written atomically with world-readable perms so the nginx pod (a different user,
via hostPath) and rsync can always read a complete file.

Multi-node: each node identifies itself via KRAKOW_NODE_ID (defaults to the
hostname). The dashboard Pi runs this directly; remote nodes run the same script
and rsync their <node-id>.json to the dashboard Pi's app/data/ dir.
"""

import json
import os
import socket
import struct
import subprocess
import time

import psutil

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")

NODE_ID = os.environ.get("KRAKOW_NODE_ID") or socket.gethostname()
NODE_LABEL = os.environ.get("KRAKOW_NODE_LABEL", NODE_ID)
NODE_ROLE = os.environ.get("KRAKOW_NODE_ROLE", "monitor")  # "monitor" | "test"
OUTPUT_PATH = os.path.join(DATA_DIR, NODE_ID + ".json")

KUBECTL = "/usr/local/bin/kubectl" if os.path.exists("/usr/local/bin/kubectl") else "kubectl"
KUBECONFIG = os.environ.get("KUBECONFIG", "/home/orangepi/.kube/config")
CLUSTER_REFRESH_SECS = 25
HISTORY_POINTS = 40


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def get_active_interface(local_ip):
    try:
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address == local_ip:
                    return iface
    except Exception:
        pass
    return "eth0"


def get_mac(iface):
    try:
        for addr in psutil.net_if_addrs().get(iface, []):
            if addr.family == psutil.AF_LINK:
                return addr.address
    except Exception:
        pass
    return "N/A"


def get_gateway():
    try:
        with open("/proc/net/route") as f:
            for line in f.readlines()[1:]:
                parts = line.strip().split()
                if len(parts) >= 3 and parts[1] == "00000000":
                    return socket.inet_ntoa(struct.pack("<I", int(parts[2], 16)))
    except Exception:
        pass
    return "N/A"


def get_os():
    """Report the actual distro so every host (Pis, desktop) reads correctly."""
    try:
        with open("/etc/os-release") as f:
            kv = dict(l.strip().split("=", 1) for l in f if "=" in l)
        name = kv.get("PRETTY_NAME", "").strip('"')
        if name:
            return name
    except Exception:
        pass
    try:
        import platform
        return f"{platform.system()} {platform.release()}".strip()
    except Exception:
        return "unknown"


def count_connections():
    """Count TCP sockets without root by reading /proc directly.

    psutil.net_connections() needs root to map sockets to PIDs; the scanner runs
    unprivileged, so we read the kernel tables instead.
    """
    total = 0
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(path) as f:
                total += max(0, len(f.readlines()) - 1)  # minus header row
        except Exception:
            pass
    return total


def scan_ports(local_ip):
    open_ports = []
    for port in (22, 80, 443, 3000, 6443, 8080, 8443, 30080):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        try:
            if s.connect_ex((local_ip, port)) == 0:
                open_ports.append({"port": port, "status": "OPEN"})
        except Exception:
            pass
        finally:
            s.close()
    return open_ports


def get_cluster_stats(prev_cluster):
    """Best-effort K3s stats via kubectl, throttled and cached. Returns None if
    kubectl has never succeeded — the dashboard renders that gracefully."""
    now = time.time()
    if prev_cluster and (now - prev_cluster.get("_ts", 0)) < CLUSTER_REFRESH_SECS:
        return prev_cluster

    env = dict(os.environ)
    env["KUBECONFIG"] = KUBECONFIG

    def run(args):
        return subprocess.run(
            [KUBECTL, *args], capture_output=True, text=True, timeout=8, env=env
        )

    try:
        nodes = run(["get", "nodes", "--no-headers"])
        node_lines = [l for l in nodes.stdout.splitlines() if l.strip()]
        pods = run(["get", "pods", "-A", "--no-headers"])
        pod_lines = [l for l in pods.stdout.splitlines() if l.strip()]
        return {
            "_ts": now,
            "reachable": bool(node_lines),
            "nodes_total": len(node_lines),
            "nodes_ready": sum(1 for l in node_lines if " Ready" in l),
            "pods_total": len(pod_lines),
            "pods_running": sum(1 for l in pod_lines if " Running" in l),
        }
    except Exception:
        return prev_cluster or {"_ts": now, "reachable": False}


def load_previous():
    if os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def atomic_write(path, payload):
    """Write then rename so readers never see a half-written file, with 0644
    perms so the nginx container and rsync can always read it."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def main():
    prev = load_previous()
    now = time.time()

    net_io = psutil.net_io_counters()
    upload_speed = download_speed = 0
    prev_ts = prev.get("timestamp")
    if prev_ts:
        elapsed = now - prev_ts
        if elapsed > 0:
            upload_speed = max(0, (net_io.bytes_sent - prev.get("traffic", {}).get("bytes_sent", net_io.bytes_sent)) / elapsed)
            download_speed = max(0, (net_io.bytes_recv - prev.get("traffic", {}).get("bytes_recv", net_io.bytes_recv)) / elapsed)

    local_ip = get_local_ip()
    iface = get_active_interface(local_ip)

    history = prev.get("history", [])
    history.append({"t": int(now), "up": round(upload_speed), "down": round(download_speed)})
    history = history[-HISTORY_POINTS:]

    vm = psutil.virtual_memory()
    data = {
        "timestamp": now,
        "node": {"id": NODE_ID, "label": NODE_LABEL, "role": NODE_ROLE},
        "system": {
            "ip": local_ip,
            "hostname": socket.gethostname(),
            "os": get_os(),
            "uptime": now - psutil.boot_time(),
        },
        "resources": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": vm.percent,
            "memory_used": vm.used,
            "memory_total": vm.total,
            "cpu_cores": psutil.cpu_count(),
        },
        "traffic": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
        },
        "bandwidth": {
            "upload_speed": round(upload_speed),
            "download_speed": round(download_speed),
        },
        "connections": {"total": count_connections()},
        "processes": {"active": len(psutil.pids())},
        "scan_results": scan_ports(local_ip),
        "network": {
            "status": "online",
            "interface": iface,
            "mac": get_mac(iface),
            "gateway": get_gateway(),
        },
        "cluster": get_cluster_stats(prev.get("cluster")) if NODE_ROLE == "monitor" else None,
        "history": history,
    }

    atomic_write(OUTPUT_PATH, data)


if __name__ == "__main__":
    main()
