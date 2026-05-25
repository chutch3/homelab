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
    emby["<b>emby</b><br/><i>embyserver:4.10.0.5</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant emby as emby
```

---

## Services


### emby

**Image:** `emby/embyserver:4.10.0.5`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
UID=0
GID=1000
GIDLIST=1000
```


**Volumes:**

- `emby:/config`
- `all_data:/mnt/external`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, emby, 1
```
<!-- DOCKUMENTOR END -->
