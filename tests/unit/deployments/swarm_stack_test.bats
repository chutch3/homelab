#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load ../scripts/test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export BASE_DOMAIN="test.example.com"
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export SERVICES_CONFIG="${TEST_TEMP_DIR}/config/services.yaml"
    export GENERATED_SWARM_STACK="${TEST_TEMP_DIR}/deployments/swarm/stack.yaml"

    # Create config directory structure
    mkdir -p "${TEST_TEMP_DIR}/config"
    mkdir -p "${TEST_TEMP_DIR}/deployments/swarm"

    # Copy the real services.yaml for testing
    cp "${BATS_TEST_DIRNAME}/../../../config/services.yaml" "${SERVICES_CONFIG}"

    # Generate the swarm stack file for testing
    # shellcheck disable=SC1091
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"
    generate_swarm_stack_from_services

    # Change to test directory
    cd "$TEST_TEMP_DIR" || return
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT SERVICES_CONFIG GENERATED_SWARM_STACK
}

@test "swarm_stack_should_have_valid_yaml_syntax" {
    # Test that the stack.yaml file is valid YAML structure
    # Create minimal env files for validation
    echo "BASE_DOMAIN=test.example.com" > .env
    echo "DOMAIN_TEST=test.test.example.com" > .domains

    run docker compose -f "${GENERATED_SWARM_STACK}" config --quiet
    [ "$status" -eq 0 ]
}

@test "swarm_stack_should_have_proper_volume_syntax" {
    # Test that volume declarations are properly formatted
    run grep -E "^\s+-\s+\$\{PWD\}" "${GENERATED_SWARM_STACK}"
    [ "$status" -ne 0 ]  # Should not find volume syntax outside of volumes section
}

@test "swarm_stack_should_define_volumes_section" {
    # Test that volumes are properly defined in the volumes section
    run grep -A 20 "volumes:" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]
}

@test "swarm_stack_should_have_reverseproxy_service" {
    # Test that reverseproxy service is defined
    run grep -A 10 "reverseproxy:" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]
    [[ "$output" == *"image:"* ]]
}

@test "swarm_stack_should_have_valid_secrets_section" {
    # Test that secrets are properly defined
    run grep -A 10 "secrets:" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]
}

@test "swarm_stack_should_have_overlay_network" {
    # Test that overlay network is defined for swarm
    run grep -A 5 "networks:" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]
    [[ "$output" == *"driver: overlay"* ]]
}
