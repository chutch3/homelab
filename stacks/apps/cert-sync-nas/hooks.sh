#!/usr/bin/env bash
set -euo pipefail

hook_mode() {
    case "$1" in
        pre_deploy) echo "user" ;;
        *)          echo "user" ;;
    esac
}

pre_deploy() {
    # CERT_SYNC_SSH_KEY_FILE is the key used to SSH into the NAS to install certs.
    # Defaults to homelab_rsa but should ideally be a dedicated NAS-only key.
    # Use SUDO_USER to resolve the real user's home — hooks run as root via become.
    local real_user="${SUDO_USER:-$USER}"
    local real_home
    real_home=$(eval echo "~${real_user}")
    local ssh_key="${CERT_SYNC_SSH_KEY_FILE:-${real_home}/.ssh/homelab_rsa}"

    if [[ ! -f "$ssh_key" ]]; then
        echo "ERROR: SSH key not found at $ssh_key" >&2
        echo "  Set CERT_SYNC_SSH_KEY_FILE in .env to point to the NAS SSH key." >&2
        exit 1
    fi

    if docker secret inspect cert_sync_ssh_key >/dev/null 2>&1; then
        echo "Secret cert_sync_ssh_key already exists, skipping"
        return 0
    fi

    docker secret create cert_sync_ssh_key "$ssh_key"
    echo "Created secret cert_sync_ssh_key from $ssh_key"
}

post_deploy() { :; }

case "${1:-}" in
    hook_mode)   hook_mode "${2:-}" ;;
    pre_deploy)  pre_deploy ;;
    post_deploy) post_deploy ;;
    *) echo "Usage: $0 {pre_deploy|post_deploy}" >&2; exit 1 ;;
esac
