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
    radarr["<b>radarr</b><br/><i>radarr:version-6.1.1.10360</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant radarr as radarr
```

---

## Services


### radarr

**Image:** `lscr.io/linuxserver/radarr:version-6.1.1.10360`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
PUID=1000
PGID=1000
TZ=${TZ}
```


**Volumes:**

- `radarr_config:/config`
- `torrents:/data/torrents`
- `usenet:/data/usenet`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, radarr, 1
```
<!-- DOCKUMENTOR END -->
