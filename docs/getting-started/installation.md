# Installation

The [Quick Start](quick-start.md) terminal session covers the full deployment flow interactively. This page documents the commands for reference.

## Deploy

```bash
task ansible:install        # Install Ansible + dependencies
task ansible:ssh:generate   # Create SSH key pair
task ansible:ssh:distribute # Push to all nodes
task ansible:ping           # Verify connectivity
task ansible:bootstrap      # Install Docker, harden nodes
task ansible:deploy         # Init swarm, deploy all stacks
```

## What Deploys

1. **Docker Swarm** — multi-node cluster initialized
2. **traefik-public network** — shared overlay for service routing
3. **Traefik** — reverse proxy with automatic Let's Encrypt SSL
4. **Technitium** — internal DNS with auto-registration
5. **Monitoring** — Prometheus + Grafana + Loki + Promtail
6. **41 application stacks** — deployed in parallel with DNS records

## Multi-Node

Add workers to `ansible/inventory/02-hosts.yml`:

```yaml
workers:
  hosts:
    worker-01:
      ansible_host: 192.168.1.101
      ansible_user: ubuntu
      node_labels:
        gpu: true
        database: true
    worker-02:
      ansible_host: 192.168.1.102
      ansible_user: ubuntu
      node_labels:
        storage: true
```

Workers join the swarm automatically on `task ansible:deploy`.

## Teardown

```bash
task ansible:teardown                  # Remove services (keeps data)
task ansible:teardown:with-volumes     # Remove everything (destructive)
```

## Troubleshooting

**SSH permission denied:** `task ansible:ssh:distribute` or debug with `ssh -v user@node`

**Service stuck pending:** `docker service ps <service>` — check placement constraints

**SSL issues:** `docker service logs reverse-proxy_traefik | grep acme`

Full troubleshooting: [Troubleshooting Guide](../troubleshooting.md)
