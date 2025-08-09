#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true

    # Mock docker-compose commands
    export DOCKER_COMPOSE_COMMANDS_FILE="${TEST_TEMP_DIR}/docker_compose_commands.log"
    true > "$DOCKER_COMPOSE_COMMANDS_FILE"

    docker-compose() {
        echo "docker-compose $*" >> "$DOCKER_COMPOSE_COMMANDS_FILE"
        echo "Docker Compose executed: $*" >&2
        return 0
    }
    export -f docker-compose

    # Source the compose script
    cd "$TEST_TEMP_DIR" || return
    source "${BATS_TEST_DIRNAME}/../../../scripts/deployments/compose.sh"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "compose_up_should_call_docker_compose_up" {
    run compose_up
    [ "$status" -eq 0 ]
    [[ "$output" == *"Starting services with Docker Compose..."* ]]

    # Check that docker-compose up was called
    run cat "$DOCKER_COMPOSE_COMMANDS_FILE"
    [[ "$output" == *"docker-compose up -d"* ]]
}

@test "compose_up_should_pass_arguments_to_docker_compose" {
    run compose_up service1 service2
    [ "$status" -eq 0 ]

    # Check that arguments were passed through
    run cat "$DOCKER_COMPOSE_COMMANDS_FILE"
    [[ "$output" == *"docker-compose up -d service1 service2"* ]]
}

@test "compose_down_should_call_docker_compose_down" {
    run compose_down
    [ "$status" -eq 0 ]
    [[ "$output" == *"Stopping services..."* ]]

    # Check that docker-compose down was called
    run cat "$DOCKER_COMPOSE_COMMANDS_FILE"
    [[ "$output" == *"docker-compose down"* ]]
}

@test "compose_down_should_pass_arguments_to_docker_compose" {
    run compose_down --volumes --remove-orphans
    [ "$status" -eq 0 ]

    # Check that arguments were passed through
    run cat "$DOCKER_COMPOSE_COMMANDS_FILE"
    [[ "$output" == *"docker-compose down --volumes --remove-orphans"* ]]
}

@test "compose_logs_should_call_docker_compose_logs" {
    run compose_logs
    [ "$status" -eq 0 ]
    [[ "$output" == *"Showing logs..."* ]]

    # Check that docker-compose logs was called
    run cat "$DOCKER_COMPOSE_COMMANDS_FILE"
    [[ "$output" == *"docker-compose logs"* ]]
}

@test "compose_logs_should_pass_arguments_to_docker_compose" {
    run compose_logs -f service1
    [ "$status" -eq 0 ]

    # Check that arguments were passed through
    run cat "$DOCKER_COMPOSE_COMMANDS_FILE"
    [[ "$output" == *"docker-compose logs -f service1"* ]]
}

@test "compose_functions_should_exist" {
    # Test that all expected functions are defined
    run type compose_up
    [ "$status" -eq 0 ]
    [[ "$output" == *"compose_up is a function"* ]]

    run type compose_down
    [ "$status" -eq 0 ]
    [[ "$output" == *"compose_down is a function"* ]]

    run type compose_logs
    [ "$status" -eq 0 ]
    [[ "$output" == *"compose_logs is a function"* ]]
}
