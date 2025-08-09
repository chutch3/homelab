#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export PROJECT_ROOT="${TEST_TEMP_DIR}"

    # Test the consolidated SSH file when we create it
    if [ -f "${BATS_TEST_DIRNAME}/../../../scripts/ssh.sh" ]; then
        source "${BATS_TEST_DIRNAME}/../../../scripts/ssh.sh"
    fi
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "ssh_key_auth_should_be_available_after_consolidation" {
    # Test that the core ssh_key_auth function exists
    run type ssh_key_auth
    [ "$status" -eq 0 ]
    [[ "$output" == *"ssh_key_auth is a function"* ]]
}

@test "ssh_password_auth_should_be_available_after_consolidation" {
    # Test that ssh_password_auth function exists
    run type ssh_password_auth
    [ "$status" -eq 0 ]
    [[ "$output" == *"ssh_password_auth is a function"* ]]
}

@test "ssh_copy_id_should_be_available_after_consolidation" {
    # Test that ssh_copy_id function exists
    run type ssh_copy_id
    [ "$status" -eq 0 ]
    [[ "$output" == *"ssh_copy_id is a function"* ]]
}

@test "ssh_docker_command_should_be_available_after_consolidation" {
    # Test that the higher-level ssh_docker_command function exists
    run type ssh_docker_command
    [ "$status" -eq 0 ]
    [[ "$output" == *"ssh_docker_command is a function"* ]]
}

@test "ssh_test_connection_should_be_available_after_consolidation" {
    # Test that ssh_test_connection function exists
    run type ssh_test_connection
    [ "$status" -eq 0 ]
    [[ "$output" == *"ssh_test_connection is a function"* ]]
}

@test "ssh_execute_should_be_available_after_consolidation" {
    # Test that ssh_execute function exists
    run type ssh_execute
    [ "$status" -eq 0 ]
    [[ "$output" == *"ssh_execute is a function"* ]]
}

@test "ssh_environment_variables_should_be_set" {
    # Test that SSH environment variables are properly set
    [ -n "$SSH_KEY_FILE" ]
    [ -n "$SSH_TIMEOUT" ]

    # Should have default values
    [[ "$SSH_KEY_FILE" == *".ssh/selfhosted_rsa" ]]
    [ "$SSH_TIMEOUT" = "5" ]
}
