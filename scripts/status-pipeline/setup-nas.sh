#!/usr/bin/env bash
# Status Pipeline NAS Setup
# Deploys sync-status.sh to the NAS and registers an OMV cron job.
#
# Usage:
#   ./setup-nas.sh          # Initial setup
#   ./setup-nas.sh setup    # Initial setup (explicit)
#   ./setup-nas.sh update   # Update sync script on NAS

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/sync-status.sh"
BUCKET_POLICY="$SCRIPT_DIR/bucket-policy.json"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

prompt() {
    local var_name="$1"
    local prompt_text="$2"
    local default="${3:-}"

    if [ -n "$default" ]; then
        read -r -p "$prompt_text [$default]: " value
        eval "$var_name=\"${value:-$default}\""
    else
        read -r -p "$prompt_text: " value
        eval "$var_name=\"$value\""
    fi
}

usage() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    setup     Initial setup: deploy script, create bucket, register cron (default)
    update    Update sync-status.sh on NAS

Examples:
    $0              # Run initial setup
    $0 setup        # Run initial setup (explicit)
    $0 update       # Update sync-status.sh on NAS
EOF
    exit 1
}

load_environment() {
    if [ -f "$PROJECT_ROOT/.env" ]; then
        set -a
        # shellcheck source=/dev/null
        source "$PROJECT_ROOT/.env"
        set +a
        log_info "Loaded environment from .env"
    fi

    if [ -f "$PROJECT_ROOT/scripts/common/ssh.sh" ]; then
        # shellcheck source=/dev/null
        source "$PROJECT_ROOT/scripts/common/ssh.sh"
        log_info "Loaded ssh library"
    else
        log_error "Could not find scripts/common/ssh.sh"
        exit 1
    fi
}

get_nas_connection_info() {
    log_info "Gathering NAS connection information..."

    if [ -z "${NAS_SERVER:-}" ]; then
        prompt NAS_SERVER "NAS hostname or IP" "nas.local"
    else
        log_info "Using NAS_SERVER from .env: $NAS_SERVER"
    fi

    if [ -z "${NAS_USER:-}" ]; then
        prompt NAS_USER "SSH username for NAS" "admin"
    else
        log_info "Using NAS_USER from .env: $NAS_USER"
    fi

    NAS_USER_HOST="root@$NAS_SERVER"
    export NAS_USER_HOST NAS_SERVER NAS_USER
}

ensure_ssh_connectivity() {
    log_info "Testing SSH connection to $NAS_USER_HOST..."

    if ssh_test_connection "$NAS_USER_HOST"; then
        log_info "SSH connection successful"
        return 0
    fi

    log_warn "Cannot connect with SSH key. Attempting to copy SSH key..."
    if ssh_copy_key "$NAS_USER_HOST"; then
        if ssh_test_connection "$NAS_USER_HOST"; then
            log_info "SSH connection successful"
            return 0
        fi
    fi

    log_error "SSH connection failed. Check that SSH is enabled on OMV."
    exit 1
}

get_pipeline_config() {
    log_info "Configuring status pipeline..."

    if [ -z "${STATUS_PIPELINE_STATUS_SLUG:-}" ]; then
        prompt STATUS_PIPELINE_STATUS_SLUG "Uptime Kuma status page slug" "services"
    else
        log_info "Using STATUS_PIPELINE_STATUS_SLUG from .env: $STATUS_PIPELINE_STATUS_SLUG"
    fi

    STATUS_PIPELINE_MINIO_ACCESS_KEY="${STATUS_PIPELINE_MINIO_ACCESS_KEY:?STATUS_PIPELINE_MINIO_ACCESS_KEY is required in .env}"
    STATUS_PIPELINE_MINIO_SECRET_KEY="${STATUS_PIPELINE_MINIO_SECRET_KEY:?STATUS_PIPELINE_MINIO_SECRET_KEY is required in .env}"
    STATUS_PIPELINE_MINIO_HOST="${STATUS_PIPELINE_MINIO_HOST:?STATUS_PIPELINE_MINIO_HOST is required in .env}"
    log_info "Using MinIO credentials from .env"

    export STATUS_PIPELINE_STATUS_SLUG STATUS_PIPELINE_MINIO_ACCESS_KEY STATUS_PIPELINE_MINIO_SECRET_KEY STATUS_PIPELINE_MINIO_HOST
}

