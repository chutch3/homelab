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
    runner["<b>runner</b><br/><i>act_runner:latest</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant runner as runner
```

---

## Services


### runner

**Image:** `gitea/act_runner:latest`


| Property | Value |
|----------|-------|
| **Networks** | default |
| **Depends on** | — |


**Environment:**

```
GITEA_INSTANCE_URL=https://git.${BASE_DOMAIN}
GITEA_RUNNER_REGISTRATION_TOKEN=${FORGEJO_RUNNER_TOKEN}
GITEA_RUNNER_NAME=homelab-runner
GITEA_RUNNER_LABELS=ubuntu-latest:docker://node:16-bullseye,self-hosted
```


**Volumes:**

- `runner-data:/data`
- `/var/run/docker.sock:/var/run/docker.sock`


---


## Network Flow

```mermaid
sankey-beta
    Net: default, runner, 1
```
<!-- DOCKUMENTOR END -->
