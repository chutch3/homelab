# Certificate Sync for NAS

Automatically issues and renews an SSL certificate for the NAS via `acme.sh` (Cloudflare DNS challenge) and installs it into OpenMediaVault.

## How It Works

On every container start, the startup script:

1. Copies the SSH key from the Docker secret (`/ssh-key/id_rsa`) to `/root/.ssh/id_rsa` so that `ssh`/`scp` can find it (the `neilpang/acme.sh` image sets `$HOME=/acme.sh`, but OpenSSH resolves default key paths from the passwd home `/root`)
2. Runs `acme.sh --issue` via Cloudflare DNS challenge — skips silently if the cert isn't due for renewal yet
3. Runs `/scripts/sync-nas-cert.sh` to copy the certificate from the `acme_certs` volume and install it on the NAS via OMV RPC over SSH — if this fails the container exits and Swarm restarts it
4. Installs a weekly crontab (Sundays at 3 AM) to renew and re-sync
5. Starts `crond` to keep the container running

`sync-nas-cert.sh` calls `omv_cert_install` from `scripts/common/nas/omv.sh`, which:
- SCPs the cert and key to `/tmp/` on the NAS
- SSHes in and runs `omv-rpc CertificateMgmt set` to import the cert
- Applies dirty config modules and restarts nginx

## Prerequisites

### NAS SSH access

The SSH key used by the container must be authorized on the NAS for `NAS_USER` (default: `cody`):

```bash
ssh-copy-id -i "$SSH_KEY_FILE" cody@nas.<your-domain>
```

### NAS sudoers rule (required for OMV 7)

The NAS user needs passwordless sudo for the OMV management commands. On the NAS:

```bash
echo 'cody ALL=(ALL) NOPASSWD: /usr/sbin/omv-rpc, /usr/sbin/omv-salt, /usr/bin/systemctl restart nginx' \
  | sudo tee /etc/sudoers.d/omv-cert-sync
sudo chmod 440 /etc/sudoers.d/omv-cert-sync
```

This is required because OMV 7 stores the engine socket in a root-only directory. There is no group delegation available.

## Setup & Deployment

```bash
task ansible:deploy:service -- -e "stack_name=cert-sync-nas" -K
```

The deploy pipeline reads `pre-flight.yml`, creates the `cert_sync_ssh_key` Docker secret from the key at `$SSH_KEY_FILE`, and validates that `CLOUDFLARE_DNS_API_TOKEN` and `SSH_KEY_FILE` are set in `.env` before deploying.

Note: `CF_Token` is the internal container environment variable name set from `CLOUDFLARE_DNS_API_TOKEN` — you only need to set `CLOUDFLARE_DNS_API_TOKEN` in `.env`.

### Verify Deployment

```bash
# Check service status
docker service ls | grep cert-sync

# View logs
docker service logs cert-sync-nas_nas-cert --tail 50

# Check restart count (should stay at 0-1 after initial deploy)
docker service ps cert-sync-nas_nas-cert
```

## Failure Handling

All failures are fatal — if the initial sync or a cron-triggered sync fails, the container exits and Docker Swarm restarts it (`condition: any, delay: 5s`). This means the container will keep retrying until the sync succeeds.

To diagnose a failure:

```bash
docker service logs cert-sync-nas_nas-cert --tail 100
docker service ps cert-sync-nas_nas-cert --no-trunc
```

## Configuration

Environment variables (set via `.env` and passed through `docker-compose.yml`):

| Variable | Default | Description |
|---|---|---|
| `CLOUDFLARE_DNS_API_TOKEN` | *(required)* | Cloudflare API token for DNS challenge |
| `BASE_DOMAIN` | *(required)* | Base domain — NAS host and cert domain are derived from this |
| `SSH_KEY_FILE` | `~/.ssh/homelab_rsa` | Path to the SSH private key used by `init-secrets.sh` |
| `NAS_HOST` | `nas.${BASE_DOMAIN}` | NAS hostname for SSH/SCP (overrides the derived value) |
| `NAS_USER` | `root` | SSH user on the NAS |
| `CERT_DOMAIN` | `nas.${BASE_DOMAIN}` | Domain for the certificate (overrides the derived value) |
| `TZ` | `America/New_York` | Timezone for cron schedule |

## SSH Key Rotation

If you rename or regenerate the SSH key, the Docker secret will be stale and SSH auth will fail. Steps to fix:

```bash
# 1. Scale down the service so Swarm releases the secret
docker service scale cert-sync-nas_nas-cert=0

# 2. Detach the secret from the service (required before deletion)
docker service update --secret-rm cert_sync_ssh_key cert-sync-nas_nas-cert

# 3. Remove the stale secret
docker secret rm cert_sync_ssh_key

# 4. Redeploy — pre-flight recreates the secret automatically
task ansible:deploy:service -- -e "stack_name=cert-sync-nas" -K
```

Also ensure the new public key is in `root@nas.<your-domain>:~/.ssh/authorized_keys`:

```bash
ssh-copy-id -i "$SSH_KEY_FILE" root@nas.<your-domain>
```

## Troubleshooting

### SSH auth fails (`Permission denied (publickey,password)`)

Most likely cause: the Docker secret is stale (see SSH Key Rotation above). To confirm the right key is in the secret, check the fingerprint:

```bash
# Fingerprint of the key on the host
ssh-keygen -lf "$SSH_KEY_FILE"

# Fingerprint of the key currently in the container
docker exec $(docker ps -q -f name=cert-sync-nas_nas-cert) ssh-keygen -lf /root/.ssh/id_rsa
```

If they don't match, recreate the secret.

### Certificate not syncing

```bash
# View recent logs
docker service logs cert-sync-nas_nas-cert --tail 50

# Trigger an immediate sync manually
docker exec $(docker ps -q -f name=cert-sync-nas_nas-cert) /scripts/sync-nas-cert.sh
```

### Let's Encrypt rate limit errors

The `--force` flag was intentionally removed from the `acme.sh --issue` command. If you see rate limit errors (429), the container was restarting in a loop and hit the 5-cert/week limit. Wait for the window to pass (the error message shows the exact retry time) — the cert will renew automatically on the next Sunday cron run.

### Certificate not applying in OMV

```bash
ssh root@nas.<your-domain>

# List certificates in OMV
omv-rpc -u admin "CertificateMgmt" "getList" | jq

# Check which cert the web UI is using
omv-rpc -u admin "WebGui" "getSettings" | jq .sslcertificateref

# Manually apply nginx config
omv-salt deploy run nginx
```

## Security Notes

- SSH private key is stored as a Docker secret (encrypted in the Swarm raft store)
- The secret is mounted read-only at `/ssh-key/id_rsa` inside the container
- No password authentication — key-only SSH access to the NAS (`StrictHostKeyChecking=accept-new`)
- Consider using a dedicated NAS SSH key with restricted permissions rather than the shared `homelab_rsa`
