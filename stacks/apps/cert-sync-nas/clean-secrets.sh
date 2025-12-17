#!/bin/bash
set -e

# Cleanup script for cert-sync-nas stack
# Removes Docker secret

SECRET_NAME="cert_sync_ssh_key"

echo "🧹 Cleaning up cert-sync-nas resources..."

# Remove secret
if docker secret ls --format '{{.Name}}' | grep -q "^${SECRET_NAME}$"; then
    echo "🗑️  Removing Docker secret '${SECRET_NAME}'..."
    docker secret rm "${SECRET_NAME}"
    echo "✅ Secret removed"
else
    echo "ℹ️  Secret '${SECRET_NAME}' does not exist"
fi

echo "🎉 Cleanup complete!"
