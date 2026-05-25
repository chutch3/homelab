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
    flaresolverr(["<b>flaresolverr</b><br/><i>flaresolverr:latest</i><br/>🔌 "]):::exposed
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant flaresolverr as flaresolverr
```

---

## Services


### flaresolverr

**Image:** `ghcr.io/flaresolverr/flaresolverr:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |
| **Ports** | Internal: 8191 |


**Environment:**

```
PUID=1000
PGID=1000
TZ=${TZ}
LOG_LEVEL=${FLARESOLVERR_LOG_LEVEL:-info}
HEADLESS=true
```


**Volumes:**

- `flaresolverr:/config`


---


## Network Flow

```mermaid
sankey-beta
    Internal Scope, flaresolverr, 1
```
<!-- DOCKUMENTOR END -->
