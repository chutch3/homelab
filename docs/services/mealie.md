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
    mealie["<b>mealie</b><br/><i>mealie:v3.9.2</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant mealie as mealie
```

---

## Services


### mealie

**Image:** `ghcr.io/mealie-recipes/mealie:v3.9.2`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
ALLOW_SIGNUP=false
PUID=1000
PGID=1000
TZ=${TZ}
BASE_URL=https://mealie.${BASE_DOMAIN}
MAX_WORKERS=1
WEB_CONCURRENCY=1
AUTO_BACKUP_ENABLED=true
OIDC_AUTH_ENABLED=true
OIDC_SIGNUP_ENABLED=true
OIDC_CONFIGURATION_URL=https://auth.${BASE_DOMAIN}/application/o/mealie/.well-known/openid-configuration
OIDC_CLIENT_ID=${MEALIE_OAUTH_CLIENT_ID}
OIDC_CLIENT_SECRET=${MEALIE_OAUTH_CLIENT_SECRET}
OIDC_PROVIDER_NAME=Authentik
OIDC_AUTO_REDIRECT=false
OIDC_ADMIN_GROUP=Mealie Admins
OIDC_USER_GROUP=Mealie Users
```


**Volumes:**

- `mealie_data:/app/data`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, mealie, 1
```
<!-- DOCKUMENTOR END -->
