#!/usr/bin/env bats

# The dns healthcheck command itself, against the real Technitium image: only
# this proves the probe tells a live resolver from a dead one.

load "${BATS_TEST_DIRNAME}/../../../tests/helpers/bats-support/load"
load "${BATS_TEST_DIRNAME}/../../../tests/helpers/bats-assert/load"

COMPOSE="${BATS_TEST_DIRNAME}/../docker-compose.yml"
CONTAINER="homelab-dns-healthcheck-test"

# This is a throwaway local container. Without pinning, it would run on
# whatever context is active — normally `homelab`, i.e. the swarm manager.
export DOCKER_CONTEXT="${DOCKER_CONTEXT_OVERRIDE:-default}"

setup_file() {
    if [[ "${HOMELAB_DNS_IMAGE_E2E:-}" != "1" ]]; then
        skip "set HOMELAB_DNS_IMAGE_E2E=1 to run against the real dns image"
    fi
    local image
    image="$(grep -oP '(?<=image: )technitium/dns-server:\S+' "$COMPOSE")"
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    docker run -d --name "$CONTAINER" "$image" >/dev/null
    # The probe is the readiness signal, so use it to wait for the server.
    local i
    for i in $(seq 1 60); do
        docker exec "$CONTAINER" sh -c "$(probe)" >/dev/null 2>&1 && return 0
        sleep 1
    done
    echo "dns server never came up" >&2
    return 1
}

teardown_file() {
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}

setup() {
    if [[ "${HOMELAB_DNS_IMAGE_E2E:-}" != "1" ]]; then
        skip "set HOMELAB_DNS_IMAGE_E2E=1 to run against the real dns image"
    fi
}

# The command as the compose file actually defines it — never a copy, or the
# test and the healthcheck drift apart.
probe() {
    uv run --project "${BATS_TEST_DIRNAME}/../../../tools/ci" python -c '
import sys, yaml
doc = yaml.safe_load(open(sys.argv[1]))
print(doc["services"]["dns-server"]["healthcheck"]["test"][1])
' "$COMPOSE"
}

@test "the compose file defines the probe as a shell command" {
    run probe
    assert_success
    assert_output --partial "dig"
}

@test "the probe passes while the server answers queries" {
    run docker exec "$CONTAINER" sh -c "$(probe)"
    assert_success
}

@test "the probe fails when nothing is listening" {
    # An unanchored grep passes here: the error `dig +short` prints on stdout
    # contains the address. That is the bug this test exists to catch.
    local live dead
    live="$(probe)"
    dead="${live/@127.0.0.1/-p 5399 @127.0.0.1}"
    [[ "$dead" != "$live" ]]
    run docker exec "$CONTAINER" sh -c "$dead"
    assert_failure
}
