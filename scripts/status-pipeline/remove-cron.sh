#!/usr/bin/env bash
# Remove the status pipeline cron job from OMV.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"
    set +a
fi
# shellcheck source=/dev/null
source "$PROJECT_ROOT/scripts/common/ssh.sh"

NAS_SERVER="${NAS_SERVER:?NAS_SERVER is required in .env}"
NAS_ROOT="root@${NAS_SERVER}"

# Find UUID of the status pipeline cron job
UUID=$(ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=accept-new "$NAS_ROOT" \
    'omv-rpc -u admin Cron getList '"'"'{"start":0,"limit":100,"sortfield":"uuid","sortdir":"ASC","type":["userdefined"]}'"'"' | jq -r '"'"'.data[] | select(.command | contains("sync-status.sh")) | .uuid'"'"'')

if [[ -z "$UUID" ]]; then
    echo "No status pipeline cron job found"
    exit 0
fi

echo "Removing cron job: $UUID"
ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=accept-new "$NAS_ROOT" \
    "omv-rpc -u admin Cron delete '{\"uuid\":\"$UUID\"}'"

SSH_TIMEOUT=30 ssh_execute --login "$NAS_ROOT" "omv-salt deploy run cron"
echo "Cron job removed"
