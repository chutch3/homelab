<!-- DOCKUMENTOR START -->
# Architecture

---

## Service Topology

```mermaid
%%{init: {"flowchart": {"defaultRenderer": "elk", "nodeSpacing": 40, "rankSpacing": 50}}}%%
flowchart TD
    classDef exposed fill:#2d3748,stroke:#4299e1,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef internal fill:#1a202c,stroke:#718096,stroke-width:1px,color:#e2e8f0,rx:5px,ry:5px;
    classDef datastore fill:#2b6cb0,stroke:#63b3ed,stroke-width:2px,color:#fff,rx:8px,ry:8px;
    tor_vpn["<b>tor-vpn</b><br/><i>gluetun:latest</i>"]:::internal
    tor_browser["<b>tor-browser</b><br/><i>tor-browser:1.18.0</i>"]:::internal
    ip_check["<b>ip-check</b><br/><i>python:3.12-alpine</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant tor_vpn as tor-vpn
    participant tor_browser as tor-browser
    participant ip_check as ip-check
```

---

## Services


### tor-vpn

**Image:** `qmcgaw/gluetun:latest`


| Property | Value |
|----------|-------|
| **Networks** | tor-internal |
| **Depends on** | — |


**Environment:**

```
VPN_SERVICE_PROVIDER=${TOR_VPN_SERVICE_PROVIDER}
VPN_TYPE=wireguard
WIREGUARD_PRIVATE_KEY=${TOR_WIREGUARD_PRIVATE_KEY}
WIREGUARD_ADDRESSES=${TOR_WIREGUARD_ADDRESSES}
SERVER_COUNTRIES=${TOR_VPN_SERVER_COUNTRIES}
TZ=${TZ}
SOCKS5_ENABLED=on
SOCKS5_LISTENING_ADDRESS=:1080
FIREWALL_INPUT_PORTS=1080
```



---

### tor-browser

**Image:** `kasmweb/tor-browser:1.18.0`


| Property | Value |
|----------|-------|
| **Networks** | tor-internal, traefik-public |
| **Depends on** | — |


**Environment:**

```
VNC_PW=${TOR_BROWSER_VNC_PASSWORD}
TZ=${TZ}
DISABLE_CUSTOM_STARTUP=true
```


**Volumes:**

- `tor_browser_data:/home/kasm-user`
- `{'type': 'tmpfs', 'target': '/dev/shm', 'tmpfs': {'size': 536870912}}`


---

### ip-check

**Image:** `python:3.12-alpine`


**Command:** `['python3', '/app/server.py']`


| Property | Value |
|----------|-------|
| **Networks** | tor-internal, traefik-public |
| **Depends on** | — |


**Environment:**

```
TOR_VPN_HOST=tor-vpn
TOR_VPN_SOCKS_PORT=1080
```



---


## Network Flow

```mermaid
sankey-beta
    Net: tor-internal, ip_check, 1
    Net: tor-internal, tor_browser, 1
    Net: tor-internal, tor_vpn, 1
    Net: traefik-public, ip_check, 1
    Net: traefik-public, tor_browser, 1
```
<!-- DOCKUMENTOR END -->
