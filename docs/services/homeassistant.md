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
    homeassistant["<b>homeassistant</b><br/><i>home-assistant:stable</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant homeassistant as homeassistant
```

---

## Services


### homeassistant

**Image:** `ghcr.io/home-assistant/home-assistant:stable`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |



**Volumes:**

- `homeassistant:/config`
- `/etc/localtime:/etc/localtime:ro`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, homeassistant, 1
```
<!-- DOCKUMENTOR END -->
