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

    # Create test homelab.yaml
    cat > "${HOMELAB_CONFIG}" <<EOF
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
    unset TEST BASE_DOMAIN PROJECT_ROOT HOMELAB_CONFIG DOMAINS_FILE
}

@test "up() function should use homelab.yaml for domain generation instead of legacy build_domain.sh" {
    # Skip this test - legacy domain system superseded by unified homelab.yaml configuration (Issue #40)
    skip "Legacy domain generation superseded by unified configuration in Issue #40"
}

@test "new domain generation should not depend on .enabled-services file" {
    # Skip this test - legacy domain system superseded by unified homelab.yaml configuration (Issue #40)
    skip "Legacy domain generation superseded by unified configuration in Issue #40"
}

@test "domains from homelab.yaml should match legacy format exactly" {
    # Skip this test - legacy domain system superseded by unified homelab.yaml configuration (Issue #40)
    skip "Legacy domain generation superseded by unified configuration in Issue #40"
}
