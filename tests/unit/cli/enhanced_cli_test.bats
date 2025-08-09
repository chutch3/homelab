#!/usr/bin/env bats

bats_require_minimum_version 1.5.0

setup() {
    # Load test helper functions
    load ../scripts/test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export BASE_DOMAIN="test.example.com"
    export AVAILABLE_DIR="${TEST_TEMP_DIR}/reverseproxy/templates/conf.d"
    export ENABLED_DIR="${TEST_TEMP_DIR}/reverseproxy/templates/conf.d/enabled"
    export SSL_DIR="${TEST_TEMP_DIR}/reverseproxy/ssl"
    export DOMAIN_FILE="${TEST_TEMP_DIR}/.domains"

    # Create necessary directory structure for the script
    mkdir -p "${PROJECT_ROOT}/config"
    mkdir -p "${AVAILABLE_DIR}"
    mkdir -p "${ENABLED_DIR}"
    mkdir -p "${SSL_DIR}"
    mkdir -p "${PROJECT_ROOT}/scripts"

    # Copy necessary script files to test directory
    cp -r "${BATS_TEST_DIRNAME}/../../../scripts/"* "${PROJECT_ROOT}/scripts/"

    # Create a test selfhosted.sh script in the test directory
    cp "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" "${PROJECT_ROOT}/selfhosted.sh"
    cat > "${PROJECT_ROOT}/config/services.yaml" <<EOF
version: "1.0"
categories:
  finance: "Finance & Budgeting"
  media: "Media Management"
services:
  actual:
    name: "Actual Budget"
    description: "Personal finance application"
    category: finance
    domain: "budget"
    port: 5006
    compose:
      image: "actualbudget/actual-server:latest"
      ports: ["5006:5006"]
    nginx:
      upstream: "actual:5006"
      additional_config: "location / { proxy_pass http://actual:5006; }"
  photoprism:
    name: "PhotoPrism"
    description: "Photo management"
    category: media
    domain: "photos"
    port: 2342
    compose:
      image: "photoprism/photoprism:latest"
      ports: ["2342:2342"]
    nginx:
      upstream: "photoprism:2342"
      additional_config: "location / { proxy_pass http://photoprism:2342; }"
EOF

    # Change to project directory for CLI tests
    cd "${PROJECT_ROOT}" || return
}

teardown() {
    # Clean up test directory (this removes all test files)
    temp_del "$TEST_TEMP_DIR"
}

@test "selfhosted_service_list_should_show_available_services" {
    # Test that './selfhosted service list' shows services from config
    cd "${PROJECT_ROOT}"
    run bash "${PROJECT_ROOT}/selfhosted.sh" service list
    [ "$status" -eq 0 ]
    [[ "$output" == *"actual"* ]]
    [[ "$output" == *"Actual Budget"* ]]
    [[ "$output" == *"photoprism"* ]]
    [[ "$output" == *"PhotoPrism"* ]]
}

@test "selfhosted_service_generate_should_create_deployment_files" {
    # Test that './selfhosted service generate' creates all deployment files
    cd "${PROJECT_ROOT}"
    run bash "${PROJECT_ROOT}/selfhosted.sh" service generate
    [ "$status" -eq 0 ]
    [ -f "${PROJECT_ROOT}/generated-docker-compose.yaml" ]
    [ -f "${PROJECT_ROOT}/.domains" ]
    [ -d "${PROJECT_ROOT}/generated-nginx" ]
}

@test "selfhosted_service_validate_should_check_config" {
    # Test that './selfhosted service validate' validates the services config
    cd "${PROJECT_ROOT}"
    run bash "${PROJECT_ROOT}/selfhosted.sh" service validate
    [ "$status" -eq 0 ]
    [[ "$output" == *"Services configuration is valid"* ]]
}

@test "selfhosted_service_info_should_show_service_details" {
    # Test that './selfhosted service info <service>' shows service details
    cd "${PROJECT_ROOT}"
    run bash "${PROJECT_ROOT}/selfhosted.sh" service info actual
    [ "$status" -eq 0 ]
    [[ "$output" == *"Actual Budget"* ]]
    [[ "$output" == *"finance"* ]]
    [[ "$output" == *"budget"* ]]
}

@test "selfhosted_service_help_should_show_service_commands" {
    # Test that './selfhosted service help' shows available service commands
    cd "${PROJECT_ROOT}"
    run bash "${PROJECT_ROOT}/selfhosted.sh" service help
    [ "$status" -eq 0 ]
    [[ "$output" == *"list"* ]]
    [[ "$output" == *"generate"* ]]
    [[ "$output" == *"validate"* ]]
    [[ "$output" == *"info"* ]]
}

@test "selfhosted_deploy_compose_should_use_generated_files" {
    # Test that './selfhosted deploy compose' attempts to call compose function
    cd "${PROJECT_ROOT}"
    # Expect either success (0) or command not found (127) - both are valid
    run -0 -127 bash "${PROJECT_ROOT}/selfhosted.sh" deploy compose up --dry-run
    # Should either generate files and run compose, or show that docker-compose is missing
    [[ "$output" == *"Starting services with Docker Compose"* ]] || [[ "$output" == *"docker-compose: command not found"* ]]
}

@test "selfhosted_help_should_show_improved_usage" {
    # Test that './selfhosted help' shows the new command structure
    cd "${PROJECT_ROOT}"
    run bash "${PROJECT_ROOT}/selfhosted.sh" help
    [ "$status" -eq 0 ]
    [[ "$output" == *"service"* ]]
    [[ "$output" == *"deploy"* ]]
    [[ "$output" == *"config"* ]]
}

@test "selfhosted_config_init_should_setup_environment" {
    # Test that './selfhosted config init' attempts to set up the environment
    cd "${PROJECT_ROOT}"
    run bash "${PROJECT_ROOT}/selfhosted.sh" config init
    # May exit with 1 if .env needs editing, but should show initialization message
    [[ "$output" == *"Initializing selfhosted environment"* ]]
}

@test "selfhosted_unknown_command_should_show_helpful_error" {
    # Test that unknown commands show helpful error messages
    cd "${PROJECT_ROOT}"
    run bash "${PROJECT_ROOT}/selfhosted.sh" unknown-command
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown command"* ]]
    [[ "$output" == *"Available commands:"* ]]
    [[ "$output" == *"service"* ]]
    [[ "$output" == *"deploy"* ]]
}
