#!/usr/bin/env bash
set -euo pipefail

hook_mode() {
    case "$1" in
        pre_deploy) echo "root" ;;
        *)          echo "user" ;;
    esac
}

pre_deploy() {
    local sentinel="/tmp/preflight-hook-test.txt"
    echo "pre_deploy hook executed as $(whoami)" >> "$sentinel"

    # Verify root operations work
    touch /tmp/preflight-root-test
    chown root:root /tmp/preflight-root-test
    echo "root operation succeeded" >> "$sentinel"

    # Verify Docker context vars are present
    echo "DOCKER_CONTEXT=${DOCKER_CONTEXT:-unset}" >> "$sentinel"
    echo "DOCKER_CONFIG=${DOCKER_CONFIG:-unset}" >> "$sentinel"
}

post_deploy() { :; }

case "${1:-}" in
    hook_mode)   hook_mode "${2:-}" ;;
    pre_deploy)  pre_deploy ;;
    post_deploy) post_deploy ;;
    *) echo "Usage: $0 {hook_mode <event>|pre_deploy|post_deploy}" >&2; exit 1 ;;
esac
