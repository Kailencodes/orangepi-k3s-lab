#!/usr/bin/env bash
# Krakow — teardown / uninstall
#
# Removes everything bootstrap.yml installed:
#   - the krakow-scanner systemd service
#   - the scanner cron jobs (if an old bootstrap left them)
#   - K3s itself, which also removes the deployed dashboard (my-app)
#   - the Flux CLI, the user kubeconfig, and the shell aliases
#
# Swap, log2ram and the cgroup boot args are generic board tweaks and are left
# in place by default. Pass --deep to remove those too.
#
# Usage:   bash uninstall.sh           # remove the project
#          bash uninstall.sh --deep    # also undo swap/log2ram/cgroup tweaks
set -uo pipefail

echo ">> Stopping and removing the krakow-scanner service…"
sudo systemctl disable --now krakow-scanner 2>/dev/null || true
sudo rm -f /etc/systemd/system/krakow-scanner.service
sudo systemctl daemon-reload 2>/dev/null || true

echo ">> Removing scanner/stats cron jobs…"
( crontab -l 2>/dev/null | grep -vE 'scanner\.py|stats\.sh|Ansible: (krakow|cluster)' ) | crontab - 2>/dev/null || true

echo ">> Uninstalling K3s (this also removes the deployed dashboard)…"
if [ -x /usr/local/bin/k3s-uninstall.sh ]; then
  sudo /usr/local/bin/k3s-uninstall.sh
else
  echo "   k3s-uninstall.sh not found — K3s already gone, skipping."
fi

echo ">> Removing Flux CLI, kube config and shell aliases…"
sudo rm -f /usr/local/bin/flux
rm -rf "$HOME/.kube"
sed -i '/# BEGIN ANSIBLE MANAGED ALIASES/,/# END ANSIBLE MANAGED ALIASES/d' "$HOME/.bashrc" 2>/dev/null || true

if [ "${1:-}" = "--deep" ]; then
  echo ">> Deep clean: swap, log2ram and cgroup boot args…"
  sudo swapoff /swapfile 2>/dev/null || true
  sudo sed -i '\#/swapfile#d' /etc/fstab 2>/dev/null || true
  sudo rm -f /swapfile
  sudo systemctl disable --now log2ram 2>/dev/null || true
  sudo rm -f /etc/systemd/system/log2ram* /usr/local/bin/log2ram /etc/log2ram.conf 2>/dev/null || true
  sudo systemctl daemon-reload 2>/dev/null || true
  for f in /boot/orangepiEnv.txt /boot/armbianEnv.txt; do
    [ -f "$f" ] && sudo sed -i 's/ cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1//' "$f"
  done
fi

echo ""
echo ">> Teardown complete."
echo "   The only thing left is this repo folder. Remove it with:"
echo "       rm -rf ~/orangepi-k3s-lab"
