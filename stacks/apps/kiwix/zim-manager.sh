#!/bin/bash
# Kiwix ZIM Manager - Runs on NAS for downloads and updates
# Designed for OpenMediaVault but works on any Linux system

set -euo pipefail

# Configuration (set by setup-nas-downloads.sh)
ZIM_DATA_DIR="${ZIM_DATA_DIR:-/srv/kiwix_data}"
ZIM_LOG_DIR="${ZIM_LOG_DIR:-/var/log/kiwix}"
EMAIL_TO="${EMAIL_TO:-root@localhost}"
DOWNLOAD_SOURCE="https://download.kiwix.org/zim"

# ==============================================================================
# Command Wrappers (mockable in tests)
# ==============================================================================
# These wrapper functions allow external commands to be mocked during unit tests
# In production, they simply delegate to the actual commands
# In tests, they can be overridden with mock implementations

cmd_wget() { wget "$@"; }
cmd_sha256sum() { sha256sum "$@"; }
cmd_mail() { mail "$@"; }
cmd_sed() { sed "$@"; }
cmd_mv() { mv "$@"; }
cmd_rm() { rm "$@"; }
cmd_date() { date "$@"; }

# Starter pack content - includes tech resources and emergency preparedness content
# NOTE: Update these URLs periodically to get the latest versions
# Check https://download.kiwix.org/zim/ for current versions
# Last updated: 2025-12-04
declare -A STARTER_PACK=(
    ["wikipedia_en_nopic"]="wikipedia/wikipedia_en_all_nopic_2025-08.zim"
    ["gutenberg_en"]="gutenberg/gutenberg_en_all_2025-11.zim"
    ["medicine"]="wikipedia/wikipedia_en_medicine_nopic_2025-10.zim"
    ["stackoverflow"]="stack_exchange/stackoverflow.com_en_all_2023-11.zim"
    ["freecodecamp"]="freecodecamp/freecodecamp_en_all_2025-11.zim"
    ["openstreetmap_wiki"]="other/openstreetmap-wiki_en_all_nopic_2025-07.zim"
    ["gardening"]="stack_exchange/gardening.stackexchange.com_en_all_2025-10.zim"
    ["diy"]="stack_exchange/diy.stackexchange.com_en_all_2025-08.zim"
    ["cooking"]="stack_exchange/cooking.stackexchange.com_en_all_2025-07.zim"
    ["sustainability"]="stack_exchange/sustainability.stackexchange.com_en_all_2025-10.zim"
    ["wikivoyage"]="wikivoyage/wikivoyage_en_all_nopic_2025-09.zim"
)

LOG_FILE="${LOG_FILE:-$ZIM_LOG_DIR/zim-manager-$(date +%Y-%m-%d_%H-%M-%S).log}"
mkdir -p "$ZIM_LOG_DIR" "$ZIM_DATA_DIR" 2>/dev/null || true

# ==============================================================================
# Helper Functions
# ==============================================================================

usage() {
    cat << EOF
Usage: $0 {init|check|download <url>}

Commands:
    init              Download starter pack (Wikipedia, WikiMed, Stack Overflow, etc.)
    check             Check for available updates and send report
    download <url>    Download a specific ZIM file from URL

Environment Variables:
    ZIM_DATA_DIR      Directory for ZIM files (default: /srv/kiwix_data)
    ZIM_LOG_DIR       Directory for logs (default: /var/log/kiwix)
    EMAIL_TO          Email address for notifications (default: root@localhost)

Examples:
    $0 init
    $0 check
    $0 download https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_maxi_2024-01.zim
EOF
}

