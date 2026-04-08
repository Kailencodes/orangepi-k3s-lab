# Krakow — Orange Pi K3s Cluster

## Hardware
- Board: Orange Pi Zero 3 1.5gb ram
- OS: Debian Bookworm
- Architecture: ARM64

## Cluster
- K3s single-node
- Kubectl context: default
- Kubeconfig: ~/.kube/config

## Goals
- understand architecture already set up
- create network scripts to go on the web server dashboard
- finish the web server dashboard
- Finish K3s cluster configuration
- Deploy apps to the cluster


## Key Commands
- Check cluster: `kubectl get nodes`
- Check pods: `kubectl get pods -A`
- K3s status: `sudo systemctl status k3s`
- K3s logs: `sudo journalctl -u k3s -f`

## Notes
- Always check node resource limits before deploying (ARM64, limited RAM)
- Prefer lightweight images (alpine-based, distroless)
- Namespaces in use: (list them)
```
