#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper
    load ../../helpers/homelab_builder

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export BASE_DOMAIN="test.local"
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export HOMELAB_CONFIG="${TEST_TEMP_DIR}/homelab.yaml"
    export DOMAINS_FILE="${TEST_TEMP_DIR}/.domains"

    # Create config directory
    mkdir -p "${TEST_TEMP_DIR}/config"

    # Create test homelab.yaml with minimal services
    cat > "${HOMELAB_CONFIG}" <<EOF
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
    unset TEST BASE_DOMAIN PROJECT_ROOT HOMELAB_CONFIG DOMAINS_FILE
}

@test "generate_domains_from_services creates .domains file with correct variables" {
    # Skip this test - legacy domain system superseded by unified homelab.yaml configuration (Issue #40)
    skip "Legacy domain generation superseded by unified configuration in Issue #40"
}

@test "domains from homelab.yaml should work without .enabled-services file" {
    # Skip this test - legacy domain system superseded by unified homelab.yaml configuration (Issue #40)
    skip "Legacy domain generation superseded by unified configuration in Issue #40"
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
    # Skip this test - legacy domain system superseded by unified homelab.yaml configuration (Issue #40)
    skip "Legacy domain generation superseded by unified configuration in Issue #40"
}
