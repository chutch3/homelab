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
    freshrss["<b>freshrss</b><br/><i>freshrss:latest</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant freshrss as freshrss
```

---

## Services


### freshrss

**Image:** `freshrss/freshrss:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
TZ=${TZ}
FRESHRSS_ENV=production
CRON_MIN=4,34
FRESHRSS_INSTALL=--api-enabled --auth-type http_auth --default-user ${FRESHRSS_DEFAULT_USER:-admin}
FRESHRSS_USER=--user ${FRESHRSS_DEFAULT_USER:-admin} --password ${FRESHRSS_ADMIN_PASSWORD} --api-password ${FRESHRSS_ADMIN_API_PASSWORD} --email ${FRESHRSS_ADMIN_EMAIL}
OIDC_ENABLED=1
OIDC_PROVIDER_METADATA_URL=https://auth.${BASE_DOMAIN}/application/o/freshrss/.well-known/openid-configuration
OIDC_CLIENT_ID=${FRESHRSS_OAUTH_CLIENT_ID}
OIDC_CLIENT_SECRET=${FRESHRSS_OAUTH_CLIENT_SECRET}
OIDC_CLIENT_CRYPTO_KEY=${FRESHRSS_OAUTH_CRYPTO_KEY}
OIDC_SCOPES=openid email profile
OIDC_REMOTE_USER_CLAIM=preferred_username
OIDC_X_FORWARDED_HEADERS=X-Forwarded-Host X-Forwarded-Port X-Forwarded-Proto
TRUSTED_PROXY=${FRESHRSS_TRUSTED_PROXY:-10.0.0.0/8}
```


**Volumes:**

- `freshrss_data:/var/www/FreshRSS/data`
- `freshrss_extensions:/var/www/FreshRSS/extensions`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, freshrss, 1
```
<!-- DOCKUMENTOR END -->
