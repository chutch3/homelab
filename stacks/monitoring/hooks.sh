#!/usr/bin/env bash
set -euo pipefail

STACK_DIR="${BASH_SOURCE[0]%/*}"

hook_mode() {
    case "$1" in
        pre_deploy) echo "user" ;;
        *)          echo "user" ;;
    esac
}

pre_deploy() {
    if [[ "${STATUS_PIPELINE_MINIO_ENABLED:-false}" != "true" ]]; then
        echo "MinIO metrics disabled — creating placeholder secret so stack can deploy"
        if ! docker secret inspect status_pipeline_minio_token >/dev/null 2>&1; then
            printf 'disabled' | docker secret create status_pipeline_minio_token -
        fi
        return 0
    fi

    if [[ -z "${STATUS_PIPELINE_MINIO_HOST:-}" ]]; then
        echo "ERROR: STATUS_PIPELINE_MINIO_ENABLED=true but STATUS_PIPELINE_MINIO_HOST is not set in .env" >&2
        exit 1
    fi

    # Write the actual scrape target so Prometheus knows where to reach MinIO
    printf '[{"targets":["%s"],"labels":{"instance":"nas"}}]\n' \
        "$STATUS_PIPELINE_MINIO_HOST" > "$STACK_DIR/minio-targets.json"
    echo "Updated minio-targets.json → $STATUS_PIPELINE_MINIO_HOST"
    # The real secret is created by pre-flight.yml via create-secrets.yml
}

post_deploy() { :; }

case "${1:-}" in
    hook_mode)   hook_mode "${2:-}" ;;
    pre_deploy)  pre_deploy ;;
    post_deploy) post_deploy ;;
    *) echo "Usage: $0 {pre_deploy|post_deploy}" >&2; exit 1 ;;
esac
