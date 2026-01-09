# The start of day2..

## goals
- set up tailscale for full remote connectivity
- set up ansible images and create playbooks to automate anything I install
- set up docker maybe

## Completed
- tailscale set up using ssh keys, further steps will include automating the installation
with a playbook.
- Autmated idempotent and headless tailscale playbook using artis3n.tailscale due to it's
auto detecting OS, adding GPG keys and managing the service state.
- created an ansible vault to store my tailscale Auth key so it does not leak to the public
- Fully deployed homelab CI/CD using self hosted github-runner, the orangepi is now a "worker" that will listen to commands from github repo
- Created the pipeline so that git push triggers updates immediately
- built deploy.yml, tells github how to run Ansible Playbook
- gave orangepi passwordless access for true automation using visudo

## Challenges I Ran into
- I accidentally pushed a runner software to github which was very large and had to 'git rm --cached' to stop git from tracking the files, then added them to .gitignore so git wouldnt see it and git reset to get rid of the mistake from history.
