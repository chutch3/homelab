# tor-browser

Tor Browser via KasmVNC, with all traffic routed through a NordVPN WireGuard tunnel (gluetun). An iptables kill switch inside the browser container blocks all traffic if the VPN goes down.

Traffic path: Firefox → Tor daemon → gluetun SOCKS5 → WireGuard → internet

## Prerequisites

Before deploying, ensure the following are in place on the target Swarm node:

- Node is labeled with `tor: true` in `ansible/inventory/02-hosts.yml` under `node_labels`, and labels are synced by running:
  ```sh
  task ansible:cluster:update-labels
  ```
- iSCSI target mounted at `/mnt/iscsi/app-data/tor-browser/` (run `sudo ./setup.sh` to create and chown the directory)
- `traefik-public` external overlay network exists
- Root `.env` is populated with all `TOR_*` variables (see [Environment variables](#environment-variables))

## Setup

```sh
# 1. Create iSCSI data directory on the target node
sudo ./setup.sh

# 2. Fetch NordVPN WireGuard credentials and write to .env
./nordvpn-setup.sh --token <nordvpn_access_token>
# Other providers: populate TOR_WIREGUARD_PRIVATE_KEY and TOR_WIREGUARD_ADDRESSES in .env manually

# 3. Set remaining env vars in .env
TOR_BROWSER_VNC_PASSWORD=$(openssl rand -base64 16)

# 4. Deploy
task ansible:deploy:service -- -e 'stack_name=tor-browser'
```

## Services

| Service | Container | Purpose | URL | Auth |
|---|---|---|---|---|
| Tor Browser | `tor-browser` | Tor Browser via KasmVNC | `tor.<BASE_DOMAIN>` | Authentik |
| VPN | `tor-vpn` | gluetun WireGuard + SOCKS5 proxy | internal only | none |
| VPN Status | `ip-check` | Shows VPN exit IP | `tor-check.<BASE_DOMAIN>` | Authentik |

## How it works

### VPN (gluetun)

[Gluetun](https://github.com/qdm12/gluetun) manages a WireGuard tunnel via NordVPN NordLynx and exposes a SOCKS5 proxy on port `1080` within the `tor-internal` network. The Tor daemon inside the browser container is configured to send all its traffic through this proxy via `Socks5Proxy tasks.tor-vpn:1080` in `torrc-defaults`.

`init-vpn.sh` overrides the gluetun entrypoint to inject an iptables `INPUT ACCEPT` rule for port 1080 on all interfaces. Gluetun's built-in `FIREWALL_INPUT_PORTS` only opens the port on the WireGuard gateway interface — Docker overlay traffic arrives on `eth0` and is dropped without this workaround. The rule is re-injected in a background loop to survive VPN restarts.

### Kill switch

`browser-prestart.sh` runs as root before dropping to `kasm-user`. It:

1. Waits for gluetun's SOCKS5 on `tasks.tor-vpn:1080` (up to 300 s)
2. Resolves the gluetun task IP and derives the `/24` tor-internal subnet
3. Applies an iptables OUTPUT kill switch: allows loopback and `ESTABLISHED/RELATED` (for KasmVNC responses back to Traefik), allows the tor-internal subnet, drops everything else
4. Writes `Socks5Proxy tasks.tor-vpn:1080` to `torrc-defaults` using the hostname so Tor re-resolves via Docker DNS on each connection, surviving gluetun task restarts that change the task IP
5. Seeds the XFCE desktop icon config and creates a desktop shortcut + autostart entry for Tor Browser
6. Drops to `kasm-user` via `exec su` and hands off to the KasmVNC startup chain

### Desktop and browser lifecycle

`DISABLE_CUSTOM_STARTUP=true` is set so kasmweb's auto-restart loop does not manage the browser. Instead, `browser-prestart.sh` writes a replacement `custom_startup.sh` that sleeps indefinitely (keeping the kasmweb service manager happy) and an XFCE autostart entry that launches Tor Browser once at VNC startup. A desktop `.desktop` shortcut lets the user reopen the browser manually after closing it.

`init: true` is required — it injects tini as PID 1. Without it, `start-tor-browser --detach` orphans `firefox.real`, which becomes a zombie under the `su` PID 1 and causes the pgrep-based restart detection to fail permanently.

### Networks

- **`traefik-public`** — shared external network; gives Traefik access to route HTTPS to KasmVNC and the ip-check service
- **`tor-internal`** — isolated overlay network for traffic between `tor-browser` and `tor-vpn`; not reachable from outside the stack

### Storage

| Volume | Type | Backend |
|---|---|---|
| `tor_browser_data` | local bind mount | `/mnt/iscsi/app-data/tor-browser/` — Tor Browser profile and XFCE user config |

## Verification

After deployment, confirm the full chain is working:

```sh
TB_ID=$(docker ps --filter name=tor-browser_tor-browser --format '{{.ID}}' | head -1)

# Kill switch rules present
docker exec $TB_ID bash -c 'export XTABLES_LOCKFILE=/tmp/xtables.lock; \
  IPT=$(ls /usr/sbin/iptables-legacy /sbin/iptables-legacy 2>/dev/null | head -1); \
  [ -z "$IPT" ] && IPT=iptables; $IPT -L OUTPUT -n'

# Direct internet blocked
docker exec $TB_ID bash -c \
  'timeout 3 bash -c "cat </dev/null >/dev/tcp/8.8.8.8/53" 2>&1 && echo "LEAK" || echo "OK: blocked"'

# gluetun SOCKS5 reachable
docker exec $TB_ID bash -c \
  'timeout 5 bash -c "cat </dev/null >/dev/tcp/tasks.tor-vpn/1080" && echo "OK" || echo "FAIL"'
```

In the Tor Browser:

- `https://tor-check.<BASE_DOMAIN>` — should show a NordVPN IP, not your home IP
- `https://check.torproject.org` — should say "Congratulations. This browser is configured to use Tor."
- `https://dnsleaktest.com` — DNS servers should be Tor exit nodes

## Callouts

> **Tor identity** — Tor Browser assigns a new circuit (exit node) per tab session. The ip-check page reflects the VPN exit IP, not the Tor exit IP. Use `check.torproject.org` and `dnsleaktest.com` inside the browser to verify the Tor layer.

- **`tasks.tor-vpn` vs `tor-vpn`** — The kill switch and torrc-defaults use `tasks.tor-vpn` (task IP via round-robin DNS) not `tor-vpn` (the Swarm VIP). The VIP uses ipvs NAT which has hairpin issues on same-host overlay connections; the task IP connects directly.

- **iptables-legacy** — `nf_tables` (the nftables backend) requires kernel netlink access that Docker blocks even with `NET_ADMIN` on some kernels. The prestart script explicitly selects `iptables-legacy` when present, falling back to `iptables`. `/run/xtables.lock` is not writable in the container; `XTABLES_LOCKFILE=/tmp/xtables.lock` redirects it.

- **Docker config naming** — Docker configs are immutable once created. Updating `browser-prestart.sh` or `ip-check.py` requires renaming the config (e.g. `tor_browser_prestart_v3`) and updating both the `configs:` block and the service reference, otherwise the old config will continue to be used.

- **All services pinned to `node.labels.tor == true`** — the iSCSI bind mount and the `tor-internal` overlay network routing both depend on co-location. Node labels are managed in `ansible/inventory/02-hosts.yml` and synced with `task ansible:cluster:update-labels`.

## Environment variables

All stack-specific variables are prefixed `TOR_` in the root `.env`. Shared variables (`TZ`, `BASE_DOMAIN`) are unprefixed.

| Variable | Used by | Description |
|---|---|---|
| `TOR_VPN_SERVICE_PROVIDER` | tor-vpn | VPN provider name (e.g. `nordvpn`) |
| `TOR_WIREGUARD_PRIVATE_KEY` | tor-vpn | WireGuard private key (fetched by `nordvpn-setup.sh`) |
| `TOR_WIREGUARD_ADDRESSES` | tor-vpn | WireGuard interface address (NordLynx: `10.5.0.2/32`) |
| `TOR_VPN_SERVER_COUNTRIES` | tor-vpn | VPN exit country (e.g. `Switzerland`) |
| `TOR_BROWSER_VNC_PASSWORD` | tor-browser | KasmVNC password — generate with `openssl rand -base64 16` |

## Files

```
docker-compose.yml
setup.sh               create iSCSI data dir and set ownership
nordvpn-setup.sh       fetch NordVPN NordLynx credentials and write to .env
ip-check.py            VPN exit IP check HTTP server (pure Python, no runtime deps)
scripts/
  init-vpn.sh          gluetun entrypoint: inject port-1080 iptables INPUT rule
  browser-prestart.sh  tor-browser entrypoint: kill switch, torrc, desktop, privilege drop
```
