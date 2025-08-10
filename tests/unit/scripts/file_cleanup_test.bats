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
    export GENERATED_NGINX_DIR="${TEST_TEMP_DIR}/generated-nginx"

    # Create config directory structure
    mkdir -p "${TEST_TEMP_DIR}/config"
    mkdir -p "${TEST_TEMP_DIR}/config/services/reverseproxy/templates/conf.d"

    # Copy the real services.yaml for testing
    cp "${BATS_TEST_DIRNAME}/../../../config/services.yaml" "${SERVICES_CONFIG}"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT SERVICES_CONFIG GENERATED_NGINX_DIR
}

@test "services defined in services.yaml should not need static templates" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run nginx generation
    run generate_nginx_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Services in services.yaml should generate templates automatically
    [ -f "${GENERATED_NGINX_DIR}/actual.template" ]
    [ -f "${GENERATED_NGINX_DIR}/homepage.template" ]
    [ -f "${GENERATED_NGINX_DIR}/homeassistant.template" ]
    [ -f "${GENERATED_NGINX_DIR}/photoprism.template" ]
    [ -f "${GENERATED_NGINX_DIR}/portainer_agent.template" ]

    # These should have proper content
    run grep "proxy_pass http://actual_server:5006" "${GENERATED_NGINX_DIR}/actual.template"
    [ "$status" -eq 0 ]

    run grep "proxy_pass http://homepage:3000" "${GENERATED_NGINX_DIR}/homepage.template"
    [ "$status" -eq 0 ]
}

@test "cryptpad should not generate template if it uses external template_file" {
    # Add template_file reference to cryptpad service
    local temp_services="${TEST_TEMP_DIR}/services_with_template_ref.yaml"

    # Modify the services.yaml to add template_file reference for cryptpad
    sed '/cryptpad:/,/nginx:/{
        /nginx:/a\
      template_file: "cryptpad.template"
    }' "${SERVICES_CONFIG}" > "${temp_services}"

    export SERVICES_CONFIG="${temp_services}"

    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run nginx generation
    run generate_nginx_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # CryptPad should NOT generate a template if it references external file
    [ ! -f "${GENERATED_NGINX_DIR}/cryptpad.template" ]
}

@test "build_domain.sh functionality should be replaced by generate_domains_from_services" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Generate domains using new system
    run generate_domains_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create .domains file
    [ -f "${PROJECT_ROOT}/.domains" ]

    # Should contain same domains that build_domain.sh would create
    run grep "DOMAIN_ACTUAL=budget.test.local" "${PROJECT_ROOT}/.domains"
    [ "$status" -eq 0 ]

    run grep "DOMAIN_HOMEPAGE=dashboard.test.local" "${PROJECT_ROOT}/.domains"
    [ "$status" -eq 0 ]

    run grep "DOMAIN_CRYPTPAD=docs.test.local" "${PROJECT_ROOT}/.domains"
    [ "$status" -eq 0 ]
}
