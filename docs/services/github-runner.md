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
    github_runner["<b>github-runner</b><br/><i>github-runner:latest</i>"]:::internal
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant github_runner as github-runner
```

---

## Services


### github-runner

**Image:** `myoung34/github-runner:latest`


| Property | Value |
|----------|-------|
| **Networks** | traefik-public |
| **Depends on** | — |


**Environment:**

```
REPO_URL=https://github.com/${GITHUB_USERNAME}/${GITHUB_REPO:-homelab}
ACCESS_TOKEN=${GITHUB_TOKEN}
RUNNER_NAME=homelab-gh-runner
RUNNER_OPTIMIZE_REPOSITORY_CHECKOUT=true
DOCKER_ENABLED=true
```


**Volumes:**

- `/var/run/docker.sock:/var/run/docker.sock`
- `github-runner-data:/data`


---


## Network Flow

```mermaid
sankey-beta
    Net: traefik-public, github_runner, 1
```
<!-- DOCKUMENTOR END -->
