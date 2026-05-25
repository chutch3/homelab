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
    profilarr["<b>profilarr</b><br/><i>profilarr:latest</i>"]:::internal
    profilarr_backup["<b>profilarr-backup</b><br/><i>alpine:latest</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant profilarr as profilarr
    participant profilarr_backup as profilarr-backup
```

---

## Services


### profilarr

**Image:** `santiagosayshey/profilarr:latest`


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

- `profilarr_config:/config`


---

### profilarr-backup

**Image:** `alpine:latest`


**Command:** `['/bin/sh', '/backup.sh']`


| Property | Value |
|----------|-------|
| **Networks** | default |
| **Depends on** | — |


**Environment:**

```
TZ=${TZ}
```


**Volumes:**

- `profilarr_config:/source:ro`
- `profilarr_nas_backup:/dest`
- `./backup.sh:/backup.sh:ro`


---


## Network Flow

```mermaid
sankey-beta
    Net: default, profilarr_backup, 1
    Net: traefik-public, profilarr, 1
```
<!-- DOCKUMENTOR END -->
