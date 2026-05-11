#!/usr/bin/env bash
set -euo pipefail

# Define the root of the dev environment
DEV_ENV_ROOT="/mnt/iscsi/app-data/dev-env"

echo "Creating Dev Environment Directories..."
mkdir -p "$DEV_ENV_ROOT/workspace"
mkdir -p "$DEV_ENV_ROOT/code-server/config"
mkdir -p "$DEV_ENV_ROOT/shared-ssh"
mkdir -p "$DEV_ENV_ROOT/ai-configs/claude"
mkdir -p "$DEV_ENV_ROOT/ai-configs/gemini"
mkdir -p "$DEV_ENV_ROOT/ai-configs/cloudcli"
mkdir -p "$DEV_ENV_ROOT/ai-configs/forge"

echo "Setting Ownership to 1000:1000..."
chown -R 1000:1000 "$DEV_ENV_ROOT"

echo "Setting specific permissions for SSH folder..."
chmod 700 "$DEV_ENV_ROOT/shared-ssh"

# Load environment variables if available
if [ -f "../../../.env" ]; then
    source "../../../.env"
fi

# Determine the real user's home directory (in case the script is run with sudo)
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")

# Determine the source SSH key (default to the homelab convention)
SSH_KEY_SRC="${SSH_KEY_FILE:-$REAL_HOME/.ssh/homelab_rsa}"
SSH_DEST="$DEV_ENV_ROOT/shared-ssh"

echo "Copying Homelab SSH Key from $SSH_KEY_SRC to Shared SSH Volume..."
if [ -f "$SSH_KEY_SRC" ]; then
    # Copy private key
    cp "$SSH_KEY_SRC" "$SSH_DEST/homelab_rsa"
    chmod 600 "$SSH_DEST/homelab_rsa"
    chown 1000:1000 "$SSH_DEST/homelab_rsa"

    # Copy public key if it exists
    if [ -f "${SSH_KEY_SRC}.pub" ]; then
        cp "${SSH_KEY_SRC}.pub" "$SSH_DEST/homelab_rsa.pub"
        chmod 644 "$SSH_DEST/homelab_rsa.pub"
        chown 1000:1000 "$SSH_DEST/homelab_rsa.pub"
    fi
    echo "SSH key copied successfully."
else
    echo "Warning: SSH key not found at $SSH_KEY_SRC."
    echo "You may need to manually copy your key or generate a new one inside the Web IDE."
fi

# Setup SSH config file
SSH_CONFIG_DEST="$SSH_DEST/config"
echo "Creating default SSH config..."

cat > "$SSH_CONFIG_DEST" <<EOF
Host 192.168.* 10.* *.diyhub.dev cody-* giant imac mini
    StrictHostKeyChecking accept-new
    IdentityFile ~/.ssh/homelab_rsa

Host *
    StrictHostKeyChecking accept-new
EOF

chmod 644 "$SSH_CONFIG_DEST"
chown 1000:1000 "$SSH_CONFIG_DEST"

echo "Setup complete! You can now deploy the dev environment stacks."
