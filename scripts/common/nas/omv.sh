#!/usr/bin/env bash

# OpenMediaVault Certificate Installation Functions
# Handles installation of SSL certificates on OpenMediaVault NAS via OMV RPC

# Source required scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../cert.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../ssh.sh"

# Get dirty modules from OMV dirty modules file
# Args:
#   $1: Path to dirtymodules.json file (default: /var/lib/openmediavault/dirtymodules.json)
# Returns:
#   JSON array of dirty modules or empty array
omv_get_dirty_modules() {
    local dirty_file="${1:-/var/lib/openmediavault/dirtymodules.json}"

    if [[ -f "$dirty_file" ]]; then
        jq -c '.' < "$dirty_file"
    else
        echo "[]"
    fi
}

# Apply OMV configuration changes for dirty modules
# Args:
#   $1: JSON array of modules to apply (e.g., '["certificates","nginx"]')
# Returns:
#   0 on success, 1 on failure
omv_apply_changes() {
    local modules_json="$1"

    if [[ "$modules_json" != "[]" ]]; then
        omv-rpc -u admin "Config" "applyChanges" "{\"modules\":${modules_json},\"force\":false}"
    else
        echo "No pending changes to apply."
    fi
}

# Copy certificate files to OMV NAS
# Args:
#   $1: NAS hostname
#   $2: Directory containing cert.pem and key.pem
# Returns:
#   0 on success, 1 on failure
omv_cert_copy_files() {
    local nas_host="$1"
    local cert_dir="$2"
    local nas_user_host="${NAS_USER:-root}@${nas_host}"

    if [[ -z "$nas_host" ]]; then
        echo "Error: NAS hostname not provided" >&2
        return 1
    fi

    if [[ -z "$cert_dir" ]]; then
        echo "Error: Certificate directory not provided" >&2
        return 1
    fi

    if ! cert_validate_files "$cert_dir"; then
        return 1
    fi

    if [[ -n "${TEST:-}" ]]; then
        echo "TEST MODE: Would copy files to ${nas_user_host}"
        return 0
    fi

    scp_copy_file "${cert_dir}/cert.pem" "${nas_user_host}:/tmp/nas_cert.pem" || {
        echo "Error: Failed to copy certificate to NAS" >&2
        return 1
    }

    scp_copy_file "${cert_dir}/key.pem" "${nas_user_host}:/tmp/nas_key.pem" || {
        echo "Error: Failed to copy private key to NAS" >&2
        return 1
    }

    return 0
}

# Install certificate on OpenMediaVault NAS
# Args:
#   $1: NAS hostname (e.g., nas.example.com)
#   $2: Directory containing cert.pem and key.pem
# Returns:
#   0 on success, 1 on failure
omv_cert_install() {
    local nas_host="$1"
    local cert_dir="$2"
    local nas_user_host="${NAS_USER:-root}@${nas_host}"

    if [[ -z "$nas_host" ]]; then
        echo "Error: NAS hostname not provided" >&2
        echo "Usage: omv_cert_install <nas_hostname> <cert_directory>" >&2
        return 1
    fi

    if [[ -z "$cert_dir" ]]; then
        echo "Error: Certificate directory not provided" >&2
        echo "Usage: omv_cert_install <nas_hostname> <cert_directory>" >&2
        return 1
    fi

    if ! cert_validate_files "$cert_dir"; then
        return 1
    fi

    echo "Installing certificate on OMV NAS: $nas_host"

    if [[ -n "${TEST:-}" ]]; then
        echo "TEST MODE: Would install certificate on ${nas_user_host}"
        return 0
    fi

    if ! omv_cert_copy_files "$nas_host" "$cert_dir"; then
        echo "Error: Failed to copy certificate files" >&2
        return 1
    fi

    if ! ssh_execute_script "${nas_user_host}" "${SCRIPT_DIR}/install-cert-remote.sh"; then
        echo "Error: Failed to install certificate on NAS" >&2
        return 1
    fi

    echo "Certificate installation completed"
    return 0
}

# Export functions
export -f omv_get_dirty_modules
export -f omv_apply_changes
export -f omv_cert_copy_files
export -f omv_cert_install
