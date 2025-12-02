#!/usr/bin/env bats

load ../test_helper

setup() {
    TEST_TEMP_DIR="$(temp_make)"
    export PROJECT_ROOT="$TEST_TEMP_DIR"
    export TEST=true
}

teardown() {
    temp_del "$TEST_TEMP_DIR"
}

@test "docker_swarm/cli.sh should exist and be executable" {
    [ -f "${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh" ]
    [ -x "${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh" ]
}

@test "docker_swarm/cli.sh should show help with --help flag" {
    run "${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"USAGE:"* ]]
    [[ "$output" == *"COMMANDS:"* ]]
}

@test "docker_swarm/cli.sh should show help with help command" {
    run "${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh" help
    [ "$status" -eq 0 ]
    [[ "$output" == *"USAGE:"* ]]
}

@test "docker_swarm/cli.sh should support deploy command" {
    run "${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh" deploy --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"deploy"* ]]
}

@test "docker_swarm/cli.sh should support cluster init command" {
    run "${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh" cluster init --help
    [ "$status" -eq 0 ]
}

@test "docker_swarm/cli.sh should support cluster status command" {
    run "${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh" cluster status --help
    [ "$status" -eq 0 ]
}

@test "docker_swarm/cli.sh should support teardown command" {
    run "${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh" teardown --help
    [ "$status" -eq 0 ]
}

@test "docker_swarm/cli.sh should reject unknown command" {
    run "${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh" unknown-command
    [ "$status" -ne 0 ]
    [[ "$output" == *"Unknown command"* ]]
}

@test "docker_swarm/cli.sh should have volume command in help output" {
    run "${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "volume" ]]
}

@test "docker_swarm/cli.sh should route volume ls command to volume.sh" {
    local cli_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh"

    # Check that volume command case exists
    run grep -A5 "^\s*volume)" "$cli_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "volume.sh" ]]
}

@test "docker_swarm/cli.sh should pass volume subcommands to volume.sh" {
    local cli_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh"

    # Check that volume subcommand is passed through
    run grep "volume.sh" "$cli_script"
    [ "$status" -eq 0 ]
}

@test "docker_swarm/cli.sh should route volume diff command" {
    local cli_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh"

    # Check that diff subcommand is handled
    run grep -A20 "^\s*volume)" "$cli_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "diff" ]]
}

@test "docker_swarm/cli.sh should route volume recreate command" {
    local cli_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/cli.sh"

    # Check that recreate subcommand is handled
    run grep -A25 "^\s*volume)" "$cli_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "recreate" ]]
}
