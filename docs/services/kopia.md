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
    kopia["<b>kopia</b><br/><i>kopia:latest</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant kopia as kopia
```

---

## Services


### kopia

**Image:** `kopia/kopia:latest`


**Command:** `['server', 'start', '--insecure', '--address=0.0.0.0:51515', '--server-username=${KOPIA_SERVER_USERNAME}', '--server-password=${KOPIA_SERVER_PASSWORD}']`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
KOPIA_PASSWORD=${KOPIA_PASSWORD}
TZ=${TZ}
```


**Volumes:**

- `kopia_config:/app/config`
- `kopia_cache:/app/cache`
- `app_data:/data/app-data`
- `media_apps:/data/media-apps`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, kopia, 1
```
<!-- DOCKUMENTOR END -->
