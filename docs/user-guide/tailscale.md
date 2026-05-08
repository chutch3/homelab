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
    - **Description**: something like `homelab-nodes`
    - **Reusable**: on (the role uses the same key for all nodes)
    - **Ephemeral**: off (nodes should persist in your Tailscale network)
    - **Tags**: add `tag:homelab-server` (tagging a key automatically pre-authorizes devices)
4. Copy the key — it starts with `tskey-auth-`

!!! info "Pre-authorization"
    Adding a tag to the auth key automatically pre-authorizes any device that registers with it — there is no separate toggle in the current Tailscale UI.

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

## Accessing LAN Devices — NAS and Backup DNS

Cluster nodes register directly with Tailscale, so they are reachable by their `100.x.x.x` addresses with no extra configuration. Devices that don't run Tailscale — your NAS, Pi-hole at `192.168.86.140`, printers, or any other LAN device — are not reachable by default.

To reach them remotely, one cluster node must **advertise subnet routes** for your LAN, acting as a gateway. Remote Tailscale clients then route `192.168.86.0/24` traffic through that node.

!!! info "OPNsense Note"
    When you add OPNsense, subnet routing transfers to its Tailscale plugin. Leave `TAILSCALE_ADVERTISE_ROUTES` empty on all Linux nodes and configure the LAN route on OPNsense instead.

### Enable Subnet Routing

**1. Set the route in `.env`** on the node you want to act as gateway (typically the manager):

```bash title=".env"
TAILSCALE_ADVERTISE_ROUTES=192.168.86.0/24
```

**2. Redeploy Tailscale on that node:**

```bash
task ansible:tailscale:configure:node -- cody-X570-GAMING-X -K
```

**3. Approve the route in the Tailscale admin console:**

Advertised routes must be explicitly approved before Tailscale clients use them.

