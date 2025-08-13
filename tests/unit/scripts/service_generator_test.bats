#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper
    load "${BATS_TEST_DIRNAME}/../../helpers/bats-support/load.bash"
    load "${BATS_TEST_DIRNAME}/../../helpers/bats-assert/load.bash"
    load "${BATS_TEST_DIRNAME}/../../helpers/homelab_builder"

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export BASE_DOMAIN="test.local"
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export HOMELAB_CONFIG="${TEST_TEMP_DIR}/homelab.yaml"
    export ENABLED_SERVICES_FILE="${TEST_TEMP_DIR}/.enabled-services"

    # Create config directory structure
    mkdir -p "${TEST_TEMP_DIR}/config"
    mkdir -p "${TEST_TEMP_DIR}/config/services/reverseproxy/templates/conf.d/enabled"

    # Create test homelab.yaml with services
    create_homelab_with_services "$HOMELAB_CONFIG" "actual" "homepage"

    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT HOMELAB_CONFIG ENABLED_SERVICES_FILE
}


@test "service_generator_script_should_exist" {
    # Test that the service generator script exists
    [ -f "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh" ]
}

@test "generate_compose_should_create_docker_compose_yaml" {
    # Test that generate_compose creates a docker-compose.yaml file
    run generate_compose_from_services
    [ "$status" -eq 0 ]
    [ -f "$PROJECT_ROOT/generated-docker-compose.yaml" ]
}

@test "generate_compose_should_include_service_definition" {
    # Test that generated compose file includes the actual service
    generate_compose_from_services
    run cat "$PROJECT_ROOT/generated-docker-compose.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"actual:"* ]]
    [[ "$output" == *"image:"* ]]
}

@test "generate_nginx_should_create_template_files" {
    # Test that generate_nginx creates nginx template files
    run generate_nginx_from_services
    [ "$status" -eq 0 ]
    [ -f "$PROJECT_ROOT/generated-nginx/actual.template" ]
}

@test "generate_nginx_should_include_upstream_config" {
    # Test that generated nginx template includes upstream configuration
    generate_nginx_from_services
    run grep "proxy_pass http://actual:5006" "$PROJECT_ROOT/generated-nginx/actual.template"
    [ "$status" -eq 0 ]
}

@test "generate_domains_should_create_domains_file" {
    # Test that generate_domains creates .domains file from services.yaml
    run generate_domains_from_services
    [ "$status" -eq 0 ]
    [ -f "$PROJECT_ROOT/.domains" ]
}

@test "generate_all_should_create_complete_deployment" {
    # Test that generate_all creates all necessary files
    run generate_all_from_services
    [ "$status" -eq 0 ]
    [ -f "$PROJECT_ROOT/generated-docker-compose.yaml" ]
    [ -f "$PROJECT_ROOT/generated-nginx/actual.template" ]
    [ -f "$PROJECT_ROOT/.domains" ]
}


@test "enable_services_via_yaml should mark services as enabled in homelab.yaml" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # This function should exist (will implement)
    run enable_services_via_yaml "actual" "homepage"

    echo "output: $output"

    # Check exit status
    [ "$status" -eq 0 ]

    # Should update homelab.yaml with enabled: true
    run yq '.services.actual.enabled' "$HOMELAB_CONFIG"
    [ "$output" = "true" ]

    run yq '.services.homepage.enabled' "$HOMELAB_CONFIG"
    [ "$output" = "true" ]
}

@test "disable_services_via_yaml should mark services as disabled in homelab.yaml" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Enable services first
    enable_services_via_yaml "actual" "homepage"

    # Now disable one
    run disable_services_via_yaml "actual"

    # Check exit status
    [ "$status" -eq 0 ]

    # Should update homelab.yaml with enabled: false
    run yq '.services.actual.enabled' "${HOMELAB_CONFIG}"
    [ "$output" = "false" ]

    # Homepage should still be enabled
    run yq '.services.homepage.enabled' "${HOMELAB_CONFIG}"
    [ "$output" = "true" ]
}

@test "list_enabled_services_from_yaml should show only enabled services" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Enable some services
    enable_services_via_yaml "actual" "homepage"

    # List enabled services
    run list_enabled_services_from_yaml

    # Check exit status
    [ "$status" -eq 0 ]

    # Should contain enabled services
    [[ "$output" =~ "actual" ]]
    [[ "$output" =~ "homepage" ]]

    # Should not contain disabled services
    [[ ! "$output" =~ "cryptpad" ]]
}

