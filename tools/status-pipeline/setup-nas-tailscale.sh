#!/usr/bin/env bash
# One-off: Install and configure Tailscale on the NAS for Funnel.
# Run from the homelab project root.
#
# Usage: ./tools/status-pipeline/setup-nas-tailscale.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Load .env and SSH helpers
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"
    set +a
fi
# shellcheck source=/dev/null
source "$PROJECT_ROOT/lib/ssh.sh"

NAS_SERVER="${NAS_SERVER:?NAS_SERVER is required in .env}"
NAS_USER_HOST="root@${NAS_SERVER}"

nas_exec() {
    ssh_execute --login "$NAS_USER_HOST" "$1"
}

echo "========================================="
echo "  Tailscale Setup for NAS"
echo "========================================="
echo

# 1. Test SSH
log_info "Testing SSH connection to $NAS_USER_HOST..."
if ! ssh_test_connection "$NAS_USER_HOST"; then
    log_error "SSH connection failed — need root SSH access to NAS."
    log_error "Check that root login is enabled in OMV and SSH_KEY_FILE is correct."
    exit 1
fi
log_info "SSH connection OK"

# 2. Check dependencies on NAS
log_info "Checking NAS dependencies..."
if ! nas_exec "command -v wget" >/dev/null 2>&1; then
    log_error "wget not found on NAS — needed to download the Tailscale installer."
    exit 1
fi
log_info "  wget: found"

# 3. Install Tailscale if missing
log_info "Checking if Tailscale is already installed..."
if nas_exec "command -v tailscale" >/dev/null 2>&1; then
    EXISTING_VERSION=$(nas_exec "tailscale version" 2>&1 | head -1)
    log_info "Tailscale already installed: $EXISTING_VERSION"
else
    log_info "Tailscale not found, installing..."
    nas_exec "wget -qO- https://tailscale.com/install.sh | sh"

    # Verify the install worked
    if ! nas_exec "command -v tailscale" >/dev/null 2>&1; then
        log_error "Tailscale install failed — 'tailscale' not found after install."
        exit 1
    fi
    INSTALLED_VERSION=$(nas_exec "tailscale version" 2>&1 | head -1)
    log_info "Tailscale installed: $INSTALLED_VERSION"
fi

# 4. Ensure tailscaled is running
log_info "Checking tailscaled service..."
if ! nas_exec "systemctl is-active --quiet tailscaled" 2>/dev/null; then
    log_info "Starting tailscaled..."
    nas_exec "systemctl enable --now tailscaled"
    if ! nas_exec "systemctl is-active --quiet tailscaled" 2>/dev/null; then
        log_error "Failed to start tailscaled service."
        exit 1
    fi
fi
log_info "tailscaled is running"

# 5. Check if already authenticated with correct config
log_info "Checking Tailscale status..."
TS_STATUS=$(nas_exec "tailscale status --json 2>/dev/null || echo '{}'" 2>/dev/null)
BACKEND_STATE=$(echo "$TS_STATUS" | jq -r '.BackendState // "Unknown"')

if [[ "$BACKEND_STATE" == "Running" ]]; then
    CURRENT_HOSTNAME=$(echo "$TS_STATUS" | jq -r '.Self.HostName // "unknown"')
    CURRENT_TAGS=$(echo "$TS_STATUS" | jq -r '.Self.Tags // [] | join(", ")')
    log_info "Tailscale is running — hostname: $CURRENT_HOSTNAME, tags: ${CURRENT_TAGS:-none}"

    if [[ "$CURRENT_HOSTNAME" == "nas" && "$CURRENT_TAGS" == *"homelab-nas"* ]]; then
        log_info "Already configured correctly. Nothing to do."
        exit 0
    fi

    log_warn "Current config doesn't match desired (hostname=nas, tag=homelab-nas)"
    read -r -p "Re-authenticate with new key and tag? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Skipping. Current status:"
        nas_exec "tailscale status"
        exit 0
    fi
fi

# 6. Prompt for auth key
echo
log_warn "You need a Tailscale auth key authorized for tag:homelab-nas"
log_warn "Create one at: https://login.tailscale.com/admin/settings/keys"
echo
read -r -p "Tailscale auth key: " TS_AUTH_KEY

if [[ -z "$TS_AUTH_KEY" ]]; then
    log_error "No auth key provided"
    exit 1
fi

# 7. Authenticate
log_info "Authenticating Tailscale on NAS..."
# Tags come from the auth key — don't use --advertise-tags with tagged auth keys
nas_exec "tailscale up --auth-key=$TS_AUTH_KEY --hostname=nas --accept-routes=false --accept-dns=false --reset"

# 8. Verify authentication succeeded
log_info "Verifying Tailscale connection..."
TS_STATUS=$(nas_exec "tailscale status --json 2>/dev/null || echo '{}'" 2>/dev/null)
BACKEND_STATE=$(echo "$TS_STATUS" | jq -r '.BackendState // "Unknown"')

if [[ "$BACKEND_STATE" != "Running" ]]; then
    log_error "Tailscale authentication failed — state is '$BACKEND_STATE', expected 'Running'."
    log_error "Check the auth key and ACL policy."
    exit 1
fi

FINAL_HOSTNAME=$(echo "$TS_STATUS" | jq -r '.Self.HostName // "unknown"')
FINAL_IP=$(echo "$TS_STATUS" | jq -r '.Self.TailscaleIPs[0] // "unknown"')
log_info "Tailscale connected — hostname: $FINAL_HOSTNAME, IP: $FINAL_IP"

nas_exec "tailscale status"

echo
echo "========================================="
echo "  Tailscale Setup Complete!"
echo "========================================="
echo
echo "NAS is now on your tailnet as '$FINAL_HOSTNAME' ($FINAL_IP)"
echo
echo "Next steps:"
echo "  1. Revoke the auth key in Tailscale admin (single-use)"
echo "  2. Verify tag:homelab-nas at https://login.tailscale.com/admin/machines"
echo "  3. Enable Funnel: task status-pipeline:funnel:on"
echo