1. Open [login.tailscale.com/admin/machines](https://login.tailscale.com/admin/machines)
2. Find the gateway node and click **Edit route settings**
3. Enable `192.168.86.0/24`
4. Save

**4. Accept routes on your client device:**

Routes are not used by clients until accepted. On Linux:

```bash
tailscale up --accept-routes
```

On macOS and iOS, enable **Use Tailscale Subnets** in the app settings.

### What You Can Reach

Once subnet routing is active, all `192.168.86.0/24` addresses are routable over Tailscale:

| Device | Address | Notes |
|--------|---------|-------|
| NAS | `192.168.86.x` | File shares (SMB/NFS), admin UI |
| Pi-hole (backup DNS) | `192.168.86.140` | Admin UI at `192.168.86.140/admin` |
| Router | `192.168.86.1` | Admin UI |
| Any other LAN device | `192.168.86.x` | Printers, IoT, etc. |

### ACL Policy for Subnet Access

The default ACL policy only opens ports 22, 80, 443, and 5380 on `tag:homelab-server`. Subnet-routed traffic goes through the gateway node but targets LAN IPs that aren't tagged. To allow full LAN access, add a rule to `tailscale-acl-policy.json`:

```json
// Account owner can reach the full home LAN via subnet routing
{
    "action": "accept",
    "src":    ["autogroup:admin"],
    "dst":    ["192.168.86.0/24:*"],
},
```

Upload the updated policy to [login.tailscale.com/admin/acls](https://login.tailscale.com/admin/acls) after editing.

---

## Split DNS — Resolving Private Services Remotely

Without split DNS, connecting to Tailscale lets you reach each node at its `100.x.x.x` address but private service names like `grafana.diyhub.dev` won't resolve — your private Technitium server is on the LAN, not reachable remotely.

Split DNS fixes this by telling Tailscale: "for `diyhub.dev` queries, ask the manager node's Technitium." Since the manager is a Tailscale peer, it's reachable without advertising subnet routes.

### How It Works

Technitium is configured to accept DNS queries from Tailscale's CGNAT range (`100.64.0.0/10`) in addition to standard private networks. When you're connected to Tailscale remotely, DNS queries for `diyhub.dev` are forwarded to the manager's Tailscale IP, Technitium resolves them, and your services are accessible by name.

**Cluster nodes are not affected.** The Ansible role sets `--accept-dns=false` on every cluster node, so Tailscale never overrides their system resolver. Nodes continue using Technitium directly via the LAN IP — split DNS is only active on your personal devices (laptop, phone) when they connect remotely.

Port 53 is open between nodes in the ACL policy so Tailscale's built-in health checks can verify the nameserver is reachable. This is a health-check-only path — no actual DNS traffic from cluster nodes flows through it.

### Setup

This is a one-time manual step after Tailscale is deployed on at least the manager node.

**1. Deploy Tailscale on all nodes:**

```bash
task ansible:tailscale:configure -- -K
```

**2. Find the manager's Tailscale IP:**

```bash
task ansible:tailscale:status
```

Note the `100.x.x.x` address for `cody-X570-GAMING-X` — this is the node running Technitium.

**3. Configure split DNS in the Tailscale admin console:**

1. Open [login.tailscale.com/admin/dns](https://login.tailscale.com/admin/dns)
2. Under **Nameservers**, click **Add nameserver → Custom**
3. Set the nameserver IP to the manager's Tailscale IP (`100.x.x.x`)
4. Enable **Restrict to domain** and enter your base domain (e.g. `diyhub.dev`)
5. Save

**4. Redeploy the DNS stack to apply the Technitium recursion change:**

```bash
task ansible:deploy:service -- -e "stack_name=dns"
```

After this, any device connected to Tailscale can resolve `grafana.diyhub.dev`, `dns.diyhub.dev`, and all other private services by name.

!!! info "Manager failover"
    The DNS stack can reschedule to another `dns=true` labeled node if the manager goes down. If that happens, update the nameserver IP in the Tailscale admin console to the new node's Tailscale IP.

---

## Security Model

- **No subnet routes by default** — only the Tailscale IPs of your cluster nodes are reachable. Your LAN devices are not exposed.
- **ACL policy restricts access** — only your Tailscale account can connect to `tag:homelab-server` nodes, on specific ports only.
- **Nodes cannot reach each other via Tailscale** — the ACL policy has no node-to-node rule, so cross-node Tailscale traffic is blocked.
- **Tagged auth key** — the key is scoped to `tag:homelab-server`. A leaked key can only register new nodes with that tag; it cannot impersonate your personal devices.

---

## Trust Model

Understanding what Tailscale can and cannot see is useful before trusting it with homelab access.

### WireGuard End-to-End Encryption

All traffic between your devices travels over WireGuard tunnels. WireGuard keys are generated on each device and exchanged through Tailscale's coordination server — but the private keys never leave your devices. Tailscale facilitates the key exchange; it cannot decrypt your traffic.

### Control Plane vs Data Plane

Tailscale has two distinct planes:

| Plane | What it does | Who operates it |
|-------|--------------|-----------------|
| **Control plane** | Distributes public keys and coordinates routing | Tailscale (hosted) |
| **Data plane** | Carries actual traffic between devices | Your devices, peer-to-peer |

When two devices can reach each other directly (most home and office networks), traffic flows peer-to-peer and never touches Tailscale's servers. Tailscale's coordination server sees which devices are in your network and their public WireGuard keys — not the traffic itself.

### DERP Relay Fallback

When a direct WireGuard connection cannot be established (strict NAT, some cellular networks), traffic is relayed through Tailscale's DERP (Designated Encrypted Relay for Packets) servers. The connection is still end-to-end encrypted — DERP can see the volume and timing of relayed bytes but not their contents. Direct connections are always preferred and established as soon as they become possible.

### Headscale — Self-Hosted Control Plane

[Headscale](https://headscale.net) is an open-source, self-hosted replacement for Tailscale's coordination server. It gives you full control over the control plane. The trade-off: Headscale itself must be reachable from the internet (direct port forward, VPS, or Cloudflare tunnel), which recreates the same public exposure you were trying to avoid. For a personal homelab, this adds infrastructure complexity without a meaningful security gain over hosted Tailscale.

For this homelab, hosted Tailscale is the pragmatic choice:

- The control plane sees no traffic content — only public keys and network topology
- The ACL policy restricts what can reach your nodes and on which ports
- Tagged auth keys limit the blast radius of a leaked key to registering new `tag:homelab-server` nodes only
- No publicly exposed port on your home network is required

If your threat model requires zero trust in any third-party control plane, Headscale is the right path — but factor in the public server requirement.

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
