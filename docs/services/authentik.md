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
    postgresql[("<b>postgresql</b><br/><i>postgres:16-alpine</i><br/>💾 Datastore")]:::datastore
    redis[("<b>redis</b><br/><i>redis:alpine</i><br/>💾 Datastore")]:::datastore
    server["<b>server</b><br/><i>server:2026.5.2</i>"]:::internal
    worker["<b>worker</b><br/><i>server:2026.5.2</i>"]:::internal
    proxy["<b>proxy</b><br/><i>proxy:2026.5.2</i>"]:::internal
    ldap(["<b>ldap</b><br/><i>ldap:2026.5.2</i><br/>🔌 389:3389 | 636:6636"]):::exposed
    server --> postgresql
    server --> redis
    worker --> postgresql
    worker --> redis
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant postgresql as postgresql
    participant redis as redis
    participant server as server
    participant worker as worker
    participant proxy as proxy
    participant ldap as ldap
    server->>postgresql: Connection / Init
    server->>redis: Connection / Init
    worker->>postgresql: Connection / Init
    worker->>redis: Connection / Init
```

---

## Services


### postgresql

**Image:** `docker.io/library/postgres:16-alpine`


| Property | Value |
|----------|-------|
| **Networks** | authentik-internal |
| **Depends on** | — |


**Environment:**

```
POSTGRES_PASSWORD=${AUTHENTIK_POSTGRES_PASSWORD}
POSTGRES_USER=authentik
POSTGRES_DB=authentik
```


**Volumes:**

- `postgresql:/var/lib/postgresql/data`


---

### redis

**Image:** `docker.io/library/redis:alpine`


**Command:** `--save 60 1 --loglevel warning`


| Property | Value |
|----------|-------|
| **Networks** | authentik-internal |
| **Depends on** | — |



**Volumes:**

- `redis:/data`


---

### server

**Image:** `ghcr.io/goauthentik/server:2026.5.2`


**Command:** `server`


| Property | Value |
|----------|-------|
| **Networks** | authentik-internal, traefik-public |
| **Depends on** | postgresql, redis |


**Environment:**

```
AUTHENTIK_REDIS__HOST=redis
AUTHENTIK_POSTGRESQL__HOST=postgresql
AUTHENTIK_POSTGRESQL__USER=authentik
AUTHENTIK_POSTGRESQL__NAME=authentik
AUTHENTIK_POSTGRESQL__PASSWORD=${AUTHENTIK_POSTGRES_PASSWORD}
AUTHENTIK_SECRET_KEY=${AUTHENTIK_SECRET_KEY}
```


**Volumes:**

- `media:/media`
- `custom-templates:/templates`


---

### worker

**Image:** `ghcr.io/goauthentik/server:2026.5.2`


**Command:** `worker`


| Property | Value |
|----------|-------|
| **Networks** | authentik-internal |
| **Depends on** | postgresql, redis |


**Environment:**

```
AUTHENTIK_REDIS__HOST=redis
AUTHENTIK_POSTGRESQL__HOST=postgresql
AUTHENTIK_POSTGRESQL__USER=authentik
AUTHENTIK_POSTGRESQL__NAME=authentik
AUTHENTIK_POSTGRESQL__PASSWORD=${AUTHENTIK_POSTGRES_PASSWORD}
AUTHENTIK_SECRET_KEY=${AUTHENTIK_SECRET_KEY}
```


**Volumes:**

- `/var/run/docker.sock:/var/run/docker.sock`
- `media:/media`
- `certs:/certs`
- `custom-templates:/templates`


---

### proxy

**Image:** `ghcr.io/goauthentik/proxy:2026.5.2`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
AUTHENTIK_HOST=https://auth.${BASE_DOMAIN}
AUTHENTIK_INSECURE=false
AUTHENTIK_TOKEN=${AUTHENTIK_OUTPOST_TOKEN}
```



---

### ldap

**Image:** `ghcr.io/goauthentik/ldap:2026.5.2`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |
| **Ports** | External: 389:3389 External: 636:6636 |


**Environment:**

```
AUTHENTIK_HOST=https://auth.${BASE_DOMAIN}
AUTHENTIK_INSECURE=false
AUTHENTIK_TOKEN=${AUTHENTIK_LDAP_TOKEN}
```



---


## Network Flow

```mermaid
sankey-beta
    External Scope, ldap, 1
    Net: authentik-internal, postgresql, 1
    Net: authentik-internal, redis, 1
    Net: authentik-internal, server, 1
    Net: authentik-internal, worker, 1
    Net: traefik-public, proxy, 1
    Net: traefik-public, server, 1
```
<!-- DOCKUMENTOR END -->
