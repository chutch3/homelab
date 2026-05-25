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
    database[("<b>database</b><br/><i>postgres:15-alpine</i><br/>💾 Datastore")]:::datastore
    server(["<b>server</b><br/><i>prefect:3-python3.11</i><br/>🔌 4200:4200"]):::exposed
    worker["<b>worker</b><br/><i>prefect:3-python3.11</i>"]:::internal
    server --> database
    worker --> server
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant database as database
    participant server as server
    participant worker as worker
    server->>database: Connection / Init
    worker->>server: Connection / Init
```

---

## Services


### database

**Image:** `postgres:15-alpine`


| Property | Value |
|----------|-------|
| **Networks** | prefect-internal |
| **Depends on** | — |


**Environment:**

```
POSTGRES_USER=prefect
POSTGRES_PASSWORD=${PREFECT_DB_PASSWORD}
POSTGRES_DB=prefect
```


**Volumes:**

- `db-data:/var/lib/postgresql/data`


---

### server

**Image:** `prefecthq/prefect:3-python3.11`


**Command:** `prefect server start`


| Property | Value |
|----------|-------|
| **Networks** | prefect-internal, traefik-public |
| **Depends on** | database |
| **Ports** | External: 4200:4200 |


**Environment:**

```
PREFECT_UI_API_URL=https://prefect.${BASE_DOMAIN}/api
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://prefect:${PREFECT_DB_PASSWORD}@database:5432/prefect
PREFECT_SERVER_API_HOST=0.0.0.0
PREFECT_DOCKER_MODE=true
```


**Volumes:**

- `prefect-config:/root/.prefect`


---

### worker

**Image:** `prefecthq/prefect:3-python3.11`


**Command:** `sh -c "pip install prefect-docker --quiet &&
      prefect worker start --pool $${PREFECT_WORK_POOL}"
`


| Property | Value |
|----------|-------|
| **Networks** | prefect-internal |
| **Depends on** | server |


**Environment:**

```
PREFECT_API_URL=http://server:4200/api
PREFECT_WORK_POOL=${PREFECT_WORK_POOL:-crime-pipeline-docker}
```


**Volumes:**

- `{'type': 'bind', 'source': '/var/run/docker.sock', 'target': '/var/run/docker.sock'}`
- `{'type': 'bind', 'source': '/home/chutchens/.docker/config.json', 'target': '/root/.docker/config.json', 'read_only': True}`


---


## Network Flow

```mermaid
sankey-beta
    External Scope, server, 1
    Net: prefect-internal, database, 1
    Net: prefect-internal, worker, 1
```
<!-- DOCKUMENTOR END -->
