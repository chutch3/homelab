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
    uptime_kuma["<b>uptime-kuma</b><br/><i>uptime-kuma:1</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant uptime_kuma as uptime-kuma
```

---

## Services


### uptime-kuma

**Image:** `louislam/uptime-kuma:1`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |



**Volumes:**

- `uptime-kuma-data:/app/data`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, uptime_kuma, 1
```
<!-- DOCKUMENTOR END -->
