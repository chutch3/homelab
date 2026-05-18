#!/usr/bin/env bash
set -euo pipefail

ISCSI_APP_DATA="/mnt/iscsi/app-data/librenms"
ISCSI_CACHE="/mnt/iscsi/cache"

# Load environment variables if available
if [ -f "../../../.env" ]; then
    source "../../../.env"
fi

PUID="${UID:-1000}"
PGID="${GID:-1000}"

echo "Creating LibreNMS directories..."
mkdir -p "$ISCSI_APP_DATA/db"
mkdir -p "$ISCSI_APP_DATA/data"
mkdir -p "$ISCSI_CACHE/librenms-redis"

echo "Setting ownership..."
# MariaDB and Redis run as UID/GID 999 in their official images
chown -R 999:999 "$ISCSI_APP_DATA/db"
chown -R 999:999 "$ISCSI_CACHE/librenms-redis"
# LibreNMS app uses PUID/PGID from environment
chown -R "$PUID:$PGID" "$ISCSI_APP_DATA/data"

echo "Setup complete! Deploy with: task ansible:deploy:stack -- -e \"stack_name=librenms\""
