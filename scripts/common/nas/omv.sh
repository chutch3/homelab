#!/bin/bash

# OpenMediaVault Certificate Installation Functions
# Handles installation of SSL certificates on OpenMediaVault NAS via OMV RPC

# Source required scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../cert.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../ssh.sh"

# Generate OMV RPC command for certificate installation
# Args:
#   $1: Path to certificate file
#   $2: Path to private key file
# Returns:
#   OMV RPC command string
omv_cert_generate_rpc_command() {
    local cert_file="$1"
    local key_file="$2"

    if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
        echo "Error: Certificate or key file not found" >&2
        return 1
    fi

    # Read certificate and key content
    local cert_content
    local key_content
    cert_content=$(cat "$cert_file")
    key_content=$(cat "$key_file")

    # Generate UUID for certificate
    local uuid
    uuid=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "test-uuid-123")

    # Use jq to properly escape JSON - create JSON object and output the command
    local json_payload
    json_payload=$(jq -n \
        --arg uuid "$uuid" \
        --arg cert "$cert_content" \
        --arg key "$key_content" \
        --arg comment "Auto-synced from acme.sh - $(date)" \
        '{uuid: $uuid, certificate: $cert, privatekey: $key, comment: $comment}')

    # Generate OMV RPC command with properly escaped JSON
    echo "omv-rpc -u admin \"CertificateMgmt\" \"set\" '$json_payload'"
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

    # Validate inputs
    if [ -z "$nas_host" ]; then
        echo "Error: NAS hostname not provided" >&2
        return 1
    fi

    if [ -z "$cert_dir" ]; then
        echo "Error: Certificate directory not provided" >&2
        return 1
    fi

    # Validate certificate files exist
    if ! cert_validate_files "$cert_dir"; then
        return 1
    fi

    # In test mode, skip actual SSH operations
    if [ -n "${TEST:-}" ]; then
        echo "TEST MODE: Would copy files to $nas_host"
        return 0
    fi

    # Copy files via SCP
    scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        "${cert_dir}/cert.pem" "root@${nas_host}:/tmp/nas_cert.pem" || {
        echo "Error: Failed to copy certificate to NAS" >&2
        return 1
    }

    scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        "${cert_dir}/key.pem" "root@${nas_host}:/tmp/nas_key.pem" || {
        echo "Error: Failed to copy private key to NAS" >&2
        return 1
    }

    return 0
}

# Install certificate on OpenMediaVault NAS
# Args:
#   $1: NAS hostname (e.g., nas.diyhub.dev)
#   $2: Directory containing cert.pem and key.pem
# Returns:
#   0 on success, 1 on failure
omv_cert_install() {
    local nas_host="$1"
    local cert_dir="$2"

    # Validate inputs
    if [ -z "$nas_host" ]; then
        echo "Error: NAS hostname not provided" >&2
        echo "Usage: omv_cert_install <nas_hostname> <cert_directory>" >&2
        return 1
    fi

    if [ -z "$cert_dir" ]; then
        echo "Error: Certificate directory not provided" >&2
        echo "Usage: omv_cert_install <nas_hostname> <cert_directory>" >&2
        return 1
    fi

    # Validate certificate files
    if ! cert_validate_files "$cert_dir"; then
        return 1
    fi

    echo "Installing certificate on OMV NAS: $nas_host"

    # In test mode, skip actual installation
    if [ -n "${TEST:-}" ]; then
        echo "TEST MODE: Would install certificate on $nas_host"
        return 0
    fi

    # Copy certificate files to NAS
    if ! omv_cert_copy_files "$nas_host" "$cert_dir"; then
        echo "Error: Failed to copy certificate files" >&2
        return 1
    fi

    # Install certificate via SSH
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        "root@${nas_host}" << 'ENDSSH' || {
        # Generate UUID for the certificate
        CERT_UUID=$(cat /proc/sys/kernel/random/uuid)

        # Read certificate and key, create JSON payload with jq
        JSON_PAYLOAD=$(jq -n \
            --arg uuid "$CERT_UUID" \
            --rawfile cert /tmp/nas_cert.pem \
            --rawfile key /tmp/nas_key.pem \
            --arg comment "Auto-synced from acme.sh - $(date)" \
            '{uuid: $uuid, certificate: $cert, privatekey: $key, comment: $comment}')

        # Try to import certificate
        if ! omv-rpc -u admin "CertificateMgmt" "set" "$JSON_PAYLOAD"; then
            echo "Failed to create new certificate, trying to update existing..."

            # Get current certificate UUID
            CURRENT_UUID=$(omv-rpc -u admin "WebGui" "getSettings" | jq -r '.sslcertificateref')

            if [ -n "$CURRENT_UUID" ] && [ "$CURRENT_UUID" != "null" ]; then
                JSON_PAYLOAD=$(jq -n \
                    --arg uuid "$CURRENT_UUID" \
                    --rawfile cert /tmp/nas_cert.pem \
                    --rawfile key /tmp/nas_key.pem \
                    --arg comment "Auto-synced from acme.sh - $(date)" \
                    '{uuid: $uuid, certificate: $cert, privatekey: $key, comment: $comment}')

                omv-rpc -u admin "CertificateMgmt" "set" "$JSON_PAYLOAD" || exit 1
            else
                exit 1
            fi
        fi

        # TODO: Refactor to extract SSH heredoc logic for better testability
        # See https://github.com/chutch3/selfhosted.sh/issues/72
        # Apply pending configuration changes in OMV UI
        echo "Applying OMV configuration changes..."
        omv-rpc -u admin "Config" "applyChanges" '{"modules":["certificates"],"force":false}'

        # Write certificate files to disk
        omv-salt deploy run certificates

        # Apply nginx configuration
        omv-salt deploy run nginx

        # Restart nginx to pick up new certificate
        systemctl restart nginx

        # Clean up temporary files
        rm -f /tmp/nas_cert.pem /tmp/nas_key.pem

        echo "Certificate installed successfully"
ENDSSH
        echo "Error: Failed to install certificate on NAS" >&2
        return 1
    }

    echo "Certificate installation completed"
    return 0
}

# Export functions
export -f omv_cert_generate_rpc_command
export -f omv_cert_copy_files
export -f omv_cert_install
