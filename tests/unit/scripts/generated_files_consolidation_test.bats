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
    export GENERATED_DIR="${TEST_TEMP_DIR}/generated"

    # Create config directory structure
    mkdir -p "${TEST_TEMP_DIR}/config"

    # Copy the real services.yaml for testing
    cp "${BATS_TEST_DIRNAME}/../../../config/services.yaml" "${SERVICES_CONFIG}"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT SERVICES_CONFIG GENERATED_DIR
}

@test "generate_all_to_generated_dir should create consolidated structure" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # This function should exist (will implement)
    run generate_all_to_generated_dir

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create generated directory structure
    [ -d "${GENERATED_DIR}" ]
    [ -d "${GENERATED_DIR}/deployments" ]
    [ -d "${GENERATED_DIR}/nginx" ]
    [ -d "${GENERATED_DIR}/config" ]

    # Should create consolidated deployment files
    [ -f "${GENERATED_DIR}/deployments/docker-compose.yaml" ]
    [ -f "${GENERATED_DIR}/deployments/swarm-stack.yaml" ]

    # Should create nginx templates
    [ -d "${GENERATED_DIR}/nginx/templates" ]

    # Should create config files
    [ -f "${GENERATED_DIR}/config/domains.env" ]
    [ -f "${GENERATED_DIR}/config/enabled-services.list" ]
}

@test "generated directory should have clear structure with README" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Generate consolidated files
    run generate_all_to_generated_dir

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create README explaining the structure
    [ -f "${GENERATED_DIR}/README.md" ]

    # README should explain the structure
    run grep "Generated Files" "${GENERATED_DIR}/README.md"
    [ "$status" -eq 0 ]

    run grep "DO NOT EDIT" "${GENERATED_DIR}/README.md"
    [ "$status" -eq 0 ]
}

@test "legacy files should be preserved during transition" {
    # Create some legacy files first
    touch "${PROJECT_ROOT}/generated-docker-compose.yaml"
    mkdir -p "${PROJECT_ROOT}/generated-nginx"
    touch "${PROJECT_ROOT}/generated-nginx/test.template"
    touch "${PROJECT_ROOT}/.domains"

    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Generate to new structure
    run generate_all_to_generated_dir

    # Check exit status
    [ "$status" -eq 0 ]

    # Legacy files should still exist
    [ -f "${PROJECT_ROOT}/generated-docker-compose.yaml" ]
    [ -d "${PROJECT_ROOT}/generated-nginx" ]
    [ -f "${PROJECT_ROOT}/.domains" ]

    # New structure should also exist
    [ -d "${GENERATED_DIR}" ]
    [ -f "${GENERATED_DIR}/deployments/docker-compose.yaml" ]
}

@test "generated files should have consistent headers and timestamps" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Generate consolidated files
    run generate_all_to_generated_dir

    # Check exit status
    [ "$status" -eq 0 ]

    # All generated files should have headers
    run grep "Generated from" "${GENERATED_DIR}/deployments/docker-compose.yaml"
    [ "$status" -eq 0 ]

    run grep "DO NOT EDIT" "${GENERATED_DIR}/deployments/docker-compose.yaml"
    [ "$status" -eq 0 ]

    # Should include generation timestamp
    run grep "Generated.*$(date +%Y)" "${GENERATED_DIR}/deployments/docker-compose.yaml"
    [ "$status" -eq 0 ]
}

@test "generated directory should be .gitignore friendly" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Generate consolidated files
    run generate_all_to_generated_dir

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create or update .gitignore entry
    [ -f "${GENERATED_DIR}/.gitignore" ]

    # .gitignore should ignore generated content
    run grep "\*" "${GENERATED_DIR}/.gitignore"
    [ "$status" -eq 0 ]

    run grep "!README.md" "${GENERATED_DIR}/.gitignore"
    [ "$status" -eq 0 ]
}

@test "update_all_scripts_for_generated_dir should modify path references" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # This function should update script paths
    run update_all_scripts_for_generated_dir

    # Check exit status
    [ "$status" -eq 0 ]

    # Should report what scripts were updated
    [[ "$output" =~ "Updated script paths" ]]
}

@test "deployment commands should use generated directory structure" {
    # Enable some services first
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"
    enable_services_via_yaml "actual" "homepage"

    # Generate to new structure
    generate_all_to_generated_dir

    # Mock docker compose command
    docker() {
        echo "docker $*"
        return 0
    }
    export -f docker

    # Test using new paths (will implement)
    run start_enabled_services_from_generated

    # Check exit status
    [ "$status" -eq 0 ]

    # Should use generated directory paths
    [[ "$output" =~ "generated/deployments" ]]
}

@test "cleanup_legacy_generated_files should remove old structure" {
    # Create legacy files
    touch "${PROJECT_ROOT}/generated-docker-compose.yaml"
    mkdir -p "${PROJECT_ROOT}/generated-nginx"
    touch "${PROJECT_ROOT}/generated-nginx/test.template"
    touch "${PROJECT_ROOT}/.domains"
    touch "${PROJECT_ROOT}/.enabled-services"

    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # This function should clean up old files (after migration)
    run cleanup_legacy_generated_files

    # Check exit status
    [ "$status" -eq 0 ]

    # Legacy files should be removed
    [ ! -f "${PROJECT_ROOT}/generated-docker-compose.yaml" ]
    [ ! -d "${PROJECT_ROOT}/generated-nginx" ]
    [ ! -f "${PROJECT_ROOT}/.domains" ]

    # .enabled-services should be preserved (user data)
    [ -f "${PROJECT_ROOT}/.enabled-services" ]
}
