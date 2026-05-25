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
    cryptpad["<b>cryptpad</b><br/><i>cryptpad:version-2026.2.2</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant cryptpad as cryptpad
```

---

## Services


### cryptpad

**Image:** `cryptpad/cryptpad:version-2026.2.2`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
CPAD_MAIN_DOMAIN=https://cryptpad.${BASE_DOMAIN}
CPAD_SANDBOX_DOMAIN=https://cryptpad-sandbox.${BASE_DOMAIN}
CPAD_CONF=/cryptpad/config/config.js
CPAD_INSTALL_ONLYOFFICE=yes
```


**Volumes:**

- `cryptpad-config:/cryptpad/config`
- `cryptpad-data:/cryptpad/data`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, cryptpad, 1
```
<!-- DOCKUMENTOR END -->