check_nas_dependencies() {
    log_info "Checking NAS dependencies..."

    for cmd in wget jq openssl; do
        if ssh_command_exists "$NAS_USER_HOST" "$cmd"; then
            log_info "  $cmd: found"
        else
            log_error "  $cmd: NOT FOUND — install it on the NAS before continuing"
            exit 1
        fi
    done
}

create_minio_bucket() {
    log_info "Creating MinIO bucket and applying policy..."

    local minio="https://${STATUS_PIPELINE_MINIO_HOST}"
    local date sig

    # Create bucket via S3 PUT (ignore failure if already exists)
    date=$(date -u +"%a, %d %b %Y %H:%M:%S GMT")
    sig=$(printf "PUT\n\n\n%s\n/public-status/" "$date" | openssl dgst -sha1 -hmac "$STATUS_PIPELINE_MINIO_SECRET_KEY" -binary | openssl enc -base64)
    ssh_execute --login "$NAS_USER_HOST" \
        "wget -qO /dev/null --timeout=10 --method=PUT \
        --header='Date: ${date}' \
        --header='Authorization: AWS ${STATUS_PIPELINE_MINIO_ACCESS_KEY}:${sig}' \
        '${minio}/public-status/'" 2>/dev/null || true
    log_info "Bucket create: done"

    # Apply anonymous read policy via S3 PUT bucket policy
    scp_copy_file "$BUCKET_POLICY" "$NAS_USER_HOST:/tmp/bucket-policy.json"
    date=$(date -u +"%a, %d %b %Y %H:%M:%S GMT")
    sig=$(printf "PUT\n\napplication/json\n%s\n/public-status/?policy" "$date" | openssl dgst -sha1 -hmac "$STATUS_PIPELINE_MINIO_SECRET_KEY" -binary | openssl enc -base64)
    ssh_execute --login "$NAS_USER_HOST" \
        "wget -qO /dev/null --timeout=10 --method=PUT \
        --header='Date: ${date}' \
        --header='Content-Type: application/json' \
        --header='Authorization: AWS ${STATUS_PIPELINE_MINIO_ACCESS_KEY}:${sig}' \
        --body-file=/tmp/bucket-policy.json \
        '${minio}/public-status/?policy'"
    ssh_execute "$NAS_USER_HOST" "rm -f /tmp/bucket-policy.json"
    log_info "Bucket policy applied"
}

install_sync_script() {
    log_info "Installing sync-status.sh on NAS..."

    scp_copy_file "$SYNC_SCRIPT" "$NAS_USER_HOST:/usr/local/bin/sync-status.sh"
    ssh_execute "$NAS_USER_HOST" "chmod +x /usr/local/bin/sync-status.sh"
    log_info "sync-status.sh installed"

    log_info "Creating configuration file on NAS..."
    ssh_execute "$NAS_USER_HOST" "cat > /etc/status-pipeline.conf <<EOF
STATUS_PIPELINE_UPTIME_KUMA_URL=https://uptime.${BASE_DOMAIN}
STATUS_PIPELINE_STATUS_SLUG=${STATUS_PIPELINE_STATUS_SLUG}
STATUS_PIPELINE_MINIO_ENDPOINT=https://${STATUS_PIPELINE_MINIO_HOST}
STATUS_PIPELINE_MINIO_BUCKET=public-status
STATUS_PIPELINE_MINIO_OBJECT=status.json
STATUS_PIPELINE_MINIO_ACCESS_KEY=${STATUS_PIPELINE_MINIO_ACCESS_KEY}
STATUS_PIPELINE_MINIO_SECRET_KEY=${STATUS_PIPELINE_MINIO_SECRET_KEY}
EOF"
    ssh_execute "$NAS_USER_HOST" "chmod 600 /etc/status-pipeline.conf"
    log_info "Configuration written to /etc/status-pipeline.conf"
}

