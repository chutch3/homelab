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
    code_server["<b>code-server</b><br/><i>homelab-devbox:${IMAGE_TAG:-latest}</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant code_server as code-server
```

---

## Services


### code-server

**Image:** `${REGISTRY_URL:-ghcr.io}/${GITHUB_USERNAME}/homelab-devbox:${IMAGE_TAG:-latest}`


**Command:** `code-server --auth none --bind-addr 0.0.0.0:3001 /home/coder/workspace`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
TZ=${TZ:-America/New_York}
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
```


**Volumes:**

- `code_server_config:/home/coder/.config/code-server`
- `workspace:/home/coder/workspace`
- `shared_ssh:/home/coder/.ssh`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, code_server, 1
```
<!-- DOCKUMENTOR END -->
