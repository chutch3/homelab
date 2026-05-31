#!/usr/bin/env bash
# Runs on the NAS via SSH. Expects cert at /tmp/nas_cert.pem and key at /tmp/nas_key.pem.
# Requires passwordless sudo for: /usr/sbin/omv-rpc, /usr/sbin/omv-salt, /usr/bin/systemctl restart nginx
# Add to /etc/sudoers.d/omv-cert-sync on the NAS:
#   cody ALL=(ALL) NOPASSWD: /usr/sbin/omv-rpc, /usr/sbin/omv-salt, /usr/bin/systemctl restart nginx

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
if ! sudo /usr/sbin/omv-rpc -u admin "CertificateMgmt" "set" "$JSON_PAYLOAD"; then
    echo "Failed to create new certificate, trying to update existing..." >&2

    # Get current certificate UUID
    CURRENT_UUID=$(sudo /usr/sbin/omv-rpc -u admin "WebGui" "getSettings" | jq -r '.sslcertificateref')

    if [[ -n "$CURRENT_UUID" && "$CURRENT_UUID" != "null" ]]; then
        JSON_PAYLOAD=$(jq -n \
            --arg uuid "$CURRENT_UUID" \
            --rawfile cert /tmp/nas_cert.pem \
            --rawfile key /tmp/nas_key.pem \
            --arg comment "Auto-synced from acme.sh - $(date)" \
            '{uuid: $uuid, certificate: $cert, privatekey: $key, comment: $comment}')

        sudo /usr/sbin/omv-rpc -u admin "CertificateMgmt" "set" "$JSON_PAYLOAD"
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
    sudo /usr/sbin/omv-rpc -u admin "Config" "applyChanges" "{\"modules\":${MODULES_JSON},\"force\":false}"
else
    echo "No pending changes to apply."
fi

# Write certificate files to disk and apply nginx configuration
sudo /usr/sbin/omv-salt deploy run certificates
sudo /usr/sbin/omv-salt deploy run nginx
sudo /usr/bin/systemctl restart nginx

# Restart MinIO Caddy proxy if running (it caches certs at startup)
if command -v podman &>/dev/null && podman container exists minio-proxy 2>/dev/null; then
    echo "Restarting MinIO proxy to pick up new certificate..."
    podman restart minio-proxy
fi

# Clean up temporary files
rm -f /tmp/nas_cert.pem /tmp/nas_key.pem

echo "Certificate installed successfully"
