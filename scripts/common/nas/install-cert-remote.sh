#!/usr/bin/env bash
# Runs on the NAS via SSH. Expects cert at /tmp/nas_cert.pem and key at /tmp/nas_key.pem.

set -euo pipefail

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
    echo "Failed to create new certificate, trying to update existing..." >&2

    # Get current certificate UUID
    CURRENT_UUID=$(omv-rpc -u admin "WebGui" "getSettings" | jq -r '.sslcertificateref')

    if [[ -n "$CURRENT_UUID" && "$CURRENT_UUID" != "null" ]]; then
        JSON_PAYLOAD=$(jq -n \
            --arg uuid "$CURRENT_UUID" \
            --rawfile cert /tmp/nas_cert.pem \
            --rawfile key /tmp/nas_key.pem \
            --arg comment "Auto-synced from acme.sh - $(date)" \
            '{uuid: $uuid, certificate: $cert, privatekey: $key, comment: $comment}')

        omv-rpc -u admin "CertificateMgmt" "set" "$JSON_PAYLOAD"
    else
        exit 1
    fi
fi

# Apply pending configuration changes for all dirty modules
echo "Applying OMV configuration changes..."
MODULES_JSON=$(if [[ -f /var/lib/openmediavault/dirtymodules.json ]]; then
    jq -c '.' < /var/lib/openmediavault/dirtymodules.json
else
    echo "[]"
fi)

if [[ "$MODULES_JSON" != "[]" ]]; then
    omv-rpc -u admin "Config" "applyChanges" "{\"modules\":${MODULES_JSON},\"force\":false}"
else
    echo "No pending changes to apply."
fi

# Write certificate files to disk and apply nginx configuration
omv-salt deploy run certificates
omv-salt deploy run nginx
systemctl restart nginx

# Clean up temporary files
rm -f /tmp/nas_cert.pem /tmp/nas_key.pem

echo "Certificate installed successfully"
