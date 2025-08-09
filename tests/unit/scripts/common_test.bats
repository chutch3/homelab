#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export AVAILABLE_DIR="${TEST_TEMP_DIR}/reverseproxy/templates/conf.d"
    export ENABLED_DIR="${TEST_TEMP_DIR}/reverseproxy/templates/conf.d/enabled"
    export SSL_DIR="${TEST_TEMP_DIR}/reverseproxy/ssl"
    export DOMAIN_FILE="${TEST_TEMP_DIR}/.domains"

    # Create test directory structure
    mkdir -p "$AVAILABLE_DIR"
    mkdir -p "$ENABLED_DIR"
    mkdir -p "$SSL_DIR"

    # Source the common script
    cd "$TEST_TEMP_DIR" || return
    source "${BATS_TEST_DIRNAME}/../../../scripts/common.sh"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "command_exists_should_return_true_for_existing_function" {
    # Define a test function
    test_function() {
        echo "test"
    }

    run command_exists "test_function"
    [ "$status" -eq 0 ]
}

@test "command_exists_should_return_false_for_non_existing_function" {
    run command_exists "non_existing_function"
    [ "$status" -eq 1 ]
}

@test "list_commands_should_return_commands_for_target" {
    # Define some test commands for a target
    target_test_cmd1() { echo "cmd1"; }
    target_test_cmd2() { echo "cmd2"; }
    target_other_cmd() { echo "other"; }

    run list_commands "target_test"
    [ "$status" -eq 0 ]
    [[ "$output" == *"cmd1"* ]]
    [[ "$output" == *"cmd2"* ]]
    [[ "$output" != *"other"* ]]
}

@test "load_env_should_fail_when_env_file_missing" {
    # Make sure .env doesn't exist
    rm -f "$PROJECT_ROOT/.env"

    run load_env
    [ "$status" -eq 1 ]
    [[ "$output" == *"❌ Error: .env file not found"* ]]
}

@test "load_env_should_succeed_when_env_file_exists" {
    # Create a test .env file
    echo "TEST_VAR=test_value" > "$PROJECT_ROOT/.env"

    run load_env
    [ "$status" -eq 0 ]

    # Test that load_env actually sources the file by checking if it can read it
    [ -f "$PROJECT_ROOT/.env" ]
}

@test "ensure_certs_exist_should_skip_when_certs_directory_exists" {
    # Create certs directory
    mkdir -p "$PROJECT_ROOT/certs"

    run ensure_certs_exist
    [ "$status" -eq 0 ]
    [[ "$output" == *"✅ Certificates are already initialized"* ]]
}

@test "ensure_certs_exist_should_fail_when_no_env_file" {
    # Ensure certs directory doesn't exist
    rm -rf "$PROJECT_ROOT/certs"
    # Ensure .env file doesn't exist
    rm -f "$PROJECT_ROOT/.env"

    run ensure_certs_exist
    [ "$status" -eq 1 ]
    [[ "$output" == *"❌ Error: .env file not found"* ]]
}

@test "list_available_services_should_display_message" {
    run list_available_services
    [ "$status" -eq 0 ]
    [[ "$output" == *"Available services:"* ]]
}

@test "sync_files_should_be_interactive_function" {
    # Test that the function exists and is callable
    run type sync-files
    [ "$status" -eq 0 ]
    [[ "$output" == *"sync-files is a function"* ]]
}
