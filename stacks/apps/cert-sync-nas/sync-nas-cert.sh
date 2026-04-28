#!/usr/bin/env bash
set -euo pipefail

# Sync SSL Certificate from acme.sh to NAS
# This script copies certificates from acme.sh and installs them on OMV

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_DIR="${COMMON_DIR:-${SCRIPT_DIR}/common}"

# shellcheck disable=SC1091
source "${COMMON_DIR}/nas/omv.sh"

# Configuration
NAS_HOST="${NAS_HOST:-nas.example.com}"
NAS_USER="${NAS_USER:-root}"
CERT_DOMAIN="${CERT_DOMAIN:-nas.example.com}"
ACME_DIR="${ACME_DIR:-/acme.sh}"

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_DIR}"' EXIT

echo "🔐 Starting NAS certificate sync at $(date)"
echo "   NAS Host: ${NAS_HOST}"
echo "   Certificate Domain: ${CERT_DOMAIN}"
echo "   Acme Directory: ${ACME_DIR}"

echo ""
echo "📄 Copying certificates from acme.sh..."

CERT_PATH="${ACME_DIR}/${CERT_DOMAIN}_ecc"

if [[ ! -d "${CERT_PATH}" ]]; then
    CERT_PATH="${ACME_DIR}/${CERT_DOMAIN}"
    if [[ ! -d "${CERT_PATH}" ]]; then
        echo "❌ Certificate directory not found: ${CERT_PATH}" >&2
        exit 1
    fi
    echo "   Using non-ECC cert path: ${CERT_PATH}"
else
    echo "   Using ECC cert path: ${CERT_PATH}"
fi

if [[ ! -f "${CERT_PATH}/fullchain.cer" ]]; then
    echo "❌ Certificate file not found: ${CERT_PATH}/fullchain.cer" >&2
    exit 1
fi

if [[ ! -f "${CERT_PATH}/${CERT_DOMAIN}.key" ]]; then
    echo "❌ Key file not found: ${CERT_PATH}/${CERT_DOMAIN}.key" >&2
    exit 1
fi

cp "${CERT_PATH}/fullchain.cer" "${TEMP_DIR}/cert.pem"
cp "${CERT_PATH}/${CERT_DOMAIN}.key" "${TEMP_DIR}/key.pem"

echo "✅ Certificates copied successfully"

echo ""
echo "📤 Installing certificate on OMV NAS..."
if ! omv_cert_install "${NAS_HOST}" "${TEMP_DIR}"; then
    echo "❌ Failed to install certificate on OMV NAS" >&2
    exit 1
fi

echo ""
echo "🎉 Certificate sync completed successfully at $(date)"
