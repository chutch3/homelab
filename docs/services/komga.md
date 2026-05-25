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
    komga(["<b>komga</b><br/><i>komga:latest</i><br/>🔌 25600:25600"]):::exposed
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant komga as komga
```

---

## Services


### komga

**Image:** `gotson/komga:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |
| **Ports** | External: 25600:25600 |


**Environment:**

```
TZ=${TZ}
KOMGA_ADMIN_EMAIL=${KOMGA_ADMIN_EMAIL}
KOMGA_ADMIN_PASSWORD=${KOMGA_ADMIN_PASSWORD}
KOMGA_OAUTH2ACCOUNTCREATION=true
SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_AUTHENTIK_PROVIDER=authentik
SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_AUTHENTIK_CLIENT_NAME=Authentik
SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_AUTHENTIK_CLIENT_ID=${KOMGA_OAUTH2_CLIENT_ID}
SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_AUTHENTIK_CLIENT_SECRET=${KOMGA_OAUTH2_CLIENT_SECRET}
SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_AUTHENTIK_SCOPE=openid,email,profile
SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_AUTHENTIK_AUTHORIZATION_GRANT_TYPE=authorization_code
SPRING_SECURITY_OAUTH2_CLIENT_PROVIDER_AUTHENTIK_ISSUER_URI=https://auth.${BASE_DOMAIN}/application/o/komga/
SPRING_SECURITY_OAUTH2_CLIENT_PROVIDER_AUTHENTIK_USER_NAME_ATTRIBUTE=preferred_username
```


**Volumes:**

- `komga_config:/config`
- `all_data:/data`


---


## Network Flow

```mermaid
sankey-beta
    External Scope, komga, 1
```
<!-- DOCKUMENTOR END -->
