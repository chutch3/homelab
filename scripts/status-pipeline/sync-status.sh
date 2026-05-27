#!/usr/bin/env bash
# Fetch Uptime Kuma status page data and upload to MinIO as a public JSON file.
# Runs on the NAS (OpenMediaVault) as an OMV scheduled task every 15 minutes.
#
# Reads configuration from /etc/status-pipeline.conf (deployed by setup-nas.sh).
set -euo pipefail

CONF_FILE="/etc/status-pipeline.conf"
if [[ -f "$CONF_FILE" ]]; then
    # shellcheck source=/dev/null
    . "$CONF_FILE"
fi

STATUS_PIPELINE_UPTIME_KUMA_URL="${STATUS_PIPELINE_UPTIME_KUMA_URL:?STATUS_PIPELINE_UPTIME_KUMA_URL is required}"
STATUS_PIPELINE_STATUS_SLUG="${STATUS_PIPELINE_STATUS_SLUG:?STATUS_PIPELINE_STATUS_SLUG is required}"
STATUS_PIPELINE_MINIO_ENDPOINT="${STATUS_PIPELINE_MINIO_ENDPOINT:?STATUS_PIPELINE_MINIO_ENDPOINT is required}"
STATUS_PIPELINE_MINIO_BUCKET="${STATUS_PIPELINE_MINIO_BUCKET:-public-status}"
STATUS_PIPELINE_MINIO_OBJECT="${STATUS_PIPELINE_MINIO_OBJECT:-status.json}"
STATUS_PIPELINE_MINIO_ACCESS_KEY="${STATUS_PIPELINE_MINIO_ACCESS_KEY:?STATUS_PIPELINE_MINIO_ACCESS_KEY is required}"
STATUS_PIPELINE_MINIO_SECRET_KEY="${STATUS_PIPELINE_MINIO_SECRET_KEY:?STATUS_PIPELINE_MINIO_SECRET_KEY is required}"

TMPFILE_STATUS="$(mktemp)"
TMPFILE_HEARTBEAT="$(mktemp)"
TMPFILE_MERGED="$(mktemp)"
trap 'rm -f "$TMPFILE_STATUS" "$TMPFILE_HEARTBEAT" "$TMPFILE_MERGED"' EXIT

BASE_URL="${STATUS_PIPELINE_UPTIME_KUMA_URL}/api/status-page"

# Fetch status page (publicGroupList, config)
if ! wget -qO "$TMPFILE_STATUS" --timeout=30 "${BASE_URL}/${STATUS_PIPELINE_STATUS_SLUG}"; then
    echo "ERROR: Failed to fetch status page" >&2
    exit 1
fi

# Fetch heartbeat data (heartbeatList, uptimeList)
if ! wget -qO "$TMPFILE_HEARTBEAT" --timeout=30 "${BASE_URL}/heartbeat/${STATUS_PIPELINE_STATUS_SLUG}"; then
    echo "ERROR: Failed to fetch heartbeat data" >&2
    exit 1
fi

# Merge both responses into a single JSON
jq -s '.[0] * .[1]' "$TMPFILE_STATUS" "$TMPFILE_HEARTBEAT" > "$TMPFILE_MERGED"

if ! jq empty "$TMPFILE_MERGED" 2>/dev/null; then
    echo "ERROR: Merged result is not valid JSON" >&2
    exit 1
fi

# Upload to MinIO via S3 API
RESOURCE="/${STATUS_PIPELINE_MINIO_BUCKET}/${STATUS_PIPELINE_MINIO_OBJECT}"
CONTENT_TYPE="application/json"
DATE=$(date -u +"%a, %d %b %Y %H:%M:%S GMT")
STRING_TO_SIGN="PUT\n\n${CONTENT_TYPE}\n${DATE}\n${RESOURCE}"
SIGNATURE=$(printf '%b' "$STRING_TO_SIGN" | openssl dgst -sha1 -hmac "$STATUS_PIPELINE_MINIO_SECRET_KEY" -binary | openssl enc -base64)

UPLOAD_RESPONSE=$(wget -qO- --timeout=30 \
    --method=PUT \
    --header="Date: ${DATE}" \
    --header="Content-Type: ${CONTENT_TYPE}" \
    --header="Authorization: AWS ${STATUS_PIPELINE_MINIO_ACCESS_KEY}:${SIGNATURE}" \
    --body-file="$TMPFILE_MERGED" \
    "${STATUS_PIPELINE_MINIO_ENDPOINT}${RESOURCE}" 2>&1) || {
    echo "ERROR: MinIO upload failed: ${UPLOAD_RESPONSE}" >&2
    exit 1
}

echo "OK: status.json uploaded to ${STATUS_PIPELINE_MINIO_ENDPOINT}${RESOURCE}"
