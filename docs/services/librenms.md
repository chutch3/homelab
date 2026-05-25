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
    db[("<b>db</b><br/><i>mariadb:10</i><br/>💾 Datastore")]:::datastore
    redis[("<b>redis</b><br/><i>redis:7.2-alpine</i><br/>💾 Datastore")]:::datastore
    librenms["<b>librenms</b><br/><i>librenms:latest</i>"]:::internal
    dispatcher["<b>dispatcher</b><br/><i>librenms:latest</i>"]:::internal
    syslogng(["<b>syslogng</b><br/><i>librenms:latest</i><br/>🔌 514->514 | 514->514"]):::exposed
    snmptrapd(["<b>snmptrapd</b><br/><i>librenms:latest</i><br/>🔌 162->162 | 162->162"]):::exposed
    librenms --> db
    librenms --> redis
    dispatcher --> librenms
    syslogng --> librenms
    snmptrapd --> librenms
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant db as db
    participant redis as redis
    participant librenms as librenms
    participant dispatcher as dispatcher
    participant syslogng as syslogng
    participant snmptrapd as snmptrapd
    librenms->>db: Connection / Init
    librenms->>redis: Connection / Init
    dispatcher->>librenms: Connection / Init
    syslogng->>librenms: Connection / Init
    snmptrapd->>librenms: Connection / Init
```

---

## Services


### db

**Image:** `mariadb:10`


**Command:** `['mysqld', '--innodb-file-per-table=1', '--lower-case-table-names=0', '--character-set-server=utf8mb4', '--collation-server=utf8mb4_unicode_ci']`


| Property | Value |
|----------|-------|
| **Networks** | librenms-internal |
| **Depends on** | — |


**Environment:**

```
TZ=${TZ:-UTC}
MYSQL_DATABASE=librenms
MYSQL_USER=librenms
MYSQL_PASSWORD=${LIBRENMS_DB_PASSWORD}
MYSQL_ROOT_PASSWORD=${LIBRENMS_DB_PASSWORD}
```


**Volumes:**

- `db:/var/lib/mysql`


---

### redis

**Image:** `redis:7.2-alpine`


**Command:** `--save 60 1 --loglevel warning`


| Property | Value |
|----------|-------|
| **Networks** | librenms-internal |
| **Depends on** | — |



**Volumes:**

- `redis:/data`


---

### librenms

**Image:** `librenms/librenms:latest`


| Property | Value |
|----------|-------|
| **Networks** | librenms-internal, traefik-public |
| **Depends on** | db, redis |


**Environment:**

```
TZ=${TZ:-UTC}
PUID=${PUID:-1000}
PGID=${PGID:-1000}
DB_HOST=db
DB_NAME=librenms
DB_USER=librenms
DB_PASSWORD=${LIBRENMS_DB_PASSWORD}
DB_TIMEOUT=60
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
BASE_URL=https://librenms.${BASE_DOMAIN}
LIBRENMS_SNMP_COMMUNITY=${LIBRENMS_SNMP_COMMUNITY:-public}
LIBRENMS_ADMIN_USER=${LIBRENMS_ADMIN_USER:-admin}
LIBRENMS_ADMIN_PASS=${LIBRENMS_ADMIN_PASS}
LIBRENMS_ADMIN_EMAIL=${LIBRENMS_ADMIN_EMAIL}
```


**Volumes:**

- `librenms-data:/data`


---

### dispatcher

**Image:** `librenms/librenms:latest`


| Property | Value |
|----------|-------|
| **Networks** | librenms-internal |
| **Depends on** | librenms |


**Environment:**

```
TZ=${TZ:-UTC}
PUID=${PUID:-1000}
PGID=${PGID:-1000}
DB_HOST=db
DB_NAME=librenms
DB_USER=librenms
DB_PASSWORD=${LIBRENMS_DB_PASSWORD}
DB_TIMEOUT=60
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
BASE_URL=https://librenms.${BASE_DOMAIN}
LIBRENMS_SNMP_COMMUNITY=${LIBRENMS_SNMP_COMMUNITY:-public}
SIDECAR_DISPATCHER=1
DISPATCHER_NODE_ID=dispatcher1
```


**Volumes:**

- `librenms-data:/data`


---

### syslogng

**Image:** `librenms/librenms:latest`


| Property | Value |
|----------|-------|
| **Networks** | librenms-internal |
| **Depends on** | librenms |
| **Ports** | External: 514->514 External: 514->514 |


**Environment:**

```
TZ=${TZ:-UTC}
PUID=${PUID:-1000}
PGID=${PGID:-1000}
DB_HOST=db
DB_NAME=librenms
DB_USER=librenms
DB_PASSWORD=${LIBRENMS_DB_PASSWORD}
DB_TIMEOUT=60
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
BASE_URL=https://librenms.${BASE_DOMAIN}
SIDECAR_SYSLOGNG=1
```


**Volumes:**

- `librenms-data:/data`


---

### snmptrapd

**Image:** `librenms/librenms:latest`


| Property | Value |
|----------|-------|
| **Networks** | librenms-internal |
| **Depends on** | librenms |
| **Ports** | External: 162->162 External: 162->162 |


**Environment:**

```
TZ=${TZ:-UTC}
PUID=${PUID:-1000}
PGID=${PGID:-1000}
DB_HOST=db
DB_NAME=librenms
DB_USER=librenms
DB_PASSWORD=${LIBRENMS_DB_PASSWORD}
DB_TIMEOUT=60
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
BASE_URL=https://librenms.${BASE_DOMAIN}
SIDECAR_SNMPTRAPD=1
```


**Volumes:**

- `librenms-data:/data`


---


## Network Flow

```mermaid
sankey-beta
    External Scope, snmptrapd, 1
    External Scope, syslogng, 1
    Net: librenms-internal, db, 1
    Net: librenms-internal, dispatcher, 1
    Net: librenms-internal, librenms, 1
    Net: librenms-internal, redis, 1
    Net: traefik-public, librenms, 1
```
<!-- DOCKUMENTOR END -->
