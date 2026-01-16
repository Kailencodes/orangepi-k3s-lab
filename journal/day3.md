# Welcome to Day Three
## Today I installed K3s as well as it's many counterparts. 

- I rearranged files to create a better organization
- created a playbook main.yml to do a number of things including: Enable cgroup 
memory in boot orangepiEnv ( a resource manager so my pi doesnt crash)
- Reboot the Orange Pi if boot config changes
- Download and install K3s using curl, ensure k3s service started
- create .kube dir
- Download nerdctl a less ram intensive alternative to Docker, runs same commands

