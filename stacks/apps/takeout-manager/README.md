# Google Photos Takeout Manager

A distributed service for automating the download, extraction, and organization of Google Photos Takeout archives.

## Overview

This service provides a web-based solution for managing Google Photos Takeout jobs across a Docker Swarm cluster. It consists of two components:

- **Manager**: FastAPI backend with Vue.js frontend for job creation, monitoring, and management
- **Worker**: Distributed workers that download and extract Takeout archives across all Swarm nodes

### Architecture

```mermaid
graph TB
    subgraph "Manager Service"
        Manager["Manager<br/>(FastAPI + Vue.js)"]
        DB["SQLite Database<br/>(iSCSI Storage)"]
        Manager --> DB
    end

    subgraph "Worker Services (Global Mode)"
        Worker1["Worker<br/>(Node 1)"]
        Worker2["Worker<br/>(Node 2)"]
        Worker3["Worker<br/>(Node 3)"]
        WorkerN["Worker<br/>(Node N)"]
    end

    subgraph "Storage (NAS)"
        Downloads["Downloads Share<br/>(CIFS/SMB)"]
        Pictures["Pictures Share<br/>(CIFS/SMB)"]
        Videos["Videos Share<br/>(CIFS/SMB)"]
    end

    Manager -->|Distribute Tasks| Worker1
    Manager -->|Distribute Tasks| Worker2
    Manager -->|Distribute Tasks| Worker3
    Manager -->|Distribute Tasks| WorkerN

    Worker1 --> Downloads
    Worker2 --> Downloads
    Worker3 --> Downloads
    WorkerN --> Downloads

    Worker1 --> Pictures
    Worker2 --> Pictures
    Worker3 --> Pictures
    WorkerN --> Pictures

    Worker1 --> Videos
    Worker2 --> Videos
    Worker3 --> Videos
    WorkerN --> Videos
```

### Features

- **Distributed downloads**: Workers run on all Swarm nodes for parallel chunk downloads
- **Web UI**: Create jobs, monitor progress, update cookies, and retry failed chunks
- **Automatic organization**: Sorts extracted files into photos and videos directories
- **Resumable**: Jobs can be paused and resumed with updated authentication cookies
- **Real-time monitoring**: Live progress tracking with auto-refresh

## Why This Exists

Google Photos Takeout exports can be 100+ GB and consist of dozens of archive chunks that expire after a short time. Manually downloading and extracting these archives is time-consuming and error-prone. This service automates the entire process:

1. Distributes downloads across multiple nodes for faster completion
2. Automatically extracts and organizes media files by type
3. Provides visibility into progress and failures
4. Allows cookie updates when authentication expires
5. Enables retry of failed chunks without starting over

## Prerequisites

- Docker Swarm cluster initialized
- iSCSI block storage mounted at `/mnt/iscsi/app-data/takeout-manager` (for SQLite database)
- SMB/CIFS shares configured:
  - Downloads: `//${NAS_SERVER}/google_photos_takeout`
  - Pictures: `//${NAS_SERVER}/all_data/google_photos_pictures`
  - Videos: `//${NAS_SERVER}/all_data/google_photos_videos`
- Container registry (GitHub Container Registry, Docker Hub, or private registry)
- GitHub Personal Access Token with `write:packages` and `read:packages` scopes (if using GHCR)

## Configuration

Configure environment variables in your `.env` file:

```bash
# Registry Configuration
REGISTRY_URL=ghcr.io
REGISTRY_NAMESPACE=your-github-username
IMAGE_TAG=latest

# Storage Configuration
SMB_USERNAME=your_smb_username
SMB_PASSWORD=your_smb_password
SMB_DOMAIN=your_domain
NAS_SERVER=nas.example.com

# Domain Configuration
BASE_DOMAIN=example.com
TZ=America/New_York
PUID=1000
PGID=1000
```

## Deployment Commands

### 1. Login to Container Registry

Login all Swarm nodes to your container registry:

```bash
# Set credentials
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export GITHUB_USERNAME=your-github-username

# Login all nodes
task ansible:registry:login
```

For other registries:
```bash
# Docker Hub
export REGISTRY_URL=docker.io
export REGISTRY_USER=your-username
export REGISTRY_PASS=your-password
task ansible:registry:login:custom

# Private registry
export REGISTRY_URL=registry.example.com
export REGISTRY_USER=admin
export REGISTRY_PASS=your-password
task ansible:registry:login:custom
```

### 2. Build and Push Images

From the `stacks/apps/takeout-manager` directory:

```bash
# Show current configuration
task config

# Login to registry (local)
task login

# Build images locally (no push)
task build

# Build and push to registry
task publish

# Build and push specific version
task release VERSION=v1.0.0
```

### 3. Deploy to Docker Swarm

From the homelab root directory:

```bash
# Deploy the stack
task ansible:deploy:stack -- -e "stack_name=takeout-manager"

# Verify deployment
docker stack ps takeout-manager

# Check logs
docker service logs takeout-manager_takeout-manager -f
docker service logs takeout-manager_takeout-worker -f
```

### 4. Access the UI

Once deployed, access the web interface at:
```
https://takeout.${BASE_DOMAIN}
```

## Available Tasks

View all available tasks from the `stacks/apps/takeout-manager` directory:

```bash
task --list
```

Common tasks:
- `task config` - Show current registry configuration
- `task login` - Login to container registry
- `task build` - Build images locally
- `task publish` - Build and push to registry
- `task release VERSION=v1.0.0` - Build and push versioned release
- `task help` - Show detailed usage examples

## Local Development

For local testing and development:

```bash
# Terminal 1: Start the manager API
cd manager
poetry install
poetry run uvicorn app.main:app --reload --port 8000

# Terminal 2: Start the frontend dev server
cd manager/frontend
npm install
npm run dev

# Terminal 3 (optional): Start a worker
cd worker
poetry install
MANAGER_URL=http://localhost:8000 poetry run python main.py
```

Access the development UI at `http://localhost:5173`.

## Storage Requirements

- **Manager Database**: SQLite on iSCSI block storage (high-performance required)
- **Downloads**: CIFS/SMB share for storing `.tgz` archive chunks
- **Pictures**: CIFS/SMB share for extracted photo files
- **Videos**: CIFS/SMB share for extracted video files

## How It Works

1. **Job Creation**: User creates a job via web UI with Google Takeout parameters
2. **Chunk Distribution**: Manager creates download tasks for each archive chunk
3. **Download Phase**: Workers fetch chunks from Google and save to `/downloads`
4. **Extraction Phase**: Workers extract archives and sort files by type
5. **Organization**: Photos go to `/pictures`, videos to `/videos`
6. **Completion**: Job status updates and UI shows final results

## Troubleshooting

**Images not found during deployment:**
```bash
# Verify images are pushed
docker manifest inspect ${REGISTRY_URL}/${REGISTRY_NAMESPACE}/takeout-manager:${IMAGE_TAG}

# Re-login all nodes
task ansible:registry:login

# Rebuild and push
cd stacks/apps/takeout-manager
task publish
```

**Manager won't start:**
```bash
# Check iSCSI mount permissions
ls -la /mnt/iscsi/app-data/takeout-manager
sudo chown -R 1000:1000 /mnt/iscsi/app-data/takeout-manager
```

**Worker can't access volumes:**
```bash
# Test SMB connectivity
smbclient -L //${NAS_SERVER} -U ${SMB_USERNAME}

# Check volume mounts
docker volume inspect takeout-manager_takeout-downloads
```
