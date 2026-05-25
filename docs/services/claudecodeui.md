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
    claudecodeui["<b>claudecodeui</b><br/><i>homelab-devbox:${IMAGE_TAG:-latest}</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant claudecodeui as claudecodeui
```

---

## Services


### claudecodeui

**Image:** `${REGISTRY_URL:-ghcr.io}/${GITHUB_USERNAME}/homelab-devbox:${IMAGE_TAG:-latest}`


**Command:** `/bin/bash -c "export PATH=$$HOME/.local/share/fnm:$$PATH && eval \"\$$(fnm env --use-on-cd)\" && mkdir -p ~/.claude ~/.config/gemini ~/.cloudcli ~/.forge && cloudcli start"`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
TZ=${TZ:-America/New_York}
PORT=3001
NODE_ENV=production
VITE_IS_PLATFORM=true
WORKSPACES_ROOT=/home/coder/workspace
OPENROUTER_KEY=${OPENROUTER_KEY}
```


**Volumes:**

- `workspace:/home/coder/workspace`
- `claude_config:/home/coder/.claude`
- `gemini_config:/home/coder/.config/gemini`
- `cloudcli_config:/home/coder/.cloudcli`
- `forge_config:/home/coder/.forge`
- `shared_ssh:/home/coder/.ssh`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, claudecodeui, 1
```
<!-- DOCKUMENTOR END -->
