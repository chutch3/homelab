#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export BASE_DOMAIN="test.local"
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export SERVICES_CONFIG="${TEST_TEMP_DIR}/config/services.yaml"

    # Create config directory structure
    mkdir -p "${TEST_TEMP_DIR}/config"
    mkdir -p "${TEST_TEMP_DIR}/config/services/reverseproxy/templates/conf.d/enabled"

    # Copy the real services.yaml for testing
    cp "${BATS_TEST_DIRNAME}/../../../config/services.yaml" "${SERVICES_CONFIG}"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT SERVICES_CONFIG
}

@test "selfhosted.sh should provide service enable command" {
    # Test the service enable command directly
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service enable actual homepage

    # Check exit status
    [ "$status" -eq 0 ]

    # Should enable services in services.yaml
    [[ "$output" =~ "Enabling service: actual" ]]
    [[ "$output" =~ "Enabling service: homepage" ]]
    [[ "$output" =~ Successfully\ enabled\ 2\ service\(s\) ]]

    # Verify services are enabled in config
    run yq '.services.actual.enabled' "${SERVICES_CONFIG}"
    [ "$output" = "true" ]

    run yq '.services.homepage.enabled' "${SERVICES_CONFIG}"
    [ "$output" = "true" ]
}

@test "selfhosted.sh should provide service disable command" {
    # First enable some services
    bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service enable actual homepage

    # Test the service disable command
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service disable actual

    # Check exit status
    [ "$status" -eq 0 ]

    # Should disable services in services.yaml
    [[ "$output" =~ "Disabling service: actual" ]]
    [[ "$output" =~ Successfully\ disabled\ 1\ service\(s\) ]]

    # Verify service is disabled in config
    run yq '.services.actual.enabled' "${SERVICES_CONFIG}"
    [ "$output" = "false" ]

    # Homepage should still be enabled
    run yq '.services.homepage.enabled' "${SERVICES_CONFIG}"
    [ "$output" = "true" ]
}

@test "selfhosted.sh should provide service status command" {
    # First enable some services
    bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service enable actual homepage

    # Test the service status command
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service status

    # Check exit status
    [ "$status" -eq 0 ]

    # Should show enabled services
    [[ "$output" =~ "Service Status Overview" ]]
    [[ "$output" =~ "actual" ]]
    [[ "$output" =~ "homepage" ]]
}

@test "legacy migration function should work independently" {
    # Create legacy .enabled-services file
    cat > "${TEST_TEMP_DIR}/.enabled-services" <<EOF
actual
homepage
EOF

    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Test migration function directly
    run migrate_from_legacy_enabled_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should mention migration
    [[ "$output" =~ "Migrating from legacy" ]]

    # Should migrate to services.yaml
    run yq '.services.actual.enabled' "${SERVICES_CONFIG}"
    [ "$output" = "true" ]

    run yq '.services.homepage.enabled' "${SERVICES_CONFIG}"
    [ "$output" = "true" ]

    # Should backup legacy file
    [ -f "${TEST_TEMP_DIR}/.enabled-services.backup" ]

    # Should remove legacy file
    [ ! -f "${TEST_TEMP_DIR}/.enabled-services" ]
}

@test "generate_enabled_services_from_yaml should create backward compatibility file" {
    # Enable some services first
    bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service enable actual homepage

    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Test the generation function directly
    run generate_enabled_services_from_yaml

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create .enabled-services file for backward compatibility
    [ -f "${TEST_TEMP_DIR}/.enabled-services" ]

    # Should contain enabled services
    run grep "actual" "${TEST_TEMP_DIR}/.enabled-services"
    [ "$status" -eq 0 ]

    run grep "homepage" "${TEST_TEMP_DIR}/.enabled-services"
    [ "$status" -eq 0 ]
}
