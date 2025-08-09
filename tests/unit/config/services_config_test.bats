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

@test "services_yaml_should_exist" {
    # Test that the unified services.yaml configuration exists
    [ -f "${BATS_TEST_DIRNAME}/../../../config/services.yaml" ]
}

@test "services_yaml_should_be_valid_yaml" {
    # Test that services.yaml is valid YAML
    run yq '.' "${BATS_TEST_DIRNAME}/../../../config/services.yaml"
    [ "$status" -eq 0 ]
}

@test "services_yaml_should_contain_actual_service" {
    # Test that actual budget service is defined
    run yq '.services.actual.name' "${BATS_TEST_DIRNAME}/../../../config/services.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == '"Actual Budget"' ]]
}

@test "services_yaml_should_define_service_metadata" {
    # Test that services have required metadata
    run yq '.services.actual.description' "${BATS_TEST_DIRNAME}/../../../config/services.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" != "null" ]]

    run yq '.services.actual.category' "${BATS_TEST_DIRNAME}/../../../config/services.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == '"finance"' ]]
}

@test "services_yaml_should_define_domain_patterns" {
    # Test that services have domain configuration
    run yq '.services.actual.domain' "${BATS_TEST_DIRNAME}/../../../config/services.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == '"budget"' ]]
}

@test "services_yaml_should_define_compose_config" {
    # Test that services have compose configuration
    run yq '.services.actual.compose' "${BATS_TEST_DIRNAME}/../../../config/services.yaml"
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
