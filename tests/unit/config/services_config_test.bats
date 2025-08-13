#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load ../scripts/test_helper
    load ../../helpers/homelab_builder

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test homelab.yaml
    TEST_HOMELAB_CONFIG="${TEST_TEMP_DIR}/homelab.yaml"
    copy_test_fixture "$TEST_HOMELAB_CONFIG"

    # Set up test environment variables
    export TEST=true

    # Change to test directory
    cd "$TEST_TEMP_DIR" || return
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "homelab_config_should_exist" {
    # Test that the homelab.yaml configuration exists
    [ -f "$TEST_HOMELAB_CONFIG" ]
}

@test "homelab_config_should_be_valid_yaml" {
    # Test that homelab.yaml is valid YAML
    run yq '.' "$TEST_HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
}

@test "homelab_config_should_contain_actual_service" {
    # Test that actual budget service is defined
    run yq '.services.actual.name' "$TEST_HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    # Handle both quoted (python yq) and unquoted (go yq) output
    [[ "$output" == '"Actual Budget"' || "$output" == 'Actual Budget' ]]
}

@test "homelab_config_should_define_service_metadata" {
    # Test that services have required metadata
    run yq '.services.actual.description' "$TEST_HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" != "null" ]]

    run yq '.services.actual.category' "$TEST_HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    # Handle both quoted (python yq) and unquoted (go yq) output
    [[ "$output" == '"finance"' || "$output" == 'finance' ]]
}

@test "homelab_config_should_define_domain_patterns" {
    # Test that services have domain configuration
    run yq '.services.actual.domain' "$TEST_HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    # Handle both quoted (python yq) and unquoted (go yq) output
    [[ "$output" == '"budget"' || "$output" == 'budget' ]]
}

@test "homelab_config_should_define_compose_config" {
    # Test that services have compose configuration
    run yq '.services.actual.compose' "$TEST_HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" != "null" ]]
}

@test "services_yaml_should_define_swarm_config" {
    # Test that services have swarm-specific overrides
    run yq '.swarm.services.actual' "${BATS_TEST_DIRNAME}/../../../config/services.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" != "null" ]]
}

@test "services_yaml_should_define_nginx_template" {
    # Test that services have nginx configuration
    run yq '.services.actual.nginx' "${BATS_TEST_DIRNAME}/../../../config/services.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" != "null" ]]
}
