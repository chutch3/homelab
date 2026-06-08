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
    kenku_pg[("<b>kenku-pg</b><br/><i>postgres:15-alpine</i><br/>💾 Datastore")]:::datastore
    kenku_pg_backup[("<b>kenku-pg-backup</b><br/><i>postgres-backup-local:15-alpine</i><br/>💾 Datastore")]:::datastore
    kenku["<b>kenku</b><br/><i>kenku@sha256:5b84ba1f9fa87d8e6b3dc15436292a140a7e68a52739ca336bb3123f8c8e162c</i>"]:::internal
    qbittorrent --> vpn
    deluge --> vpn
    sabnzbd --> vpn
    nzbget --> vpn
    flaresolverr --> vpn
    kenku_pg_backup --> kenku_pg
    kenku --> flaresolverr
    kenku --> kenku_pg
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
    participant kenku_pg as kenku-pg
    participant kenku_pg_backup as kenku-pg-backup
    participant kenku as kenku
    qbittorrent->>vpn: Connection / Init
    deluge->>vpn: Connection / Init
    sabnzbd->>vpn: Connection / Init
    nzbget->>vpn: Connection / Init
    flaresolverr->>vpn: Connection / Init
    kenku_pg_backup->>kenku_pg: Connection / Init
    kenku->>kenku_pg: Connection / Init
    kenku->>vpn: Connection / Init
    kenku->>flaresolverr: Connection / Init
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

### kenku-pg

**Image:** `postgres:15-alpine`


| Property | Value |
|----------|-------|
| **Networks** | downloads-internal |
| **Depends on** | — |


**Environment:**

```
POSTGRES_USER=${DOWNLOADS_KENKU_DB_USER}
POSTGRES_PASSWORD=${DOWNLOADS_KENKU_DB_PASSWORD}
POSTGRES_DB=${DOWNLOADS_KENKU_DB_NAME}
```


**Volumes:**

- `kenku_pg:/var/lib/postgresql/data`


---

### kenku-pg-backup

**Image:** `prodrigestivill/postgres-backup-local:15-alpine`


| Property | Value |
|----------|-------|
| **Networks** | downloads-internal |
| **Depends on** | kenku-pg |


**Environment:**

```
POSTGRES_HOST=kenku-pg
POSTGRES_DB=${DOWNLOADS_KENKU_DB_NAME}
POSTGRES_USER=${DOWNLOADS_KENKU_DB_USER}
POSTGRES_PASSWORD=${DOWNLOADS_KENKU_DB_PASSWORD}
SCHEDULE=@daily
BACKUP_KEEP_DAYS=7
BACKUP_KEEP_WEEKS=4
BACKUP_KEEP_MONTHS=6
TZ=${TZ}
```


**Volumes:**

- `kenku_db_backups:/backups`


---

### kenku

**Image:** `ghcr.io/chutch3/kenku@sha256:5b84ba1f9fa87d8e6b3dc15436292a140a7e68a52739ca336bb3123f8c8e162c`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public, downloads-internal |
| **Depends on** | kenku-pg, vpn, flaresolverr |


**Environment:**

```
POSTGRES_HOST=kenku-pg:5432
POSTGRES_USER=${DOWNLOADS_KENKU_DB_USER}
POSTGRES_PASSWORD=${DOWNLOADS_KENKU_DB_PASSWORD}
POSTGRES_DB=${DOWNLOADS_KENKU_DB_NAME}
HTTP_PROXY=http://vpn:8888
HTTPS_PROXY=http://vpn:8888
NO_PROXY=localhost,127.0.0.1
TZ=${TZ}
```


**Volumes:**

- `torrents:/Manga`


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
    Net: downloads-internal, kenku, 1
    Net: downloads-internal, kenku_pg, 1
    Net: downloads-internal, kenku_pg_backup, 1
    Net: traefik-public, kenku, 1
```
<!-- DOCKUMENTOR END -->
