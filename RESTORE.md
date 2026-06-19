# Krakow — Restore Guide

Complete steps to rebuild this project on a fresh SBC.

## Hardware Target
- Orange Pi Zero 3 (or compatible ARM64 SBC)
- 1.5GB+ RAM recommended
- Debian Bookworm (ARM64)

---

## Step 1 — Flash & First Boot

1. Flash **Debian Bookworm ARM64** to SD card (use official Orange Pi image or Armbian)
2. Boot, SSH in as `orangepi`
3. Set hostname to `krakow`:
   ```bash
   sudo hostnamectl set-hostname krakow
   ```
4. Set up SSH key auth (optional but recommended):
   ```bash
   ssh-copy-id orangepi@<ip>
   ```

---

## Step 2 — Clone the Repo

```bash
sudo apt update && sudo apt install -y git python3-pip
# On recent Bookworm images the apt 'ansible' package has broken deps
# (it pulls an old python3 that conflicts with the installed Python 3.13).
# Install Ansible via pip instead:
pip3 install ansible --break-system-packages
export PATH="$HOME/.local/bin:$PATH"   # so 'ansible-playbook' is on PATH

git clone https://github.com/KailenCodes/orangepi-k3s-lab.git ~/orangepi-k3s-lab
cd ~/orangepi-k3s-lab
```

---

## Step 3 — Run the Bootstrap Playbook

This installs everything: swap, log2ram, K3s, Flux CLI, Python packages, the scanner service, and crontab.

**Run locally on the SBC:**
```bash
ansible-playbook -i "localhost," -c local bootstrap.yml --ask-become-pass
```

**Or run remotely from another machine** (update `hosts.ini` with the SBC's IP first):
```bash
ansible-playbook -i hosts.ini bootstrap.yml --ask-become-pass
```

The playbook will reboot once if it needs to update boot config for cgroup support — then re-run it. On completion it prints the dashboard URL.

---

## Step 4 — Deploy the Dashboard App

The K3s manifests are applied automatically by the bootstrap playbook. Verify:

```bash
kubectl get pods -A
kubectl get svc -A
```

The dashboard is accessible at `http://<ip>:30080`. Find the Pi's current IP with:

```bash
hostname -I        # the dashboard is on the first address, port 30080
```

**No image build is required.** The dashboard runs stock `nginx:alpine` and serves
the files in `app/` directly via a hostPath mount, so updating the UI is just:

```bash
cd ~/orangepi-k3s-lab && git pull
# refresh the browser — nginx serves app/index.html live, no rebuild/rollout
```

---

## Step 5 — Verify Services

```bash
# K3s
sudo systemctl status k3s
kubectl get nodes

# Network scanner (writes app/network_data.json every 5s, incl. cluster stats)
sudo systemctl status krakow-scanner
cat ~/orangepi-k3s-lab/app/network_data.json | head
```

---

## What the Bootstrap Installs

| Component | Method | Notes |
|-----------|--------|-------|
| Swap (2GB) | Ansible | swappiness=10 |
| log2ram | Shell installer | SIZE=128M |
| K3s | get.k3s.io script | traefik + metrics-server disabled |
| Flux CLI | fluxcd.io installer | For GitOps manifests |
| psutil | pip (`--break-system-packages`) | Required by scanner.py; apt version conflicts with Python 3.13 |
| krakow-scanner | systemd service | Runs scanner.py every 5s (network + cluster stats) |
| Dashboard | `nginx:alpine` + hostPath | Serves `app/` directly — no custom image to build |

---

## Secrets / Sensitive Config

The following are **not stored in this repo** and must be set up manually:
- SSH keys / authorized_keys
- GitHub deploy keys (if using private registry)
- Any API keys used by apps

---

## Repo Structure

```
orangepi-k3s-lab/
├── app/                    # Dashboard web app + network scanner
│   ├── scanner.py          # Network stats collector (runs via krakow-scanner.service)
│   ├── run_scanner.sh      # Loop wrapper for scanner.py
│   ├── index.html          # Dashboard frontend
│   ├── app.css             # Dashboard styles
│   └── Dockerfile          # Builds the nginx container image
├── cluster/
│   ├── my-app/             # K3s manifests for the dashboard
│   └── flux-system/        # Flux GitOps components
├── ansible_project/        # Modular Ansible roles (k3s, tailscale, etc.)
├── bootstrap.yml           # Main provisioning playbook (start here)
├── optimize_pi.yml         # Standalone swap/stability playbook
├── krakow-scanner.service  # systemd unit file for the scanner
├── stats.sh                # Outputs cluster stats JSON for dashboard
└── hosts.ini               # Ansible inventory (update IP before remote use)
```
