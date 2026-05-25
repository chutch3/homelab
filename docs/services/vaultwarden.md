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
    vaultwarden["<b>vaultwarden</b><br/><i>server:latest</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant vaultwarden as vaultwarden
```

---

## Services


### vaultwarden

**Image:** `vaultwarden/server:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
DOMAIN=https://vaultwarden.${BASE_DOMAIN}
ADMIN_TOKEN=${VAULTWARDEN_ADMIN_TOKEN:-some-random-token-change-me}
SSO_ENABLED=true
SSO_ONLY=false
SSO_AUTHORITY=https://auth.${BASE_DOMAIN}/application/o/vaultwarden/
SSO_CLIENT_ID=${VAULTWARDEN_OAUTH_CLIENT_ID}
SSO_CLIENT_SECRET=${VAULTWARDEN_OAUTH_CLIENT_SECRET}
SSO_SCOPES=openid email profile
```


**Volumes:**

- `vaultwarden-data:/data`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, vaultwarden, 1
```
<!-- DOCKUMENTOR END -->
