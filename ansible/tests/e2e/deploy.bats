#!/usr/bin/env bats

# The deploy path end to end: real ansible-playbook, real ci plan, real Swarm.
# Deploys fixtures under this directory via `stacks_root`, never the repo's own
# stacks. Gated on HOMELAB_ANSIBLE_E2E=1; skips without a swarm.

load "${BATS_TEST_DIRNAME}/../../../tests/helpers/bats-support/load"
load "${BATS_TEST_DIRNAME}/../../../tests/helpers/bats-assert/load"

REPO_ROOT="${BATS_TEST_DIRNAME}/../../.."
FIXTURES="${BATS_TEST_DIRNAME}/fixtures"
PLAYBOOK="ansible/playbooks/deploy/stacks.yml"
PROBES=(probe-app probe-base probe-stuck probe-unhealthy probe-slow probe-after)

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

# Seconds the named task took, from the profile_tasks summary.
task_seconds() {
    printf '%s\n' "$output" | grep -F -- "$1" | grep -oE '[0-9]+\.[0-9]+s$' | tail -1 | tr -d 's'
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
    refute_output --partial "TASK [Deploy probe-base]"

    after="$(spec_of probe-base_ready)"
    [[ "$before" == "$after" ]]
}

@test "an explicit target deploys even when it has already converged" {
    deploy converging probe-base
    assert_success
    assert_output --partial "TASK [Deploy probe-base]"
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

# Swarm holds a task in `starting` until its healthcheck passes, so a stack
# that declares one converges only when it is actually serving. This is what
# the dns stack relies on, and what a fixed-duration pause used to stand in for.
@test "a running task whose healthcheck fails is never converged" {
    deploy unhealthy probe-unhealthy -e converge_retries=4 -e converge_delay=2
    assert_failure
    assert_output --partial "probe-unhealthy did not converge"

    # The distinction that matters: the service exists and its container runs.
    run docker service ls --filter name=probe-unhealthy --format '{{.Replicas}}'
    assert_output --partial "0/1"
}

@test "a dependent waits for its dependency's healthcheck, not just its start" {
    deploy health-gated probe-after
    assert_success
    assert_output --partial "converged — probe-slow"

    local slow_converged dependent_deployed
    slow_converged="$(line_of "converged — probe-slow")"
    dependent_deployed="$(line_of "Deploy probe-after")"
    [[ -n "$slow_converged" && -n "$dependent_deployed" ]]
    (( slow_converged < dependent_deployed ))

    # probe-slow reports unhealthy for its first 15s. Time the convergence
    # probe itself, not the run: Ansible's own setup takes longer than 15s, so
    # wall-clock here would pass even with the healthcheck removed.
    local waited
    waited="$(task_seconds "Ask ci whether the stack has converged — probe-slow")"
    [[ -n "$waited" ]]
    (( ${waited%.*} >= 15 ))
}

# The replica column counts the outgoing task too, so a stack under update
# reads as 1/1 against the tasks it is replacing. Convergence must wait for the
# update to finish, not just for the count to look right.
@test "a redeploy is not converged until the new task is healthy, not the old one" {
    deploy health-gated probe-slow
    assert_success

    # Same stack, changed spec: this is an update, not a first deploy.
    deploy health-gated-v2 probe-slow
    assert_success
    assert_output --partial "TASK [Deploy probe-slow]"

    local waited
    waited="$(task_seconds "Ask ci whether the stack has converged — probe-slow")"
    [[ -n "$waited" ]]
    (( ${waited%.*} >= 15 ))
}

@test "a stack that never converges fails naming it" {
    deploy stuck probe-stuck -e converge_retries=2 -e converge_delay=2
    assert_failure
    assert_output --partial "probe-stuck did not converge"
}
