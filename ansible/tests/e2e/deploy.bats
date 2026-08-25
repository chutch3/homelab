#!/usr/bin/env bats

# The deploy path end to end: real ansible-playbook, real ci plan, real Swarm.
# Deploys fixtures under this directory via `stacks_root`, never the repo's own
# stacks. Gated on HOMELAB_ANSIBLE_E2E=1; skips without a swarm.

load "${BATS_TEST_DIRNAME}/../../../tests/helpers/bats-support/load"
load "${BATS_TEST_DIRNAME}/../../../tests/helpers/bats-assert/load"

REPO_ROOT="${BATS_TEST_DIRNAME}/../../.."
FIXTURES="${BATS_TEST_DIRNAME}/fixtures"
PLAYBOOK="ansible/playbooks/deploy/stacks.yml"
PROBES=(probe-app probe-base probe-stuck)

setup_file() {
    if [[ "${HOMELAB_ANSIBLE_E2E:-}" != "1" ]]; then
        skip "set HOMELAB_ANSIBLE_E2E=1 to run against a real swarm"
    fi
    if [[ "$(docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null)" != "active" ]]; then
        skip "no active docker swarm on this daemon"
    fi
}

teardown_file() {
    local stack
    for stack in "${PROBES[@]}"; do
        docker stack rm "$stack" >/dev/null 2>&1 || true
    done
}

setup() {
    if [[ "${HOMELAB_ANSIBLE_E2E:-}" != "1" ]]; then
        skip "set HOMELAB_ANSIBLE_E2E=1 to run against a real swarm"
    fi
    cd "$REPO_ROOT" || return 1
}

# $1 fixture root, $2 targets (empty for all), rest passed to ansible.
deploy() {
    local root="$1" stacks="$2"
    shift 2
    run env ANSIBLE_CONFIG=ansible/ansible.cfg uv run ansible-playbook \
        -i ansible/inventory/ "$PLAYBOOK" \
        -e "stacks=${stacks}" \
        -e "stacks_root=${FIXTURES}/${root}" \
        -e register_dns=false -e register_uptime=false "$@"
}

line_of() {
    printf '%s\n' "$output" | grep -n -- "$1" | head -1 | cut -d: -f1
}

spec_of() {
    docker service inspect "$1" --format '{{json .Spec}}'
}

@test "a dependency converges before its dependent is deployed" {
    deploy converging probe-app
    assert_success
    assert_output --partial "Deploy probe-base"
    assert_output --partial "Deploy probe-app"

    local base_converged dependent_deployed
    base_converged="$(line_of "converged — probe-base")"
    dependent_deployed="$(line_of "Deploy probe-app")"
    [[ -n "$base_converged" && -n "$dependent_deployed" ]]
    (( base_converged < dependent_deployed ))
}

@test "an ensured dependency that has converged is skipped, spec untouched" {
    local before after
    before="$(spec_of probe-base_ready)"

    deploy converging probe-app
    assert_success
    assert_output --partial "already converged (probe-base)"
    refute_output --partial "TASK [swarm : Deploy probe-base]"

    after="$(spec_of probe-base_ready)"
    [[ "$before" == "$after" ]]
}

@test "an explicit target deploys even when it has already converged" {
    deploy converging probe-base
    assert_success
    assert_output --partial "TASK [swarm : Deploy probe-base]"
    assert_output --partial "1 to deploy"
}

@test "a second identical run deploys nothing" {
    deploy converging ""
    assert_success

    deploy converging ""
    assert_success
    assert_output --partial "0 to deploy, 2 already converged"
    assert_output --partial "changed=0"
}

@test "a stack that never converges fails naming it" {
    deploy stuck probe-stuck -e converge_retries=2 -e converge_delay=2
    assert_failure
    assert_output --partial "probe-stuck did not converge"
}
