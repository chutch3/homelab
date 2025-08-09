#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load ../scripts/test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true

    # Change to test directory
    cd "$TEST_TEMP_DIR" || return
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "swarm_stack_should_have_valid_yaml_syntax" {
    # Test that the stack.yaml file is valid YAML structure
    # Create minimal env files for validation
    echo "BASE_DOMAIN=test.example.com" > .env
    echo "DOMAIN_TEST=test.test.example.com" > .domains

    run docker compose -f "${BATS_TEST_DIRNAME}/../../../deployments/swarm/stack.yaml" config --quiet
    [ "$status" -eq 0 ]
}

@test "swarm_stack_should_have_proper_volume_syntax" {
    # Test that volume declarations are properly formatted
    run grep -E "^\s+-\s+\$\{PWD\}" "${BATS_TEST_DIRNAME}/../../../deployments/swarm/stack.yaml"
    [ "$status" -ne 0 ]  # Should not find volume syntax outside of volumes section
}

@test "swarm_stack_should_define_volumes_section" {
    # Test that volumes are properly defined in the volumes section
    run grep -A 20 "volumes:" "${BATS_TEST_DIRNAME}/../../../deployments/swarm/stack.yaml"
    [ "$status" -eq 0 ]
}

@test "swarm_stack_should_have_reverseproxy_service" {
    # Test that reverseproxy service is defined
    run grep -A 10 "reverseproxy:" "${BATS_TEST_DIRNAME}/../../../deployments/swarm/stack.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"image:"* ]]
}

@test "swarm_stack_should_have_valid_secrets_section" {
    # Test that secrets are properly defined
    run grep -A 10 "secrets:" "${BATS_TEST_DIRNAME}/../../../deployments/swarm/stack.yaml"
    [ "$status" -eq 0 ]
}

@test "swarm_stack_should_have_overlay_network" {
    # Test that overlay network is defined for swarm
    run grep -A 5 "networks:" "${BATS_TEST_DIRNAME}/../../../deployments/swarm/stack.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"driver: overlay"* ]]
}
