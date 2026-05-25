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
    kolibri["<b>kolibri</b><br/><i>kolibri-oidc:${IMAGE_TAG:-latest}</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant kolibri as kolibri
```

---

## Services


### kolibri

**Image:** `${REGISTRY_URL:-ghcr.io}/${REGISTRY_NAMESPACE:-your-username}/kolibri-oidc:${IMAGE_TAG:-latest}`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
TZ=${TZ:-UTC}
PUID=${PUID:-1000}
PGID=${PGID:-1000}
KOLIBRI_HTTP_PORT=8080
CLIENT_ID=${KOLIBRI_OAUTH_CLIENT_ID}
CLIENT_SECRET=${KOLIBRI_OAUTH_CLIENT_SECRET}
KOLIBRI_OIDC_AUTHORIZATION_ENDPOINT=https://auth.${BASE_DOMAIN}/application/o/authorize/
KOLIBRI_OIDC_TOKEN_ENDPOINT=https://auth.${BASE_DOMAIN}/application/o/token/
KOLIBRI_OIDC_USERINFO_ENDPOINT=https://auth.${BASE_DOMAIN}/application/o/userinfo/
KOLIBRI_OIDC_JWKS_ENDPOINT=https://auth.${BASE_DOMAIN}/application/o/kolibri/jwks/
KOLIBRI_OIDC_ENDSESSION_ENDPOINT=https://auth.${BASE_DOMAIN}/application/o/kolibri/end-session/
KOLIBRI_OIDC_CLIENT_URL=https://kolibri.${BASE_DOMAIN}
```


**Volumes:**

- `kolibri_data:/kolibrihome`
- `kolibri_content:/kolibrihome/content`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, kolibri, 1
```
<!-- DOCKUMENTOR END -->
