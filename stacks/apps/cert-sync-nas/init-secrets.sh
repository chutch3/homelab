#!/bin/bash
set -e

# Init script for cert-sync-nas stack
# Creates Docker secret for SSH authentication

# Get script directory and source common scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOMELAB_ROOT="${SCRIPT_DIR}/../../.."
COMMON_DIR="${HOMELAB_ROOT}/scripts/common"

# Source SSH common functions (reuses SSH_KEY_FILE variable)
source "${COMMON_DIR}/ssh.sh"

SECRET_NAME="cert_sync_ssh_key"

echo "🔧 Initializing cert-sync-nas stack..."

# Create SSH secret
if [ ! -f "$SSH_KEY_FILE" ]; then
    echo "❌ Error: SSH key not found at: $SSH_KEY_FILE"
    echo "   Please ensure SSH keys are set up for your infrastructure."
    exit 1
fi

echo "✅ Found SSH key: $SSH_KEY_FILE"

if docker secret ls --format '{{.Name}}' | grep -q "^${SECRET_NAME}$"; then
    echo "✅ Docker secret '${SECRET_NAME}' already exists"
else
    echo "📝 Creating Docker secret '${SECRET_NAME}'..."
    docker secret create "${SECRET_NAME}" "$SSH_KEY_FILE"
    echo "✅ Docker secret created successfully"
fi

echo "🎉 Initialization complete! Stack is ready to deploy."
echo "   Scripts are mounted directly from: ${SCRIPT_DIR}/sync-nas-cert.sh"
