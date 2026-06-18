#!/usr/bin/env bash
set -euo pipefail

STACK=fiber-e2e
SECRET=e2e_db_password
NETWORK=backups
# Script must be invocable from any working directory; resolve paths relative to itself.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

cleanup() {
    echo "--- cleanup ---"
    docker stack rm "${STACK}" 2>/dev/null || true
    # Wait for stack services to drain before removing shared resources
    local attempts=0
    while docker stack ps "${STACK}" --no-trunc -q 2>/dev/null | grep -q .; do
        attempts=$(( attempts + 1 ))
        if [ "${attempts}" -ge 30 ]; then
            echo "WARNING: stack tasks still running after 30s" >&2
            break
        fi
        sleep 1
    done
    docker secret rm "${SECRET}" 2>/dev/null || true
    docker network rm "${NETWORK}" 2>/dev/null || true
    docker swarm leave --force 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# 1. Bootstrap single-node swarm (idempotent)
# ---------------------------------------------------------------------------
docker swarm init 2>/dev/null || true

# ---------------------------------------------------------------------------
# 2. Overlay network
# ---------------------------------------------------------------------------
docker network create -d overlay --attachable "${NETWORK}" 2>/dev/null || true

# ---------------------------------------------------------------------------
# 3. Secret
# ---------------------------------------------------------------------------
printf 'testpass' | docker secret create "${SECRET}" - 2>/dev/null || true

# ---------------------------------------------------------------------------
# 4. Build fiber image
# ---------------------------------------------------------------------------
docker build \
    -t fiber:e2e \
    -f "${REPO_ROOT}/stacks/apps/fiber/app/Dockerfile" \
    "${REPO_ROOT}/stacks/apps/fiber"

# ---------------------------------------------------------------------------
# 5. Deploy stack
# ---------------------------------------------------------------------------
docker stack deploy \
    -c "${SCRIPT_DIR}/stack.yml" \
    "${STACK}"

# ---------------------------------------------------------------------------
# 6. Poll for a .dump artifact in the fiber bowl (up to 150 s)
# ---------------------------------------------------------------------------
echo "--- waiting for dump artifact ---"
DUMP_PATH=""
attempts=0
while [ "${attempts}" -lt 150 ]; do
    # Get the container ID of the running fiber task
    FIBER_CONTAINER=$(docker ps --filter "name=${STACK}_fiber" --format "{{.ID}}" 2>/dev/null | head -1)
    if [ -n "${FIBER_CONTAINER}" ]; then
        DUMP_PATH=$(docker exec "${FIBER_CONTAINER}" sh -c 'ls /backups/*/*.dump 2>/dev/null | head -1' 2>/dev/null || true)
        if [ -n "${DUMP_PATH}" ]; then
            echo "dump found: ${DUMP_PATH}"
            break
        fi
    fi
    attempts=$(( attempts + 1 ))
    sleep 1
done

if [ -z "${DUMP_PATH}" ]; then
    echo "FAIL: no dump artifact appeared within 150 s" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 7. Copy dump out and restore into a scratch DB; assert row count = 1000
# ---------------------------------------------------------------------------
echo "--- restoring dump and asserting row count ---"

# Copy the dump file out of the fiber container to the host
TMP_DUMP="$(mktemp --suffix=.dump)"
docker cp "${FIBER_CONTAINER}:${DUMP_PATH}" "${TMP_DUMP}"

# Spin up a throwaway postgres:16 container to restore into
SCRATCH_NAME="fiber-e2e-scratch-$$"
docker run -d \
    --name "${SCRATCH_NAME}" \
    -e POSTGRES_USER=verify \
    -e POSTGRES_PASSWORD=verify \
    -e POSTGRES_DB=verify \
    postgres:16

# Give postgres a moment to start
sleep 5

# Copy dump into scratch container then restore
docker cp "${TMP_DUMP}" "${SCRATCH_NAME}:/tmp/verify.dump"
rm -f "${TMP_DUMP}"

docker exec "${SCRATCH_NAME}" \
    pg_restore \
    -U verify \
    -d verify \
    --no-privileges \
    --no-owner \
    /tmp/verify.dump

# Assert row count
ROW_COUNT=$(docker exec "${SCRATCH_NAME}" \
    psql -U verify -d verify -tAc "SELECT COUNT(*) FROM e2e_data;")

docker rm -f "${SCRATCH_NAME}" 2>/dev/null || true

ROW_COUNT=$(echo "${ROW_COUNT}" | tr -d '[:space:]')
if [ "${ROW_COUNT}" != "1000" ]; then
    echo "FAIL: expected 1000 rows, got '${ROW_COUNT}'" >&2
    exit 1
fi

echo "PASS: dump restored successfully, row count = ${ROW_COUNT}"
