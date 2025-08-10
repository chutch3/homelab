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

    # Create test services.yaml with minimal services
    cat > "${SERVICES_CONFIG}" <<EOF
version: "1.0"

categories:
  finance: "Finance & Budgeting"
  collaboration: "Collaboration & Productivity"

defaults:
  domain_pattern: "\${service}.\${BASE_DOMAIN}"

services:
  actual:
    name: "Actual Budget"
    category: finance
    domain: "budget"
    port: 5006

  cryptpad:
    name: "CryptPad"
    category: collaboration
    domain: "docs"
    domain_sandbox: "sandbox-docs"
    port: 3000

  homepage:
    name: "Homepage"
    category: core
    domain: "dashboard"
    port: 3000
EOF

    # Create test .env file
    echo "BASE_DOMAIN=test.local" >"${TEST_TEMP_DIR}/.env"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT SERVICES_CONFIG DOMAINS_FILE
}

@test "generate_domains_from_services creates .domains file with correct variables" {
    # Source the service generator script to get the function
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run the function
    run generate_domains_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Verify .domains file exists
    [ -f "${DOMAINS_FILE}" ]

    # Check for required base domain
    run grep "^BASE_DOMAIN=test.local$" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]

    # Check for service domains (these should be generated from services.yaml)
    run grep "^DOMAIN_ACTUAL=budget.test.local$" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]

    run grep "^DOMAIN_CRYPTPAD=docs.test.local$" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]

    run grep "^DOMAIN_HOMEPAGE=dashboard.test.local$" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]
}

@test "domains from services.yaml should work without .enabled-services file" {
    # Source the service generator script to get the function
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Ensure no .enabled-services file exists
    [ ! -f "${TEST_TEMP_DIR}/.enabled-services" ]

    # Run the function
    run generate_domains_from_services

    # Should succeed even without .enabled-services
    [ "$status" -eq 0 ]

    # Should still generate domains for all services in services.yaml
    [ -f "${DOMAINS_FILE}" ]
    run grep "DOMAIN_ACTUAL=budget.test.local" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]
}

@test "generated domains file should have proper header and be well-formed" {
    # Source the service generator script to get the function
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run the function
    run generate_domains_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Verify file starts with comment
    run head -n 1 "${DOMAINS_FILE}"
    [[ "$output" =~ ^#.*Generated ]]

    # Verify BASE_DOMAIN comes first after comments
    run grep -n "^BASE_DOMAIN=" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]
    [[ "$output" =~ ^[0-9]+:BASE_DOMAIN=test.local ]]
}

@test "domains should be normalized for environment variables" {
    # Add a service with special characters to test normalization
    cat >> "${SERVICES_CONFIG}" <<EOF
  my-special_service:
    name: "Special Service"
    category: finance
    domain: "special"
    port: 8080
EOF

    # Source the service generator script to get the function
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run the function
    run generate_domains_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Check that the domain variable is properly normalized
    run grep "^DOMAIN_MY_SPECIAL_SERVICE=special.test.local$" "${DOMAINS_FILE}"
    [ "$status" -eq 0 ]
}
