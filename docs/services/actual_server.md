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
    actual_server["<b>actual_server</b><br/><i>actual-server:26.5.0</i>"]:::internal
    actual_mcp["<b>actual_mcp</b><br/><i>actual-mcp:latest</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant actual_server as actual_server
    participant actual_mcp as actual_mcp
```

---

## Services


### actual_server

**Image:** `docker.io/actualbudget/actual-server:26.5.0`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
ACTUAL_UPLOAD_FILE_SYNC_SIZE_LIMIT_MB=20
ACTUAL_UPLOAD_SYNC_ENCRYPTED_FILE_SYNC_SIZE_LIMIT_MB=50
ACTUAL_UPLOAD_FILE_SIZE_LIMIT_MB=20
DEBUG=actual:config
```


**Volumes:**

- `budget:/data`
- `ssl_certs:/certs`


---

### actual_mcp

**Image:** `sstefanov/actual-mcp:latest`


**Command:** `['--sse']`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
ACTUAL_SERVER_URL=http://actual_server:5006
ACTUAL_PASSWORD=${ACTUAL_PASSWORD}
ACTUAL_BUDGET_SYNC_ID=${ACTUAL_BUDGET_SYNC_ID}
ACTUAL_BUDGET_ENCRYPTION_PASSWORD=${ACTUAL_BUDGET_ENCRYPTION_PASSWORD}
```


**Volumes:**

- `mcp_data:/data`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, actual_mcp, 1
    Net: traefik-public, actual_server, 1
```
<!-- DOCKUMENTOR END -->
