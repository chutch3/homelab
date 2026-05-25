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
    takeout_manager["<b>takeout-manager</b><br/><i>takeout-manager:${TAKEOUT_MANAGER_IMAGE_TAG:-latest}</i>"]:::internal
    takeout_worker["<b>takeout-worker</b><br/><i>takeout-worker:${TAKEOUT_MANAGER_IMAGE_TAG:-latest}</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant takeout_manager as takeout-manager
    participant takeout_worker as takeout-worker
```

---

## Services


### takeout-manager

**Image:** `${TAKEOUT_MANAGER_REGISTRY_URL:-ghcr.io}/${TAKEOUT_MANAGER_REGISTRY_NAMESPACE:-your-username}/takeout-manager:${TAKEOUT_MANAGER_IMAGE_TAG:-latest}`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
TZ=${TZ:-UTC}
PUID=${PUID:-1000}
PGID=${PGID:-1000}
```


**Volumes:**

- `takeout-manager-db:/app/db`


---

### takeout-worker

**Image:** `${TAKEOUT_MANAGER_REGISTRY_URL:-ghcr.io}/${TAKEOUT_MANAGER_REGISTRY_NAMESPACE:-your-username}/takeout-worker:${TAKEOUT_MANAGER_IMAGE_TAG:-latest}`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
TZ=${TZ:-UTC}
PUID=${PUID:-1000}
PGID=${PGID:-1000}
MANAGER_URL=http://takeout-manager:8000
```


**Volumes:**

- `takeout-downloads:/downloads`
- `takeout-pictures:/pictures`
- `takeout-videos:/videos`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, takeout_manager, 1
    Net: traefik-public, takeout_worker, 1
```
<!-- DOCKUMENTOR END -->
