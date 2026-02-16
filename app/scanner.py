import socket
import json
import psutil
import time

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

def scan_network():
    local_ip = get_local_ip()
    open_ports = []
    # 22 (SSH), 80 (HTTP), 6443 (K3s API), 8080 (Common Web)
    target_ports = [22, 80, 443, 6443, 8080] 
    
    for port in target_ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        if s.connect_ex((local_ip, port)) == 0:
            open_ports.append({"port": port, "status": "OPEN"})
        s.close()
    return open_ports

# Gather real system stats for the Krakow dashboard
uptime_seconds = time.time() - psutil.boot_time()
net_io = psutil.net_io_counters()

data = {
    "system": {
        "ip": get_local_ip(),
        "hostname": socket.gethostname(),
        "os": "Armbian / K3s",
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
    "connections": {
        "total": len(psutil.net_connections())
    },
    "scan_results": scan_network(),
    "network": {"status": "online", "interface": "eth0"}
}


with open('/orangepi-k3s-lab/app/network_data.json', 'w') as f:
    json.dump(data, f, indent=4)
