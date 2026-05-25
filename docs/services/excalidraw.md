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
    excalidraw_web["<b>excalidraw-web</b><br/><i>excalidraw:latest</i>"]:::internal
    excalidraw_room["<b>excalidraw-room</b><br/><i>excalidraw-room:latest</i>"]:::internal
    excalidraw_storage["<b>excalidraw-storage</b><br/><i>excalidraw-storage-backend:latest</i>"]:::internal
    excalidraw_db[("<b>excalidraw-db</b><br/><i>postgres:16-alpine</i><br/>💾 Datastore")]:::datastore
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant excalidraw_web as excalidraw-web
    participant excalidraw_room as excalidraw-room
    participant excalidraw_storage as excalidraw-storage
    participant excalidraw_db as excalidraw-db
```

---

## Services


### excalidraw-web

**Image:** `excalidraw/excalidraw:latest`


**Command:** `['-c', 'echo "--- Starting Global Patch ---"\n# Loop through ALL .js files in assets to catch every minified chunk\nfind /usr/share/nginx/html/assets -name \'*.js\' | while read -r file; do\n  echo "Patching $$file..."\n  # 1. Replace the POST URL and remap to /scenes/\n  sed -i "s|https://json.excalidraw.com/api/v2/post/|$$VITE_APP_HTTP_STORAGE_BACKEND_URL/api/v2/scenes/|g" "$$file"\n  # 2. Replace the standard API URL and remap to /scenes/\n  sed -i "s|https://json.excalidraw.com/api/v2/|$$VITE_APP_HTTP_STORAGE_BACKEND_URL/api/v2/scenes/|g" "$$file"\n  # 3. Replace the Collaboration/WebSocket URL\n  sed -i "s|https://oss-collab.excalidraw.com|$$VITE_APP_WS_SERVER_URL|g" "$$file"\ndone\n\n# Delete gzipped files so Nginx is forced to serve our patched versions\nfind /usr/share/nginx/html -name \'*.gz\' -delete\necho "--- Patching Complete ---"\nnginx -g \'daemon off;\'\n']`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
VITE_APP_WS_SERVER_URL=https://excalidraw-room.${BASE_DOMAIN}
VITE_APP_HTTP_STORAGE_BACKEND_URL=https://excalidraw-storage.${BASE_DOMAIN}
```



---

### excalidraw-room

**Image:** `excalidraw/excalidraw-room:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |




---

### excalidraw-storage

**Image:** `ghcr.io/kitsteam/excalidraw-storage-backend:latest`


**Command:** `['/bin/sh', '-c', 'ENCODED_PW=$$(node -e "console.log(encodeURIComponent(process.env.RAW_DB_PASSWORD))")\nexport STORAGE_URI=postgresql://excalidraw:$$ENCODED_PW@excalidraw-db:5432/excalidraw\nnode dist/main\n']`


| Property | Value |
|----------|-------|
| **Networks** | excalidraw-internal, traefik-public |
| **Depends on** | — |


**Environment:**

```
RAW_DB_PASSWORD=${EXCALIDRAW_DB_PASSWORD}
STORAGE_TYPE=postgres
PORT=8080
ALLOWED_ORIGINS=https://excalidraw.${BASE_DOMAIN}
```



---

### excalidraw-db

**Image:** `postgres:16-alpine`


| Property | Value |
|----------|-------|
| **Networks** | excalidraw-internal |
| **Depends on** | — |


**Environment:**

```
POSTGRES_USER=excalidraw
POSTGRES_PASSWORD=${EXCALIDRAW_DB_PASSWORD}
POSTGRES_DB=excalidraw
```


**Volumes:**

- `excalidraw_pgdata:/var/lib/postgresql/data`


---


## Network Flow

```mermaid
sankey-beta
    Net: excalidraw-internal, excalidraw_db, 1
    Net: excalidraw-internal, excalidraw_storage, 1
    Net: traefik-public, excalidraw_room, 1
    Net: traefik-public, excalidraw_storage, 1
    Net: traefik-public, excalidraw_web, 1
```
<!-- DOCKUMENTOR END -->
