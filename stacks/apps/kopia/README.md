# Kopia Backup - Docker Swarm

Automated backup system for application data running in Docker Swarm.

## Overview

This Kopia instance runs in Docker Swarm and backs up:
- `/mnt/iscsi/app-data` - Application data (databases, configs)
- `/mnt/iscsi/media-apps` - Media application data

Connects to a remote storage backend (Backblaze B2, S3, etc.) for offsite backups.

## Access

- Web UI: `https://backup.${BASE_DOMAIN}`
- Authentication: Authentik SSO (forward auth via Traefik)
- Note: Basic auth credentials (`KOPIA_SERVER_USERNAME`/`KOPIA_SERVER_PASSWORD`) are still required for API access and CLI operations

## Deployment

### Prerequisites

1. **Authentik Configuration**:
   - The service uses Authentik forward auth middleware (`authentik@swarm`) for web UI access
   - Users will authenticate through Authentik before accessing the Kopia web UI

2. **Environment variables** in root `.env` file:
   ```bash
   KOPIA_PASSWORD=<repository-password>          # Repository encryption password
   KOPIA_SERVER_USERNAME=<web-ui-username>       # For API/CLI access
   KOPIA_SERVER_PASSWORD=<web-ui-password>       # For API/CLI access
   ```

3. **Storage Backend Credentials** (e.g., Backblaze B2 key ID and application key)

### Deploy Stack

```bash
task ansible:deploy:stack -- -e "stack_name=kopia"
```

### Connect to Repository

After deploying, connect to your storage backend:

```bash
# Get the container ID
CONTAINER_ID=$(docker ps -q -f label=com.docker.swarm.service.name=kopia_kopia)

# Connect to B2 repository (example)
docker exec -it $CONTAINER_ID kopia repository connect b2 \
  --bucket=<YOUR_B2_BUCKET> \
  --key-id=<B2_KEY_ID> \
  --key=<B2_APPLICATION_KEY>

# Or connect to S3-compatible storage
# docker exec -it $CONTAINER_ID kopia repository connect s3 \
#   --bucket=<YOUR_S3_BUCKET> \
#   --endpoint=<S3_ENDPOINT> \
#   --access-key=<ACCESS_KEY> \
#   --secret-access-key=<SECRET_KEY>
```

## Initial Configuration

After connecting to the repository, configure backup policies and create initial snapshots.

### 1. Exclude PostgreSQL directories

**IMPORTANT**: PostgreSQL data directories should NOT be backed up while the database is running, as file-based backups can be inconsistent. Exclude these directories from Kopia backups:

```bash
# Get the container ID
CONTAINER_ID=$(docker ps -q -f label=com.docker.swarm.service.name=kopia_kopia)

# Exclude PostgreSQL directories from backups
docker exec -it $CONTAINER_ID kopia policy set /data/app-data \
  --add-ignore "**/postgresql/"

# Verify exclusions
docker exec -it $CONTAINER_ID kopia policy show /data/app-data
```

This will exclude:
- `/mnt/iscsi/app-data/authentik/postgresql`
- `/mnt/iscsi/app-data/forgejo/postgresql`
- Any other `*/postgresql/` directories

### 2. Set up backup policies

```bash
# Get the container ID
CONTAINER_ID=$(docker ps -q -f label=com.docker.swarm.service.name=kopia_kopia)

# Set policy for app-data (weekly backups, keep 4 weekly + 3 monthly)
docker exec -it $CONTAINER_ID kopia policy set /data/app-data \
  --snapshot-interval 168h \
  --keep-daily 0 --keep-weekly 4 --keep-monthly 3

# Set policy for media-apps (weekly backups, keep 4 weekly + 3 monthly)
docker exec -it $CONTAINER_ID kopia policy set /data/media-apps \
  --snapshot-interval 168h \
  --keep-daily 0 --keep-weekly 4 --keep-monthly 3
```

### 3. Create initial snapshots

```bash
# Create initial backups
docker exec -it $CONTAINER_ID kopia snapshot create /data/app-data
docker exec -it $CONTAINER_ID kopia snapshot create /data/media-apps
```

## Backup Schedule

Backups run automatically based on the configured snapshot interval (168h = weekly):
- **app-data**: Weekly automated backups via Kopia's internal scheduler
- **media-apps**: Weekly automated backups via Kopia's internal scheduler

Retention policy: Keep 4 weekly + 3 monthly snapshots

## Architecture Notes

This Kopia instance is designed to back up live application data from Docker Swarm services:
- Backs up application data via iSCSI mounts (`/mnt/iscsi/app-data`, `/mnt/iscsi/media-apps`)
- Suitable for smaller, frequently changing datasets
- Uses weekly automated backups with retention policies

If you have a separate NAS or file server, consider running a separate Kopia instance to back up large static files (media, photos, documents) to the same repository.

## Troubleshooting

Get the container ID for all commands:
```bash
CONTAINER_ID=$(docker ps -q -f label=com.docker.swarm.service.name=kopia_kopia)
```

### Check service status
```bash
docker service ps kopia_kopia
docker service logs -f kopia_kopia
```

### List snapshots
```bash
docker exec -it $CONTAINER_ID kopia snapshot list
```

### Check policies
```bash
docker exec -it $CONTAINER_ID kopia policy list
```

### Manual snapshot
```bash
docker exec -it $CONTAINER_ID kopia snapshot create /data/app-data
```

### Repository info
```bash
docker exec -it $CONTAINER_ID kopia repository status
```


### OMV docker compose to run kopia for large file backup
```yaml
services:
    kopia:
        image: kopia/kopia:latest
        container_name: kopia
        hostname: ac28fa6b7599 # this must be the same as what is configured in the repository
        restart: unless-stopped
        environment:
            - KOPIA_PASSWORD=${KOPIA_PASSWORD} # repository encryption password
        ports:
            - "51515:51515"
        volumes:
            # 1. Config & Cache
            - CHANGE_TO_COMPOSE_DATA_PATH/kopia/config:/app/config
            - CHANGE_TO_COMPOSE_DATA_PATH/kopia/cache:/app/cache

            # 2. SSL Certificates (from OMV certificate management)
            - ${HOST_SSL_CERT}:/certs/cert.crt:ro
            - ${HOST_SSL_KEY}:/certs/cert.key:ro

            # 3. Your Actual Data (The "Window")
            # Set these in your OMV .env files:
            # - DISK1_ALL_DATA_PATH (large media files: home_videos, home_photos, media, sambashare, budget)
            # - DISK2_GOOGLE_PHOTOS_PATH (static Google Photos export)
            # Note: app-data and media-apps are backed up by Swarm Kopia instance
            # - ${DISK1_ALL_DATA_PATH}:/data/all_data:ro
            # - ${DISK2_GOOGLE_PHOTOS_PATH}:/data/google_photos_takeout:ro
        command:
            - server
            - start
            - --tls-cert-file=/certs/cert.crt
            - --tls-key-file=/certs/cert.key
            - --address=0.0.0.0:51515
            - --server-username=${KOPIA_SERVER_USERNAME}
            - --server-password=${KOPIA_SERVER_PASSWORD}
```
