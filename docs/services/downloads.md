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
    vpn(["<b>vpn</b><br/><i>gluetun:v3.41.1</i><br/>🔌 1080:1080 | 8888:8888"]):::exposed
    qbittorrent(["<b>qbittorrent</b><br/><i>qbittorrent:latest</i><br/>🔌 "]):::exposed
    deluge(["<b>deluge</b><br/><i>deluge:latest</i><br/>🔌 "]):::exposed
    sabnzbd(["<b>sabnzbd</b><br/><i>sabnzbd:latest</i><br/>🔌 "]):::exposed
    nzbget(["<b>nzbget</b><br/><i>nzbget:latest</i><br/>🔌 "]):::exposed
    flaresolverr["<b>flaresolverr</b><br/><i>flaresolverr:latest</i>"]:::internal
    tranga_pg[("<b>tranga-pg</b><br/><i>postgres:15-alpine</i><br/>💾 Datastore")]:::datastore
    tranga_api["<b>tranga-api</b><br/><i>tranga-api:cuttingedge@sha256:67333c5f0fef2578a80f846d002fd9eefd8a580bab20ee1b1aa4514d6f1cde38</i>"]:::internal
    tranga_website["<b>tranga-website</b><br/><i>tranga-website:cuttingedge@sha256:bbe6864b603167ff17c7a010eda2c26cc242b88a58e10f9bb7f39dad87848011</i>"]:::internal
    qbittorrent --> vpn
    deluge --> vpn
    sabnzbd --> vpn
    nzbget --> vpn
    flaresolverr --> vpn
    tranga_api --> flaresolverr
    tranga_api --> tranga_pg
    tranga_website --> tranga_api
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant vpn as vpn
    participant qbittorrent as qbittorrent
    participant deluge as deluge
    participant sabnzbd as sabnzbd
    participant nzbget as nzbget
    participant flaresolverr as flaresolverr
    participant tranga_pg as tranga-pg
    participant tranga_api as tranga-api
    participant tranga_website as tranga-website
    qbittorrent->>vpn: Connection / Init
    deluge->>vpn: Connection / Init
    sabnzbd->>vpn: Connection / Init
    nzbget->>vpn: Connection / Init
    flaresolverr->>vpn: Connection / Init
    tranga_api->>tranga_pg: Connection / Init
    tranga_api->>vpn: Connection / Init
    tranga_api->>flaresolverr: Connection / Init
    tranga_website->>tranga_api: Connection / Init
```

---

## Services


### vpn

**Image:** `qmcgaw/gluetun:v3.41.1`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public, downloads-internal |
| **Depends on** | — |
| **Ports** | External: 1080:1080 External: 8888:8888 |


**Environment:**

```
VPN_SERVICE_PROVIDER=${DOWNLOADS_VPN_SERVICE_PROVIDER}
VPN_TYPE=${DOWNLOADS_VPN_TYPE}
OPENVPN_USER=${DOWNLOADS_OPENVPN_USER}
OPENVPN_PASSWORD=${DOWNLOADS_OPENVPN_PASSWORD}
SERVER_COUNTRIES=${DOWNLOADS_VPN_SERVER_COUNTRIES}
SERVER_CATEGORIES=${DOWNLOADS_VPN_SERVER_CATEGORIES}
SERVER_CITIES=${DOWNLOADS_VPN_SERVER_CITIES}
FIREWALL_OUTBOUND_SUBNETS=${LOCAL_SUBNET},${DOWNLOADS_DOCKER_SUBNET}
HTTPPROXY=on
HTTPPROXY_LISTENING_ADDRESS=:8888
TZ=${TZ}
```



---

### qbittorrent

**Image:** `lscr.io/linuxserver/qbittorrent:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public, downloads-internal |
| **Depends on** | vpn |
| **Ports** | Internal: 8080 |


**Environment:**

```
PUID=${PUID}
PGID=${PGID}
TZ=${TZ}
WEBUI_PORT=8080
```


**Volumes:**

- `qbittorrent:/config`
- `torrents:/data/torrents`


---

### deluge