@test "generate_enabled_services_from_yaml should create .enabled-services file for backward compatibility" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Enable some services in services.yaml
    enable_services_via_yaml "actual" "homepage"

    # Generate .enabled-services file
    run generate_enabled_services_from_yaml

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create .enabled-services file
    [ -f "${ENABLED_SERVICES_FILE}" ]

    # Should contain enabled services
    run grep "actual" "${ENABLED_SERVICES_FILE}"
    [ "$status" -eq 0 ]

    run grep "homepage" "${ENABLED_SERVICES_FILE}"
    [ "$status" -eq 0 ]

    # Should not contain disabled services
    run grep "cryptpad" "${ENABLED_SERVICES_FILE}"
    [ "$status" -ne 0 ]
}

@test "start_enabled_services_modern should only start services marked as enabled in services.yaml" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Enable some services
    enable_services_via_yaml "actual" "homepage"

    # Mock docker compose command
    docker() {
        echo "docker $*"
        return 0
    }
    export -f docker

    # Test the modern start function
    run start_enabled_services_modern

    # Check exit status
    [ "$status" -eq 0 ]

    # Should include enabled services in docker compose command
    [[ "$output" =~ "actual" ]]
    [[ "$output" =~ "homepage" ]]
}

@test "interactive_service_enablement should be a callable function" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Test the function exists (type check)
    run type interactive_service_enablement

    # Check exit status
    [ "$status" -eq 0 ]

    # Should be recognized as a function
    [[ "$output" =~ "function" ]]
}

@test "homelab.yaml should preserve enabled state across generation operations" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Enable some services
    enable_services_via_yaml "actual" "homepage"

    # Generate other files (should not affect enabled state)
    generate_compose_from_services
    generate_nginx_from_services
    generate_domains_from_services

    # Enabled state should still be preserved
    run yq '.services.actual.enabled' "${HOMELAB_CONFIG}"
    [ "$output" = "true" ]

    run yq '.services.homepage.enabled' "${HOMELAB_CONFIG}"
    [ "$output" = "true" ]

    run yq '.services.cryptpad.enabled' "${HOMELAB_CONFIG}"
    # Should be false or null (default disabled)
    [[ "$output" = "false" || "$output" = "null" ]]
}


@test "certificate configuration should be included in generated files" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Should create certificate configuration files
    [ -f "$TEST_TEMP_DIR/generated/certificates/acme-config.yaml" ]
    [ -f "$TEST_TEMP_DIR/generated/certificates/cert-init.sh" ]
}

@test "generated docker-compose should include certificate initialization" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Generated compose should include ACME service
    grep -q "acme:" "$TEST_TEMP_DIR/generated/deployments/docker-compose.yaml"
    grep -q "acme.sh" "$TEST_TEMP_DIR/generated/deployments/docker-compose.yaml"
}

@test "generated swarm stack should include certificate secrets" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Generated swarm should define certificate secrets
    grep -q "ssl_full.pem:" "$TEST_TEMP_DIR/generated/deployments/swarm-stack.yaml"
    grep -q "ssl_key.pem:" "$TEST_TEMP_DIR/generated/deployments/swarm-stack.yaml"
    grep -q "ssl_ca.pem:" "$TEST_TEMP_DIR/generated/deployments/swarm-stack.yaml"
    grep -q "ssl_dhparam.pem:" "$TEST_TEMP_DIR/generated/deployments/swarm-stack.yaml"
}

@test "certificate checker script should be generated" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Should generate certificate status checker
    [ -f "$TEST_TEMP_DIR/generated/certificates/check-certs.sh" ]
    [ -x "$TEST_TEMP_DIR/generated/certificates/check-certs.sh" ]
}

@test "deployment should auto-initialize certificates if missing" {
    # Test that certificate checking is integrated into selfhosted.sh

    # Check that the enhanced_deploy function in selfhosted.sh includes cert checking
    grep -q "Checking certificate status" "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
    grep -q "ensure_certs_exist" "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
}

@test "certificate configuration should use BASE_DOMAIN from env" {
    # Create generated directory structure
    run generate_all_to_generated_dir

    [ "$status" -eq 0 ]

    # Certificate files should reference the correct domain
    if [ -f "$TEST_TEMP_DIR/generated/certificates/cert-init.sh" ]; then
        grep -q "test.local" "$TEST_TEMP_DIR/generated/certificates/cert-init.sh"
        grep -q "\\*.test.local" "$TEST_TEMP_DIR/generated/certificates/cert-init.sh"
    fi
}