log() {
    echo "[$(cmd_date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

send_email() {
    local subject="$1"
    local body="$2"

    if command -v mail &> /dev/null; then
        echo "$body" | cmd_mail -s "$subject" "$EMAIL_TO"
        log "Email sent to $EMAIL_TO"
    else
        log "Warning: 'mail' command not found, skipping email notification"
    fi
}

# ==============================================================================
# Download Functions
# ==============================================================================

download_with_verify() {
    local url="$1"
    local output="$2"
    local temp_file="${output}.tmp"

    log "Downloading: $url"
    if cmd_wget -c -O "$temp_file" "$url"; then
        # Download checksum
        if cmd_wget -q -O "${temp_file}.sha256" "${url}.sha256"; then
            log "Verifying checksum..."
            # Modify checksum file to reference .tmp filename
            cmd_sed -i "s/  .*$/  $(basename "$temp_file")/" "${temp_file}.sha256"
            if (cd "$(dirname "$temp_file")" && cmd_sha256sum -c "$(basename "$temp_file").sha256"); then
                cmd_mv "$temp_file" "$output"
                cmd_rm "${temp_file}.sha256"
                log "Download successful and verified: $(basename "$output")"
                return 0
            else
                log "ERROR: Checksum verification failed"
                cmd_rm -f "$temp_file" "${temp_file}.sha256"
                return 1
            fi
        else
            log "Warning: Could not download checksum, skipping verification"
            cmd_mv "$temp_file" "$output"
            return 0
        fi
    else
        log "ERROR: Download failed"
        cmd_rm -f "$temp_file"
        return 1
    fi
}

check_for_updates() {
    log "Checking for ZIM file updates..."

    local current_files
    current_files=$(ls -1 "$ZIM_DATA_DIR"/*.zim 2>/dev/null || true)
    local updates_available=0

    if [ -z "$current_files" ]; then
        log "No ZIM files found - initial setup needed"
        return 2  # Special code for initial setup
    fi

    log "Current ZIM files:"
    echo "$current_files" | tee -a "$LOG_FILE"

    # TODO: Implement actual update checking by comparing dates/versions
    # For now, just report current state

    local report
    report="Kiwix Update Check - $(date)

Current ZIM Files:
$current_files

Current Storage Usage:
$(du -sh "$ZIM_DATA_DIR")

To check for updates manually, visit: $DOWNLOAD_SOURCE

Next automated check: $(date -d '+30 days')
"

    log "Update check complete"
    send_email "Kiwix Update Check Complete" "$report"

    return $updates_available
}

download_starter_pack() {
    log "Starting initial download of starter pack..."
    local success_count=0
    local fail_count=0

    for name in "${!STARTER_PACK[@]}"; do
        local path="${STARTER_PACK[$name]}"
        # Get latest version by fetching directory listing
        # This is simplified - real implementation would parse HTML/JSON
        local url="$DOWNLOAD_SOURCE/$path"

        log "Downloading $name..."
        if download_with_verify "$url" "$ZIM_DATA_DIR/$(basename "$url")"; then
            success_count=$((success_count + 1))
        else
            fail_count=$((fail_count + 1))
        fi
    done

    local summary="Kiwix Initial Setup Complete

Successfully downloaded: $success_count files
Failed downloads: $fail_count files

Check logs at: $LOG_FILE
"

    send_email "Kiwix Initial Setup Complete" "$summary"
    log "Initial download complete: $success_count succeeded, $fail_count failed"
}

# ==============================================================================
# Main Execution
# ==============================================================================

# Skip main execution if being sourced for testing
# When BATS_TEST_MODE=1, the script only defines functions and can be sourced
# When BATS_TEST_MODE is unset, the script runs normally with argument parsing
if [ -z "${BATS_TEST_MODE:-}" ]; then
    case "${1:-check}" in
        init)
            log "=== Kiwix Initial Setup ==="
            download_starter_pack
            ;;
        check)
            log "=== Kiwix Update Check ==="
            check_for_updates
            ;;
        download)
            if [ -z "${2:-}" ]; then
                log "ERROR: download command requires a URL"
                usage
                exit 1
            fi
            download_with_verify "$2" "$ZIM_DATA_DIR/$(basename "$2")"
            ;;
        *)
            usage
            exit 1
            ;;
    esac

    log "=== Run complete ==="
fi
