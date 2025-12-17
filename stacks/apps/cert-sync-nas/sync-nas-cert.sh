#!/bin/bash
set -e

# Sync SSL Certificate from acme.sh to NAS
# This script copies certificates from acme.sh and installs them on OMV

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common/nas/omv.sh"

# Configuration
NAS_HOST="${NAS_HOST:-nas.diyhub.dev}"
CERT_DOMAIN="${CERT_DOMAIN:-nas.diyhub.dev}"
ACME_DIR="${ACME_DIR:-/acme.sh}"

# Temporary directory for certificate files
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_DIR}"' EXIT

echo "🔐 Starting NAS certificate sync at $(date)"
echo "   NAS Host: ${NAS_HOST}"
echo "   Certificate Domain: ${CERT_DOMAIN}"
echo "   Acme Directory: ${ACME_DIR}"

# Copy certificates from acme.sh directory
echo ""
echo "📄 Copying certificates from acme.sh..."

CERT_PATH="${ACME_DIR}/${CERT_DOMAIN}_ecc"

if [ ! -d "${CERT_PATH}" ]; then
    # Try without _ecc suffix as fallback
    CERT_PATH="${ACME_DIR}/${CERT_DOMAIN}"
    if [ ! -d "${CERT_PATH}" ]; then
        echo "❌ Certificate directory not found: ${CERT_PATH}"
        exit 1
    fi
fi

# Copy certificate and key with expected names
if [ ! -f "${CERT_PATH}/fullchain.cer" ]; then
    echo "❌ Certificate file not found: ${CERT_PATH}/fullchain.cer"
    exit 1
fi

if [ ! -f "${CERT_PATH}/${CERT_DOMAIN}.key" ]; then
    echo "❌ Key file not found: ${CERT_PATH}/${CERT_DOMAIN}.key"
    exit 1
fi

cp "${CERT_PATH}/fullchain.cer" "${TEMP_DIR}/cert.pem"
cp "${CERT_PATH}/${CERT_DOMAIN}.key" "${TEMP_DIR}/key.pem"

echo "✅ Certificates copied successfully"

# Install certificate on OMV NAS
echo ""
echo "📤 Installing certificate on OMV NAS..."
if ! omv_cert_install "${NAS_HOST}" "${TEMP_DIR}"; then
    echo "❌ Failed to install certificate on OMV NAS"
    exit 1
fi

echo ""
echo "🎉 Certificate sync completed successfully at $(date)"
