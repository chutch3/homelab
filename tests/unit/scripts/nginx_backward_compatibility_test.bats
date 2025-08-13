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
    export HOMELAB_CONFIG="${TEST_TEMP_DIR}/homelab.yaml"
    export GENERATED_NGINX_DIR="${TEST_TEMP_DIR}/generated-nginx"

    # Create config directory
    mkdir -p "${TEST_TEMP_DIR}/config"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT HOMELAB_CONFIG GENERATED_NGINX_DIR
}

@test "existing services.yaml nginx config should work with new generator" {
    # Copy the real services.yaml structure for a typical service
    cat > "${HOMELAB_CONFIG}" <<EOF
version: "1.0"

categories:
  finance: "Finance & Budgeting"

services:
  actual:
    name: "Actual Budget"
    category: finance
    domain: "budget"
    port: 5006
    nginx:
      upstream: "actual_server:5006"
      additional_config: |
        location / {
            proxy_pass http://actual_server:5006;
            proxy_set_header Cross-Origin-Embedder-Policy require-corp;
            proxy_set_header Cross-Origin-Opener-Policy same-origin;
        }
EOF

    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run nginx generation
    run generate_nginx_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create nginx file for actual
    [ -f "${GENERATED_NGINX_DIR}/actual.template" ]

    # Should contain HTTP redirect
    run grep "return 301 https" "${GENERATED_NGINX_DIR}/actual.template"
    [ "$status" -eq 0 ]

    # Should contain SSL config
    run grep "include /etc/nginx/conf.d/includes/ssl" "${GENERATED_NGINX_DIR}/actual.template"
    [ "$status" -eq 0 ]

    # Should contain the custom configuration from existing services.yaml
    run grep "Cross-Origin-Embedder-Policy require-corp" "${GENERATED_NGINX_DIR}/actual.template"
    [ "$status" -eq 0 ]

    # Should use correct domain variable
    run grep "\${DOMAIN_ACTUAL}" "${GENERATED_NGINX_DIR}/actual.template"
    [ "$status" -eq 0 ]
}

@test "service without nginx config should get default proxy setup" {
    # Create a minimal service without custom nginx config
    cat > "${HOMELAB_CONFIG}" <<EOF
version: "1.0"

categories:
  core: "Core Infrastructure"

services:
  minimal:
    name: "Minimal Service"
    category: core
    domain: "minimal"
    port: 8080
    nginx:
      upstream: "minimal:8080"
EOF

    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run nginx generation
    run generate_nginx_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create nginx file
    [ -f "${GENERATED_NGINX_DIR}/minimal.template" ]

    # Should contain default proxy configuration
    run grep "include /etc/nginx/conf.d/includes/proxy" "${GENERATED_NGINX_DIR}/minimal.template"
    [ "$status" -eq 0 ]

    run grep "proxy_pass http://minimal:8080" "${GENERATED_NGINX_DIR}/minimal.template"
    [ "$status" -eq 0 ]
}