@test "certificate renewal script should be generated for automation" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Should generate renewal automation
    [ -f "$TEST_TEMP_DIR/generated/certificates/renew-certs.sh" ]
    [ -x "$TEST_TEMP_DIR/generated/certificates/renew-certs.sh" ]

    # Renewal script should include proper ACME commands
    if [ -f "$TEST_TEMP_DIR/generated/certificates/renew-certs.sh" ]; then
        grep -q "acme.sh --renew" "$TEST_TEMP_DIR/generated/certificates/renew-certs.sh"
    fi
}

@test "certificate status should be checkable without docker" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Should generate status checker that works without containers
    [ -f "$TEST_TEMP_DIR/generated/certificates/cert-status.sh" ]

    # Status script should check file existence and expiry
    if [ -f "$TEST_TEMP_DIR/generated/certificates/cert-status.sh" ]; then
        grep -q "openssl x509" "$TEST_TEMP_DIR/generated/certificates/cert-status.sh"
        grep -q "expiry" "$TEST_TEMP_DIR/generated/certificates/cert-status.sh" ||
        grep -q "expires" "$TEST_TEMP_DIR/generated/certificates/cert-status.sh"
    fi
}

@test "static docker-compose.yaml should be replaceable by generated version" {

    # Generate compose file
    run generate_compose_from_services

    # Check exit status
    assert_success

    # Should create generated compose file
    [ -f "${PROJECT_ROOT}/generated-docker-compose.yaml" ]

    # Should contain all services from homelab.yaml
    run grep "actual:" "${PROJECT_ROOT}/generated-docker-compose.yaml"
    [ "$status" -eq 0 ]

    run grep "homepage:" "${PROJECT_ROOT}/generated-docker-compose.yaml"
    [ "$status" -eq 0 ]


    # Should contain networks section
    run grep "networks:" "${PROJECT_ROOT}/generated-docker-compose.yaml"
    [ "$status" -eq 0 ]
}

@test "generate_swarm_stack_from_services should create deployments/swarm/stack.yaml" {
    # This function should exist (will implement)

    create_swarm_homelab_config "$HOMELAB_CONFIG"

    run generate_swarm_stack_from_services

    echo "output: $output"

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create swarm stack file
    [ -f "${PROJECT_ROOT}/generated-swarm-stack.yaml" ]

    # Should contain swarm-specific configuration
    run grep "deploy:" "${PROJECT_ROOT}/generated-swarm-stack.yaml"
    [ "$status" -eq 0 ]

    # Should contain overlay networks
    run grep "driver: overlay" "${PROJECT_ROOT}/generated-swarm-stack.yaml"
    [ "$status" -eq 0 ]
}

@test "swarm stack should include reverseproxy with correct volumes and secrets" {
    create_swarm_homelab_config "$HOMELAB_CONFIG"

    # Generate swarm stack
    run generate_swarm_stack_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should contain reverseproxy service
    run grep "reverseproxy:" "${PROJECT_ROOT}/generated-swarm-stack.yaml"
    [ "$status" -eq 0 ]

    # Should contain secrets section
    run grep "secrets:" "${PROJECT_ROOT}/generated-swarm-stack.yaml"
    [ "$status" -eq 0 ]

    run grep "ssl_full.pem:" "${PROJECT_ROOT}/generated-swarm-stack.yaml"
    [ "$status" -eq 0 ]

    # Should contain networks section
    run grep "networks:" "${PROJECT_ROOT}/generated-swarm-stack.yaml"
    [ "$status" -eq 0 ]
}

@test "generate_all_deployment_files should create both compose and swarm files" {
    # This function should be enhanced to include swarm generation
    run generate_all_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create both files
    [ -f "${PROJECT_ROOT}/generated-docker-compose.yaml" ]
    [ -f "${PROJECT_ROOT}/generated-swarm-stack.yaml" ]
}

@test "generated swarm stack should be valid docker swarm syntax" {
    # Generate swarm stack
    create_swarm_homelab_config "$HOMELAB_CONFIG"

    run generate_swarm_stack_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Debug: check file exists
    [ -f "${PROJECT_ROOT}/generated-swarm-stack.yaml" ]

    # Should be valid YAML (basic syntax check using python)
    run poetry run python -c "import yaml; yaml.safe_load(open('${PROJECT_ROOT}/generated-swarm-stack.yaml'))"
    if [ "$status" -ne 0 ]; then
        echo "YAML validation failed: $output"
        cat "${PROJECT_ROOT}/generated-swarm-stack.yaml"
    fi
    [ "$status" -eq 0 ]

    # Should contain version info in header comments
    run grep "Generated Docker Swarm stack" "${PROJECT_ROOT}/generated-swarm-stack.yaml"
    [ "$status" -eq 0 ]
}
