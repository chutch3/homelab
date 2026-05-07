# Tailscale VPN

Tailscale gives each cluster node its own routable IP address (`100.x.x.x`) so you can access your homelab from anywhere without exposing any ports to the internet. It is optional and disabled by default.

---

## How It Works

Each node is registered as an individual Tailscale device. Your laptop or phone connects to Tailscale and can reach any node directly at its `100.x.x.x` address. Nothing else on your LAN (`192.168.86.0/24`) — your router, NAS, IoT devices — is exposed through Tailscale unless you explicitly advertise subnet routes.

!!! info "OPNsense Note"
    When you add an OPNsense firewall, subnet routing transfers to its Tailscale plugin. The cluster node configuration does not need to change — leave `TAILSCALE_ADVERTISE_ROUTES` empty on all Linux nodes and configure routes on OPNsense instead.

---

## Prerequisites

Before running the playbook you need to do two things in the Tailscale admin console.

### 1. Upload the ACL Policy

The ACL policy defines who can access what and pre-authorizes the `tag:homelab-server` tag. Without this step, tagged auth key creation will fail.

1. Open [login.tailscale.com/admin/acls](https://login.tailscale.com/admin/acls)
2. Replace the existing policy with the contents of `ansible/roles/tailscale/tailscale-acl-policy.json`
3. Save

The default policy allows only your account (`autogroup:admin`) to reach homelab nodes on ports 22, 80, 443, and 5380. Nodes cannot reach each other or your personal devices via Tailscale.

### 2. Generate a Reusable Auth Key

1. Open [login.tailscale.com/admin/settings/keys](https://login.tailscale.com/admin/settings/keys)
2. Click **Generate auth key**
3. Set the options:
    - **Reusable**: on (the role uses the same key for all nodes)
    - **Ephemeral**: off (nodes should persist in your Tailscale network)
    - **Pre-authorized**: on (skips the manual approval step)
    - **Tags**: `tag:homelab-server`
4. Copy the key — it starts with `tskey-auth-`

---

## Configuration

Add the following to your `.env` file:

```bash title=".env"
# Enable Tailscale on all cluster nodes
TAILSCALE_ENABLED=true

# Reusable auth key from the Tailscale admin console
TAILSCALE_AUTH_KEY=tskey-auth-your-key-here

# Subnet routes to advertise (leave empty for node-only access)
# Example: TAILSCALE_ADVERTISE_ROUTES=192.168.86.0/24
TAILSCALE_ADVERTISE_ROUTES=
```

### Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TAILSCALE_ENABLED` | Enable Tailscale role during bootstrap | `false` |
| `TAILSCALE_AUTH_KEY` | Reusable tagged auth key for node registration | _(required)_ |
| `TAILSCALE_ADVERTISE_ROUTES` | Comma-separated CIDRs to advertise | _(empty — node only)_ |

Per-node settings live in `ansible/inventory/group_vars/all/main.yml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `tailscale_hostname` | Node's Tailscale display name | `{{ inventory_hostname }}` |
| `tailscale_tags` | ACL tags applied to the node | `["tag:homelab-server"]` |
| `tailscale_health_check_interval_minutes` | How often the health check cron runs | `5` |

---

## Deployment

### Dry Run First

Always verify with a check run before applying changes:

```bash
task ansible:tailscale:configure -- -K --check
```

### Deploy to All Nodes

```bash
task ansible:tailscale:configure -- -K
```

### Deploy to a Single Node

Useful for testing on one machine before rolling out to the rest:

```bash
task ansible:tailscale:configure:node -- cody-X570-GAMING-X -K
```

### Check Status Across All Nodes

```bash
task ansible:tailscale:status
```

---

## What the Role Does

On each run the role:

1. Installs `tailscale` from the official apt repository if not already present
2. Reads current state from `tailscale status --json`
3. Compares current hostname and routes against desired configuration
4. Authenticates with the auth key **only if the node is not already connected** — the key is never consumed on subsequent runs
5. Applies any configuration drift (hostname or route changes) without re-authenticating
6. Deploys the health check script, sudoers rule, and root crontab entry

The role is fully idempotent — running it repeatedly produces the same result and never breaks a connected node.

---

## Health Check

A cron job runs every 5 minutes as root on each node:

```bash
/usr/local/bin/check-tailscale.sh
```

If `tailscaled` is not active or `tailscale status` fails, it restarts `tailscaled` and logs the event to `/var/log/tailscale-health.log`. Non-root users can also invoke it manually via the sudoers rule deployed by the role:

```bash
sudo /usr/local/bin/check-tailscale.sh
```

---

## Security Model

- **No subnet routes by default** — only the Tailscale IPs of your cluster nodes are reachable. Your LAN devices are not exposed.
- **ACL policy restricts access** — only your Tailscale account can connect to `tag:homelab-server` nodes, on specific ports only.
- **Nodes cannot reach each other via Tailscale** — the ACL policy has no node-to-node rule, so cross-node Tailscale traffic is blocked.
- **Tagged auth key** — the key is scoped to `tag:homelab-server`. A leaked key can only register new nodes with that tag; it cannot impersonate your personal devices.

---

## Updating the ACL Policy

To open additional ports or add new device tags, edit `ansible/roles/tailscale/tailscale-acl-policy.json` and re-upload it to [login.tailscale.com/admin/acls](https://login.tailscale.com/admin/acls). The Ansible role does not manage ACLs — they are applied manually through the Tailscale admin console.

---

## Removing Tailscale from a Node

```bash
# Remove the node from your Tailscale network
tailscale logout

# Uninstall the package
sudo apt remove tailscale
```

Set `TAILSCALE_ENABLED=false` in `.env` to prevent the role from reinstalling it during future bootstrap runs.
