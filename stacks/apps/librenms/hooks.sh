#!/usr/bin/env bash
set -euo pipefail

hook_mode() {
    case "$1" in
        pre_deploy) echo "root" ;;
        *)          echo "user" ;;
    esac
}

pre_deploy() {
    local app_data="/mnt/iscsi/app-data/librenms"
    local cache="/mnt/iscsi/cache"
    local puid="${PUID:-1000}"
    local pgid="${PGID:-1000}"

    mkdir -p "${app_data}/db" "${app_data}/data" "${cache}/librenms-redis"
    chown -R 999:999 "${app_data}/db"
    chown -R 999:999 "${cache}/librenms-redis"
    chown -R "${puid}:${pgid}" "${app_data}/data"
}

post_deploy() { :; }

case "${1:-}" in
    hook_mode)   hook_mode "${2:-}" ;;
    pre_deploy)  pre_deploy ;;
    post_deploy) post_deploy ;;
    *) echo "Usage: $0 {pre_deploy|post_deploy}" >&2; exit 1 ;;
esac
