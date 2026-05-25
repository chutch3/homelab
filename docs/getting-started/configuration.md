# Configuration Reference

## Environment Variables

Copy `.env.example` to `.env` and set your values. Full list in the file; key variables below.

### Required

| Variable | Example | Purpose |
|----------|---------|---------|
| `BASE_DOMAIN` | `yourdomain.com` | Service routing and SSL |
| `CF_Token` | Cloudflare API token | DNS challenge for Let's Encrypt |
| `PRIMARY_DNS_API_KEY` | secure password | Technitium DNS admin |

### DNS

| Variable | Default | Purpose |
|----------|---------|---------|
| `PRIMARY_DNS_TYPE` | `technitium` | DNS provider adapter |
| `PRIMARY_DNS_MANAGED` | `true` | `false` to bring your own DNS |
| `DNS_SERVER_FORWARDERS` | `1.1.1.1,1.0.0.1` | Upstream resolvers |
| `SECONDARY_DNS_ENABLED` | `false` | Sync to Pi-hole v6+ fallback |
| `SECONDARY_DNS_HOST` | — | Pi-hole IP (when enabled) |
| `SECONDARY_DNS_API_KEY` | — | Pi-hole API password |

### Service Credentials

```bash
GRAFANA_ADMIN_PASSWORD=
PHOTOPRISM_DB_PASSWORD=
MARIADB_ROOT_PASSWORD=

NAS_SERVER=192.168.1.50
SMB_USERNAME=homelab
SMB_PASSWORD=

LIBRENMS_DB_PASSWORD=
LIBRENMS_SNMP_COMMUNITY=public
LIBRENMS_ADMIN_USER=admin
LIBRENMS_ADMIN_PASS=
LIBRENMS_ADMIN_EMAIL=

TOR_VPN_SERVICE_PROVIDER=mullvad
TOR_VPN_SERVER_COUNTRIES=Switzerland
TOR_WIREGUARD_PRIVATE_KEY=
TOR_WIREGUARD_ADDRESSES=10.x.x.x/32
TOR_BROWSER_VNC_PASSWORD=
```

---

## Host Inventory

`ansible/inventory/02-hosts.yml`:

```yaml
all:
  children:
    managers:
      hosts:
        manager:
          ansible_host: 192.168.1.100
          ansible_user: ubuntu
          node_labels:
            storage: true
    workers:
      hosts:
        worker-01:
          ansible_host: 192.168.1.101
          ansible_user: ubuntu
          node_labels:
            gpu: true
            database: true
```

Node labels control placement: `database: true` for PostgreSQL, `gpu: true` for Ollama/Immich ML, `tor: true` for Tor Browser, `downloads: true` for VPN clients.

---

## Secrets Management

Synced to Bitwarden for backup/restore across machines.

```bash
task secrets:login    # Authenticate
task secrets:push     # Upload .env, hosts.yml, ssh.yml, snmp.yml
task secrets:pull     # Restore all from vault
task secrets:wipe     # Delete local copies
```

---

## Required Ports

Between cluster nodes:

| Port | Protocol | Purpose |
|------|----------|---------|
| 2377 | TCP | Swarm management |
| 7946 | TCP/UDP | Container discovery |
| 4789 | UDP | Overlay network |
| 80/443 | TCP | HTTP/HTTPS (Traefik) |
