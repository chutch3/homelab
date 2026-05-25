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
    api["<b>api</b><br/><i>librechat-dev-api:latest</i>"]:::internal
    mongodb(["<b>mongodb</b><br/><i>mongodb-no-avx</i><br/>🔌 27017:27017"]):::exposed
    meilisearch["<b>meilisearch</b><br/><i>meilisearch:v1.12.3</i>"]:::internal
    vectordb[("<b>vectordb</b><br/><i>pgvector:latest</i><br/>💾 Datastore")]:::datastore
    rag_api["<b>rag_api</b><br/><i>librechat-rag-api-dev:latest</i>"]:::internal
    api --> rag_api
    api --> meilisearch
    api --> mongodb
    api --> vectordb
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant api as api
    participant mongodb as mongodb
    participant meilisearch as meilisearch
    participant vectordb as vectordb
    participant rag_api as rag_api
    api->>mongodb: Connection / Init
    api->>meilisearch: Connection / Init
    api->>vectordb: Connection / Init
    api->>rag_api: Connection / Init
```

---

## Services


### api

**Image:** `ghcr.io/danny-avila/librechat-dev-api:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | mongodb, meilisearch, vectordb, rag_api |


**Environment:**

```
HOST=0.0.0.0
NODE_ENV=production
MONGO_URI=mongodb://mongodb:27017/LibreChat
MEILI_HOST=http://meilisearch:7700
RAG_PORT=${RAG_PORT:-8000}
RAG_API_URL=http://rag_api:${RAG_PORT:-8000}
```


**Volumes:**

- `librechat_images:/app/client/public/images`
- `librechat_uploads:/app/uploads`
- `librechat_logs:/app/api/logs`


---

### mongodb

**Image:** `nertworkweb/mongodb-no-avx`


**Command:** `--noauth --bind_ip_all`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |
| **Ports** | External: 27017:27017 |



**Volumes:**

- `librechat_mongodb:/data/db`


---

### meilisearch

**Image:** `getmeili/meilisearch:v1.12.3`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
MEILI_NO_ANALYTICS=true
```


**Volumes:**

- `librechat_meilisearch:/meili_data`


---

### vectordb

**Image:** `ankane/pgvector:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
POSTGRES_DB=mydatabase
POSTGRES_USER=myuser
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
PGDATA=/var/lib/postgresql/data/pgdata
```


**Volumes:**

- `librechat_vectordb:/var/lib/postgresql/data`


---

### rag_api

**Image:** `ghcr.io/danny-avila/librechat-rag-api-dev:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
DB_HOST=vectordb
RAG_PORT=${RAG_PORT:-8000}
RAG_API_URL=http://host.docker.internal:8000
EMBEDDINGS_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
EMBEDDINGS_MODEL=nomic-embed-text
POSTGRES_DB=mydatabase
POSTGRES_USER=myuser
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
```



---


## Network Flow

```mermaid
sankey-beta
    External Scope, mongodb, 1
    Net: traefik-public, api, 1
    Net: traefik-public, meilisearch, 1
    Net: traefik-public, rag_api, 1
    Net: traefik-public, vectordb, 1
```
<!-- DOCKUMENTOR END -->
