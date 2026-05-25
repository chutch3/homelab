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
    mlflow["<b>mlflow</b><br/><i>mlflow:v2.10.1</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant mlflow as mlflow
```

---

## Services


### mlflow

**Image:** `ghcr.io/mlflow/mlflow:v2.10.1`


**Command:** `mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri file:///mlflow/backend --default-artifact-root file:///mlflow/artifacts
`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
TZ=${TZ}
```


**Volumes:**

- `mlflow_data:/mlflow`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, mlflow, 1
```
<!-- DOCKUMENTOR END -->
