import socket
import json
import psutil
import time
import struct
import os

OUTPUT_PATH = '/home/orangepi/orangepi-k3s-lab/app/network_data.json'

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_active_interface(local_ip):
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address == local_ip:
                return iface
    return 'eth0'

def get_mac(iface):
    addrs = psutil.net_if_addrs().get(iface, [])
    for addr in addrs:
        if addr.family == psutil.AF_LINK:
            return addr.address
    return 'N/A'

def get_gateway():
    try:
        with open('/proc/net/route') as f:
            for line in f.readlines()[1:]:
                parts = line.strip().split()
                if len(parts) >= 3 and parts[1] == '00000000':
                    gateway = socket.inet_ntoa(struct.pack('<I', int(parts[2], 16)))
                    return gateway
    except Exception:
        pass
    return 'N/A'

def scan_ports(local_ip):
    open_ports = []
    target_ports = [22, 80, 443, 3000, 6443, 8080, 8443, 30080]
    for port in target_ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        if s.connect_ex((local_ip, port)) == 0:
            open_ports.append({"port": port, "status": "OPEN"})
        s.close()
    return open_ports

# Load previous data for bandwidth delta calculation
prev_bytes_sent = 0
prev_bytes_recv = 0
prev_timestamp = None
prev_history = []

if os.path.exists(OUTPUT_PATH):
    try:
        with open(OUTPUT_PATH) as f:
            prev_data = json.load(f)
        prev_bytes_sent = prev_data.get('traffic', {}).get('bytes_sent', 0)
        prev_bytes_recv = prev_data.get('traffic', {}).get('bytes_recv', 0)
        prev_timestamp = prev_data.get('timestamp')
        prev_history = prev_data.get('history', [])
    except Exception:
        pass

# Take measurements
current_timestamp = time.time()
uptime_seconds = current_timestamp - psutil.boot_time()
net_io = psutil.net_io_counters()

# Calculate bandwidth speeds
upload_speed = 0
download_speed = 0
if prev_timestamp:
    elapsed = current_timestamp - prev_timestamp
    if elapsed > 0:
        upload_speed = max(0, (net_io.bytes_sent - prev_bytes_sent) / elapsed)
        download_speed = max(0, (net_io.bytes_recv - prev_bytes_recv) / elapsed)

local_ip = get_local_ip()
iface = get_active_interface(local_ip)

# Append to rolling history (last 40 points)
prev_history.append({
    "t": int(current_timestamp),
    "up": round(upload_speed),
    "down": round(download_speed)
})
history = prev_history[-40:]

data = {
    "timestamp": current_timestamp,
    "system": {
        "ip": local_ip,
        "hostname": socket.gethostname(),
        "os": "Debian Bookworm / K3s",
        "uptime": uptime_seconds
    },
    "resources": {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_used": psutil.virtual_memory().used,
        "memory_total": psutil.virtual_memory().total,
        "cpu_cores": psutil.cpu_count()
    },
    "traffic": {
        "bytes_sent": net_io.bytes_sent,
        "bytes_recv": net_io.bytes_recv,
        "packets_sent": net_io.packets_sent,
        "packets_recv": net_io.packets_recv
    },
    "bandwidth": {
        "upload_speed": round(upload_speed),
        "download_speed": round(download_speed)
    },
    "connections": {
        "total": len(psutil.net_connections())
    },
    "processes": {
        "active": len(psutil.pids())
    },
    "scan_results": scan_ports(local_ip),
    "network": {
        "status": "online",
        "interface": iface,
        "mac": get_mac(iface),
        "gateway": get_gateway()
    },
    "history": history
}

with open(OUTPUT_PATH, 'w') as f:
    json.dump(data, f, indent=4)
