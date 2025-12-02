#!/usr/bin/env bats

load test_helper

setup() {
    TEST_TEMP_DIR="$(temp_make)"
    export PROJECT_ROOT="$TEST_TEMP_DIR"
    export TEST=true
}

teardown() {
    temp_del "$TEST_TEMP_DIR"
}

@test "cli.sh should exist and be executable" {
    [ -f "${BATS_TEST_DIRNAME}/../../../scripts/cli.sh" ]
    [ -x "${BATS_TEST_DIRNAME}/../../../scripts/cli.sh" ]
}

@test "cli.sh should show help with --help flag" {
    run "${BATS_TEST_DIRNAME}/../../../scripts/cli.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"USAGE:"* ]]
    [[ "$output" == *"COMMANDS:"* ]]
}

@test "cli.sh should show help with help command" {
    run "${BATS_TEST_DIRNAME}/../../../scripts/cli.sh" help
    [ "$status" -eq 0 ]
    [[ "$output" == *"USAGE:"* ]]
}

@test "cli.sh should default to docker swarm orchestrator" {
    # Mock the docker_swarm/cli.sh to verify it gets called
    mkdir -p "$TEST_TEMP_DIR/scripts/docker_swarm"
    cat > "$TEST_TEMP_DIR/scripts/docker_swarm/cli.sh" << 'EOF'
#!/bin/bash
echo "SWARM_CLI_CALLED"
exit 0
EOF
    chmod +x "$TEST_TEMP_DIR/scripts/docker_swarm/cli.sh"

    # Copy main cli.sh to test directory
    cp "${BATS_TEST_DIRNAME}/../../../scripts/cli.sh" "$TEST_TEMP_DIR/scripts/cli.sh"

    run "$TEST_TEMP_DIR/scripts/cli.sh" deploy
    [[ "$output" == *"SWARM_CLI_CALLED"* ]]
}

@test "cli.sh should accept --orchestrator swarm flag" {
    mkdir -p "$TEST_TEMP_DIR/scripts/docker_swarm"
    cat > "$TEST_TEMP_DIR/scripts/docker_swarm/cli.sh" << 'EOF'
#!/bin/bash
echo "SWARM_CLI_CALLED"
exit 0
EOF
    chmod +x "$TEST_TEMP_DIR/scripts/docker_swarm/cli.sh"

    cp "${BATS_TEST_DIRNAME}/../../../scripts/cli.sh" "$TEST_TEMP_DIR/scripts/cli.sh"

    run "$TEST_TEMP_DIR/scripts/cli.sh" --orchestrator swarm deploy
    [[ "$output" == *"SWARM_CLI_CALLED"* ]]
}

@test "cli.sh should reject unknown orchestrator" {
    run "${BATS_TEST_DIRNAME}/../../../scripts/cli.sh" --orchestrator unknown deploy
    [ "$status" -ne 0 ]
    [[ "$output" == *"Unknown orchestrator"* ]]
}

@test "cli.sh should pass arguments to orchestrator CLI" {
    mkdir -p "$TEST_TEMP_DIR/scripts/docker_swarm"
    cat > "$TEST_TEMP_DIR/scripts/docker_swarm/cli.sh" << 'EOF'
#!/bin/bash
echo "ARGS: $@"
exit 0
EOF
    chmod +x "$TEST_TEMP_DIR/scripts/docker_swarm/cli.sh"

    cp "${BATS_TEST_DIRNAME}/../../../scripts/cli.sh" "$TEST_TEMP_DIR/scripts/cli.sh"

    run "$TEST_TEMP_DIR/scripts/cli.sh" cluster init --config test.yaml
    [[ "$output" == *"ARGS: cluster init --config test.yaml"* ]]
}
