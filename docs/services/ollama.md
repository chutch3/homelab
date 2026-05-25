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
    ollama["<b>ollama</b><br/><i>ollama:latest</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant ollama as ollama
```

---

## Services


### ollama

**Image:** `ollama/ollama:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
OLLAMA_HOST=0.0.0.0
OLLAMA_ORIGINS=*
OLLAMA_DEBUG=1
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
```


**Volumes:**

- `ollama-data:/root/.ollama`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, ollama, 1
```
<!-- DOCKUMENTOR END -->