setup_omv_cron() {
    log_info "Registering scheduled task in OpenMediaVault..."

    # Remove existing status pipeline cron job if present
    local existing_uuid
    existing_uuid=$(ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=accept-new "$NAS_USER_HOST" \
        'omv-rpc -u admin Cron getList '"'"'{"start":0,"limit":100,"sortfield":"uuid","sortdir":"ASC","type":["userdefined"]}'"'"' | jq -r '"'"'.data[] | select(.command | contains("sync-status.sh")) | .uuid'"'"'' 2>/dev/null) || true
    if [[ -n "$existing_uuid" ]]; then
        log_info "Removing existing cron job: $existing_uuid"
        ssh_execute "$NAS_USER_HOST" "omv-rpc -u admin Cron delete '{\"uuid\":\"$existing_uuid\"}'"
    fi

    local omv_new_uuid
    omv_new_uuid=$(ssh_execute "$NAS_USER_HOST" \
        ". /etc/default/openmediavault && echo \$OMV_CONFIGOBJECT_NEW_UUID")

    ssh_execute "$NAS_USER_HOST" "omv-rpc -u admin Cron set '{
      \"uuid\": \"$omv_new_uuid\",
      \"enable\": true,
      \"type\": \"userdefined\",
      \"execution\": \"exactly\",
      \"minute\": [\"0\",\"15\",\"30\",\"45\"],
      \"everynminute\": false,
      \"hour\": [\"*\"],
      \"everynhour\": false,
      \"dayofmonth\": [\"*\"],
      \"everyndayofmonth\": false,
      \"month\": [\"*\"],
      \"dayofweek\": [\"*\"],
      \"username\": \"root\",
      \"command\": \"/usr/local/bin/sync-status.sh >> /var/log/status-pipeline.log 2>&1\",
      \"comment\": \"Status pipeline - sync Uptime Kuma to MinIO\",
      \"sendemail\": false
    }'"

    ssh_execute "$NAS_USER_HOST" "omv-salt deploy run cron"

    log_info "Scheduled task configured in OMV (every 15 minutes)"
    log_info "View in OMV: System → Scheduled Jobs"
}

verify_pipeline() {
    log_info "Running a test sync..."

    local result
    result=$(ssh_execute --login "$NAS_USER_HOST" "/usr/local/bin/sync-status.sh" 2>&1) || {
        log_error "Test sync failed: $result"
        exit 1
    }
    log_info "$result"

    log_info "Verifying anonymous read..."
    local http_code
    http_code=$(ssh_execute --login "$NAS_USER_HOST" \
        "wget -qS --timeout=10 -O /dev/null https://${STATUS_PIPELINE_MINIO_HOST}/public-status/status.json 2>&1 | grep 'HTTP/' | tail -1 | awk '{print \$2}'"
    ) || true

    if [[ "$http_code" == "200" ]]; then
        log_info "Anonymous read: OK (HTTP 200)"
    else
        log_warn "Anonymous read returned HTTP ${http_code:-unknown} — check bucket policy"
    fi
}

cmd_setup() {
    echo "========================================="
    echo "  Status Pipeline NAS Setup"
    echo "========================================="
    echo

    load_environment
    get_nas_connection_info
    ensure_ssh_connectivity
    check_nas_dependencies
    get_pipeline_config
    create_minio_bucket
    install_sync_script
    setup_omv_cron
    verify_pipeline

    echo
    echo "========================================="
    echo "  Setup Complete!"
    echo "========================================="
    echo
    echo "Next steps:"
    echo "  1. Verify in OMV UI: System → Scheduled Jobs"
    echo "  2. Install Tailscale on NAS and tag as tag:homelab-nas"
    echo "  3. Upload updated ACL policy to Tailscale admin"
    echo "  4. Enable Funnel: tailscale funnel 9000 (on NAS)"
    echo "  5. Update portfolio site statusUrl with Funnel URL"
    echo
    echo "Logs: ssh $NAS_USER@$NAS_SERVER 'tail -f /var/log/status-pipeline.log'"
    echo
}

cmd_update() {
    echo "========================================="
    echo "  Update sync-status.sh on NAS"
    echo "========================================="
    echo

    load_environment
    get_nas_connection_info
    ensure_ssh_connectivity

    log_info "Backing up existing script..."
    ssh_execute "$NAS_USER_HOST" \
        "cp /usr/local/bin/sync-status.sh /usr/local/bin/sync-status.sh.bak" 2>/dev/null || true

    scp_copy_file "$SYNC_SCRIPT" "$NAS_USER_HOST:/usr/local/bin/sync-status.sh"
    ssh_execute "$NAS_USER_HOST" "chmod +x /usr/local/bin/sync-status.sh"

    log_info "sync-status.sh updated on NAS"
}

main() {
    local command="${1:-setup}"

    case "$command" in
        setup)   cmd_setup ;;
        update)  cmd_update ;;
        -h|--help|help) usage ;;
        *)
            log_error "Unknown command: $command"
            usage
            ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
