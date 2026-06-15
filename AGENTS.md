# Agent Context

This file helps LLM-based agents understand and work with this repository.

## What This Is

A Docker Swarm homelab platform that deploys 41 self-hosted services across multiple Linux nodes using Ansible automation. Not Kubernetes — uses native Docker Swarm for simplicity.

## How To Deploy a Service

```bash
task ansible:deploy:service -- -e "stack_name=<name>"
```

Service definitions live in `stacks/apps/<name>/docker-compose.yml`. Every service uses the `traefik-public` external overlay network and gets automatic SSL via Traefik labels.

## How To Remove a Service

```bash
task ansible:teardown:service -- -e "stack_name=<name>"
task ansible:teardown:service -- -e "stack_name=<name> remove_volumes=true"  # delete data
```

## Architecture Decisions

- **Docker Swarm over Kubernetes** — simpler, lower resource overhead, sufficient for 3-node home cluster
- **Ansible over Terraform** — mutable infrastructure is fine for a homelab; Ansible is simpler for config management
- **OCFS2 over GlusterFS/Ceph** — cluster filesystem for shared iSCSI block storage; lower overhead than distributed FS
- **Traefik over Nginx** — native Docker integration, automatic service discovery via labels
- **Technitium over CoreDNS** — web UI for debugging, built-in DHCP, conditional forwarding

## File Conventions

| Pattern | Purpose |
|---------|---------|
| `stacks/apps/*/docker-compose.yml` | Service definition (Swarm mode) |
| `ansible/playbooks/*.yml` | Orchestration playbooks |
| `ansible/roles/*/` | Reusable Ansible roles |
| `ansible/inventory/group_vars/all/main.yml` | Shared variables (packages, node config) |
| `.env` / `.env.example` | All secrets and configuration |
| `Taskfile.yml` + `ansible/Taskfile.yml` | CLI interface |

## Important Patterns

**Traefik labels** (required on every exposed service):
```yaml
deploy:
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.<name>.rule=Host(`<subdomain>.${BASE_DOMAIN}`)"
    - "traefik.http.routers.<name>.entrypoints=websecure"
    - "traefik.http.routers.<name>.tls.certresolver=dns"
    - "traefik.http.services.<name>.loadbalancer.server.port=<port>"
    - "traefik.swarm.network=traefik-public"
```

**Storage volumes** — three types:
```yaml
# iSCSI (databases, configs) — bind mount to OCFS2
volumes:
  data:
    driver: local
    driver_opts:
      type: "none"
      o: "bind"
      device: "/mnt/iscsi/app-data/<service>"

# CIFS (media files) — NAS mount
volumes:
  media:
    driver: local
    driver_opts:
      type: "cifs"
      o: "username=${SMB_USERNAME},password=${SMB_PASSWORD},vers=3.0"
      device: "//${NAS_SERVER}/<share>"

# Local (temp/cache)
volumes:
  cache:
    driver: local
```

**Pre-flight provisioning** (`stacks/apps/<name>/pre-flight.yml`, optional) — declarative
per-stack setup run by the `preflight` role before deploy. All of it executes
cluster-side (delegated to a node that mounts the storage), so it never depends on the
controller's mounts:
```yaml
validate:
  env: [REQUIRED_VAR]                                  # must be non-empty in .env
  labels: [{ some_label: "true" }]                     # ≥1 node must carry it
secrets:
  - { name: my_secret, from_env: MY_VAR }              # or from_file: $KEY_PATH
directories:                                           # created + chowned on shared storage
  - { path: <svc>, owner: 1000, group: 1000 }          # under iSCSI app-data
  - { path: <svc>-redis, base: cache, owner: 999 }     # under /mnt/iscsi/cache
files:                                                  # copy a controller file onto storage
  - { from_env: SSH_KEY_FILE, dest: <svc>/key, mode: "0600", optional: true }
templates:                                             # render a stack-dir .j2 onto storage
  - { src: foo.j2, dest: <svc>/foo.conf }
```
Schema: `schemas/pre-flight.schema.json`. **Prefer this over `hooks.sh`** — a hook is only
for genuinely imperative steps (conditional logic). Never `mkdir`/`chown` shared storage in
a hook: hooks run on the controller, which may not mount `/mnt/iscsi`.

**Node placement constraints**:
```yaml
deploy:
  placement:
    constraints:
      - node.labels.database == true   # PostgreSQL, MariaDB
      - node.labels.gpu == true        # Ollama, Immich ML
      - node.labels.tor == true        # Tor Browser stack
      - node.labels.downloads == true  # VPN download clients
```

**Authentik SSO** — two integration methods:
```yaml
# Forward auth (protects any service via Traefik middleware)
- "traefik.http.routers.<name>.middlewares=authentik@swarm"

# OAuth/OIDC (direct integration in the application)
# Configure in Authentik admin → Providers → OAuth2/OIDC
```

## Secrets

All in `.env`, synced to Bitwarden via `task secrets:push/pull`. Never committed to git.

## Testing

```bash
task lint          # Shell, YAML, Dockerfile linting
task test          # Unit + integration tests
task check         # All checks (lint + test + docs:validate)
```