**Image:** `lscr.io/linuxserver/deluge:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public, downloads-internal |
| **Depends on** | vpn |
| **Ports** | Internal: 8112 Internal: 58846 |


**Environment:**

```
PUID=${PUID}
PGID=${PGID}
UMASK=002
DELUGE_LOGLEVEL=info
```


**Volumes:**

- `deluge:/config`
- `torrents:/data/torrents`


---

### sabnzbd

**Image:** `lscr.io/linuxserver/sabnzbd:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public, downloads-internal |
| **Depends on** | vpn |
| **Ports** | Internal: 8080 |


**Environment:**

```
PUID=${PUID}
PGID=${PGID}
TZ=${TZ}
BASE_DOMAIN=${BASE_DOMAIN}
```


**Volumes:**

- `sabnzbd:/config`
- `usenet:/data/usenet`


---

### nzbget

**Image:** `lscr.io/linuxserver/nzbget:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public, downloads-internal |
| **Depends on** | vpn |
| **Ports** | Internal: 6789 |


**Environment:**

```
PUID=${PUID}
PGID=${PGID}
TZ=${TZ}
```


**Volumes:**

- `nzbget:/config`
- `usenet:/data/usenet`


---

### flaresolverr

**Image:** `ghcr.io/flaresolverr/flaresolverr:latest`


| Property | Value |
|----------|-------|
| **Networks** | downloads-internal |
| **Depends on** | vpn |


**Environment:**

```
TZ=${TZ}
LOG_LEVEL=${DOWNLOADS_FLARESOLVERR_LOG_LEVEL}
HEADLESS=true
HTTP_PROXY=http://vpn:8888
HTTPS_PROXY=http://vpn:8888
NO_PROXY=localhost,127.0.0.1
```



---

### tranga-pg

**Image:** `postgres:15-alpine`


| Property | Value |
|----------|-------|
| **Networks** | downloads-internal |
| **Depends on** | — |


**Environment:**

```
POSTGRES_USER=${DOWNLOADS_TRANGA_DB_USER}
POSTGRES_PASSWORD=${DOWNLOADS_TRANGA_DB_PASSWORD}
POSTGRES_DB=${DOWNLOADS_TRANGA_DB_NAME}
```


**Volumes:**

- `tranga_pg:/var/lib/postgresql/data`


---

### tranga-api

**Image:** `ghcr.io/chutch3/tranga-api:cuttingedge@sha256:67333c5f0fef2578a80f846d002fd9eefd8a580bab20ee1b1aa4514d6f1cde38`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public, downloads-internal |
| **Depends on** | tranga-pg, vpn, flaresolverr |


**Environment:**

```
POSTGRES_HOST=tranga-pg:5432
POSTGRES_USER=${DOWNLOADS_TRANGA_DB_USER}
POSTGRES_PASSWORD=${DOWNLOADS_TRANGA_DB_PASSWORD}
POSTGRES_DB=${DOWNLOADS_TRANGA_DB_NAME}
HTTP_PROXY=http://vpn:8888
HTTPS_PROXY=http://vpn:8888
NO_PROXY=localhost,127.0.0.1
TZ=${TZ}
```


**Volumes:**

- `torrents:/Manga`


---

### tranga-website

**Image:** `ghcr.io/chutch3/tranga-website:cuttingedge@sha256:bbe6864b603167ff17c7a010eda2c26cc242b88a58e10f9bb7f39dad87848011`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public, downloads-internal |
| **Depends on** | tranga-api |


**Environment:**

```
TRANGA_API_URL=http://tranga-api:6531
```



---


## Network Flow

```mermaid
sankey-beta
    External Scope, vpn, 1
    Internal Scope, deluge, 1
    Internal Scope, nzbget, 1
    Internal Scope, qbittorrent, 1
    Internal Scope, sabnzbd, 1
    Net: downloads-internal, flaresolverr, 1
    Net: downloads-internal, tranga_api, 1
    Net: downloads-internal, tranga_pg, 1
    Net: downloads-internal, tranga_website, 1
    Net: traefik-public, tranga_api, 1
    Net: traefik-public, tranga_website, 1
```
<!-- DOCKUMENTOR END -->
