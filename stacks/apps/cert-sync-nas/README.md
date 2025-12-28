# Certificate Sync for NAS

Automatically syncs SSL certificates from Traefik to OpenMediaVault NAS using tested, modular scripts.

## How It Works

1. Runs as a Docker Swarm service with cron
2. Uses tested functions from `scripts/common/cert.sh` and `scripts/common/nas_cert.sh`
3. Extracts wildcard certificate from Traefik's `acme.json`
4. Copies certificate to NAS via SSH (using existing `selfhosted_rsa` key)
5. Installs certificate in OpenMediaVault via OMV RPC
6. Runs weekly (Sundays at 3 AM) + immediate sync on deployment

## Test Coverage

- ✅ 9 certificate extraction tests
- ✅ 6 NAS installation tests
- All functions follow TDD (Red/Green/Refactor)

## Setup & Deployment

### Automated Setup (Recommended)

The setup script automatically creates the Docker secret from your existing SSH key:

```bash
# Initialize secrets (creates Docker secret if needed)
./stacks/apps/cert-sync-nas/init-secrets.sh

# Deploy the stack
./homelab deploy --only-apps cert-sync-nas
```

**Note:** The init script reuses your existing `~/.ssh/selfhosted_rsa` key (from machines.yaml setup), so no additional SSH configuration is needed!

### Verify Deployment

```bash
# Check service status
docker service ls | grep cert-sync
docker service ps cert-sync-nas_cert-sync

# View logs
docker service logs cert-sync-nas_cert-sync

# Monitor for failures (check restart count)
docker service ps cert-sync-nas_cert-sync --format "table {{.Name}}\t{{.CurrentState}}\t{{.Error}}"

# Run manual sync (without waiting for cron)
docker exec $(docker ps -q -f name=cert-sync-nas_cert-sync) /usr/local/bin/sync-cert.sh
```

## Failure Handling

The container **exits on sync failure** (both initial and cron runs). Docker Swarm automatically restarts it.

**How to detect failures:**

```bash
# Check restart count - high count = recurring failures
docker service ps cert-sync-nas_cert-sync

# View failure logs
docker service logs cert-sync-nas_cert-sync --tail 100

# See specific error
docker service ps cert-sync-nas_cert-sync --no-trunc
```

**What happens on failure:**
1. Sync script fails
2. Container exits (cron stops)
3. Docker Swarm restarts container
4. Restart count increments
5. Initial sync runs again on restart

**Normal behavior:** Restart count stays at 0-1 (only initial deployment)

## Configuration

Environment variables (set in docker-compose.yml):

- `NAS_HOST`: Hostname or IP of NAS (default: `nas.diyhub.dev`)
- `CERT_DOMAIN`: Certificate domain to extract (default: `*.${BASE_DOMAIN}`)
- `TZ`: Timezone for cron schedule (default: `America/New_York`)

## Schedule

By default, runs every Sunday at 3 AM. To change:

Edit the cron schedule in `docker-compose.yml`:
```
0 3 * * 0  # Sundays at 3 AM
```

Cron format: `minute hour day month weekday`

## Troubleshooting

### Certificate not syncing

```bash
# Check logs
docker service logs -f cert-sync-nas_cert-sync

# Run manual sync
docker exec $(docker ps -q -f name=cert-sync-nas_cert-sync) /usr/local/bin/sync-cert.sh

# Verify acme.json has certificates
docker run --rm -v traefik_acme:/acme alpine \
  cat /acme/acme.json | jq '.cloudflare.Certificates[].domain.main'
```

### SSH connection issues

```bash
# Test SSH from container
docker exec -it $(docker ps -q -f name=cert-sync-nas_cert-sync) sh
apk add openssh-client
ssh -o StrictHostKeyChecking=no -i /ssh-key/id_rsa root@nas.diyhub.dev
```

### Certificate not applying in OMV

```bash
# SSH to NAS and check
ssh root@nas.diyhub.dev

# List certificates in OMV
omv-rpc -u admin "CertificateMgmt" "getList" | jq

# Check web UI settings
omv-rpc -u admin "WebGui" "getSettings"

# Manually apply nginx config
omv-salt deploy run nginx
```

## Manual Sync

To trigger an immediate sync without waiting for the cron schedule:

```bash
# Option 1: Execute in running container
docker exec $(docker ps -q -f name=cert-sync-nas_cert-sync) /usr/local/bin/sync-cert.sh

# Option 2: Restart service (will run initial sync)
docker service update --force cert-sync-nas_cert-sync
```

## Security Notes

- SSH key stored in Docker volume (encrypted at rest if using encrypted volumes)
- SSH key has read-only access in container
- Uses SSH key authentication (no passwords)
- Traefik acme.json mounted read-only
- Consider using a dedicated SSH key with restricted permissions on NAS
