#!/usr/bin/env bash
set -euo pipefail

hook_mode() {
    case "$1" in
        pre_deploy) echo "root" ;;
        *)          echo "user" ;;
    esac
}

pre_deploy() {
    mkdir -p /mnt/iscsi/app-data/tor-browser
    chown -R 1000:1000 /mnt/iscsi/app-data/tor-browser
}

post_deploy() { :; }

case "${1:-}" in
    hook_mode)   hook_mode "${2:-}" ;;
    pre_deploy)  pre_deploy ;;
    post_deploy) post_deploy ;;
    *) echo "Usage: $0 {pre_deploy|post_deploy}" >&2; exit 1 ;;
esac
