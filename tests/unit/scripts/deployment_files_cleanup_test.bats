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
    export GENERATED_SWARM_STACK="${TEST_TEMP_DIR}/deployments/swarm/stack.yaml"

    # Create config directory structure
    mkdir -p "${TEST_TEMP_DIR}/config"
    mkdir -p "${TEST_TEMP_DIR}/deployments/swarm"

    # Copy the real services.yaml for testing
    cp "${BATS_TEST_DIRNAME}/../../../config/services.yaml" "${SERVICES_CONFIG}"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT SERVICES_CONFIG GENERATED_SWARM_STACK
}

@test "static docker-compose.yaml should be replaceable by generated version" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Generate compose file
    run generate_compose_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create generated compose file
    [ -f "${PROJECT_ROOT}/generated-docker-compose.yaml" ]

    # Should contain all services from services.yaml
    run grep "actual:" "${PROJECT_ROOT}/generated-docker-compose.yaml"
    [ "$status" -eq 0 ]

    run grep "homepage:" "${PROJECT_ROOT}/generated-docker-compose.yaml"
    [ "$status" -eq 0 ]

    run grep "cryptpad:" "${PROJECT_ROOT}/generated-docker-compose.yaml"
    [ "$status" -eq 0 ]

    # Should contain networks section
    run grep "networks:" "${PROJECT_ROOT}/generated-docker-compose.yaml"
    [ "$status" -eq 0 ]
}

@test "generate_swarm_stack_from_services should create deployments/swarm/stack.yaml" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # This function should exist (will implement)
    run generate_swarm_stack_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create swarm stack file
    [ -f "${GENERATED_SWARM_STACK}" ]

    # Should contain swarm-specific configuration
    run grep "deploy:" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]

    # Should contain overlay networks
    run grep "driver: overlay" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]
}

@test "swarm stack should include reverseproxy with correct volumes and secrets" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Generate swarm stack
    run generate_swarm_stack_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should contain reverseproxy service
    run grep "reverseproxy:" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]

    # Should contain secrets section
    run grep "secrets:" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]

    run grep "ssl_full.pem:" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]

    # Should contain networks section
    run grep "networks:" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]
}

@test "generate_all_deployment_files should create both compose and swarm files" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # This function should be enhanced to include swarm generation
    run generate_all_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create both files
    [ -f "${PROJECT_ROOT}/generated-docker-compose.yaml" ]
    [ -f "${GENERATED_SWARM_STACK}" ]
}

@test "generated swarm stack should be valid docker swarm syntax" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Generate swarm stack
    run generate_swarm_stack_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Debug: check file exists
    [ -f "${GENERATED_SWARM_STACK}" ]

    # Should be valid YAML (basic syntax check using python)
    run poetry run python -c "import yaml; yaml.safe_load(open('${GENERATED_SWARM_STACK}'))"
    if [ "$status" -ne 0 ]; then
        echo "YAML validation failed: $output"
        cat "${GENERATED_SWARM_STACK}"
    fi
    [ "$status" -eq 0 ]

    # Should contain version info in header comments
    run grep "Generated Docker Swarm stack" "${GENERATED_SWARM_STACK}"
    [ "$status" -eq 0 ]
}
