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
    export DOMAINS_FILE="${TEST_TEMP_DIR}/.domains"

    # Create config directory
    mkdir -p "${TEST_TEMP_DIR}/config"

    # Create test services.yaml
    cat > "${SERVICES_CONFIG}" <<EOF
version: "1.0"

categories:
  finance: "Finance & Budgeting"

defaults:
  domain_pattern: "\${service}.\${BASE_DOMAIN}"

services:
  actual:
    name: "Actual Budget"
    category: finance
    domain: "budget"
    port: 5006
    compose:
      image: "actualbudget/actual-server:latest"
      ports:
        - "5006:5006"
EOF

    # Create test .env file
    echo "BASE_DOMAIN=test.local" >"${TEST_TEMP_DIR}/.env"

    # Create directories that up() function expects
    mkdir -p "${TEST_TEMP_DIR}/config/services/reverseproxy/templates/conf.d/enabled"
    mkdir -p "${TEST_TEMP_DIR}/config/services/reverseproxy/ssl"

    # Create empty .enabled-services file for legacy compatibility
    echo "actual" > "${TEST_TEMP_DIR}/.enabled-services"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT SERVICES_CONFIG DOMAINS_FILE
}

@test "up() function should use services.yaml for domain generation instead of legacy build_domain.sh" {
    # Source both scripts to get the functions
    # shellcheck source=/dev/null
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Mock the functions that up() calls to avoid side effects
    start_enabled_services() { echo "mock: starting services"; }
    setup_templates() { echo "mock: setting up templates"; }
    export -f start_enabled_services setup_templates

    # Create a load_env function for the test
    load_env() {
        if [ -f "${PROJECT_ROOT}/.env" ]; then
            # shellcheck source=/dev/null
            source "${PROJECT_ROOT}/.env"
        fi
    }

    # Create a modified up() function that uses the new system
    up_new() {
        load_env

        # Use generate_domains_from_services instead of build_domain.sh
        generate_domains_from_services

        set -a
        # shellcheck source=/dev/null
        source "${DOMAINS_FILE}"
        set +a
        env | grep -E '^(DOMAIN|BASE_DOMAIN)'

        setup_templates
        start_enabled_services
    }

    # Run the new up function
    run up_new

    # Check exit status
    [ "$status" -eq 0 ]

    # Verify .domains file was created
    [ -f "${DOMAINS_FILE}" ]

    # Verify it contains the correct domain from services.yaml
    run grep "DOMAIN_ACTUAL=budget.test.local" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]

    # Verify the output shows domain variables
    [[ "$output" =~ DOMAIN_ACTUAL=budget.test.local ]]

    # BASE_DOMAIN should be available in the environment after sourcing .domains
    run bash -c "source ${DOMAINS_FILE} && echo \$BASE_DOMAIN"
    [ "$status" -eq 0 ]
    [[ "$output" =~ test.local ]]
}

@test "new domain generation should not depend on .enabled-services file" {
    # Remove .enabled-services file
    rm -f "${TEST_TEMP_DIR}/.enabled-services"

    # Source service generator
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run domain generation
    run generate_domains_from_services

    # Should succeed without .enabled-services
    [ "$status" -eq 0 ]

    # Should generate domains for all services in services.yaml
    [ -f "${DOMAINS_FILE}" ]
    run grep "DOMAIN_ACTUAL=budget.test.local" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]
}

@test "domains from services.yaml should match legacy format exactly" {
    # Source service generator
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Generate domains from services.yaml
    run generate_domains_from_services
    [ "$status" -eq 0 ]

    # Check the format matches what docker-compose expects
    run grep "^BASE_DOMAIN=test.local$" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]

    run grep "^DOMAIN_ACTUAL=budget.test.local$" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]

    # Verify no extra whitespace or formatting issues
    run cat "${DOMAINS_FILE}"
    [[ ! "$output" =~ [[:space:]]$ ]] # No trailing whitespace
}
