#!/usr/bin/env bash
# Unprivileged Fiber e2e: plain docker compose (bridge net), real dump -> restore -> assert.
set -euo pipefail
cd "$(dirname "$0")"

PROJECT="fiber-e2e"
NET="${PROJECT}_fibernet"

cleanup() {
  docker compose -p "$PROJECT" down -v --remove-orphans >/dev/null 2>&1 || true
  docker rm -f fiber-e2e-restore >/dev/null 2>&1 || true
  rm -f e2e_db_password /tmp/e2e.dump
}
trap cleanup EXIT

echo "e2e_password" > e2e_db_password

echo "==> Building fiber:e2e image"
docker build -t fiber:e2e -f ../../app/Dockerfile ../../

echo "==> Bringing up the compose stack"
docker compose -p "$PROJECT" up -d

echo "==> Waiting for Fiber to produce a dump (<=120s)"
deadline=$((SECONDS + 120))
dump=""
while [ $SECONDS -lt $deadline ]; do
  dump=$(docker compose -p "$PROJECT" exec -T fiber sh -c 'ls /backups/e2e/*.dump 2>/dev/null | head -1' || true)
  [ -n "$dump" ] && break
  sleep 3
done
if [ -z "$dump" ]; then
  echo "FAIL: no dump produced"; docker compose -p "$PROJECT" logs fiber; exit 1
fi
echo "    dump: $dump"

echo "==> Restoring into a scratch postgres and asserting row count"
docker run -d --rm --name fiber-e2e-restore --network "$NET" -e POSTGRES_PASSWORD=restore postgres:16 >/dev/null
until docker exec fiber-e2e-restore pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
docker exec fiber-e2e-restore psql -U postgres -c 'CREATE DATABASE e2e;' >/dev/null
docker compose -p "$PROJECT" exec -T fiber sh -c "cat $dump" > /tmp/e2e.dump
docker cp /tmp/e2e.dump fiber-e2e-restore:/tmp/e2e.dump
docker exec fiber-e2e-restore pg_restore -U postgres -d e2e /tmp/e2e.dump
count=$(docker exec fiber-e2e-restore psql -U postgres -d e2e -tAc 'SELECT count(*) FROM e2e_data;' | tr -d '[:space:]')

echo "    rows restored: $count"
[ "$count" = "1000" ] || { echo "FAIL: expected 1000 rows, got $count"; exit 1; }
echo "PASS: e2e dump -> restore verified 1000 rows (unprivileged, no swarm)"
