#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load ../scripts/test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export PROJECT_ROOT="/home/cody/workspace/homelab"
    export BASE_DOMAIN="test.example.com"

    # Create mock services config for testing (backup existing if needed)
    if [ -f "/home/cody/workspace/homelab/config/services.yaml" ]; then
        cp "/home/cody/workspace/homelab/config/services.yaml" "$TEST_TEMP_DIR/services.yaml.backup"
    fi

    mkdir -p "/home/cody/workspace/homelab/config"
    cat > "/home/cody/workspace/homelab/config/services.yaml" <<EOF
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
    cd "/home/cody/workspace/homelab" || return
}

teardown() {
    # Restore original services.yaml if it existed
    if [ -f "$TEST_TEMP_DIR/services.yaml.backup" ]; then
        cp "$TEST_TEMP_DIR/services.yaml.backup" "/home/cody/workspace/homelab/config/services.yaml"
    fi

    # Clean up generated test files
    rm -f "/home/cody/workspace/homelab/generated-docker-compose.yaml"
    rm -rf "/home/cody/workspace/homelab/generated-nginx"

    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "selfhosted_service_list_should_show_available_services" {
    # Test that './selfhosted service list' shows services from config
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service list
    [ "$status" -eq 0 ]
    [[ "$output" == *"actual"* ]]
    [[ "$output" == *"Actual Budget"* ]]
    [[ "$output" == *"photoprism"* ]]
    [[ "$output" == *"PhotoPrism"* ]]
}

@test "selfhosted_service_generate_should_create_deployment_files" {
    # Test that './selfhosted service generate' creates all deployment files
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service generate
    [ "$status" -eq 0 ]
    [ -f "/home/cody/workspace/homelab/generated-docker-compose.yaml" ]
    [ -f "/home/cody/workspace/homelab/.domains" ]
    [ -d "/home/cody/workspace/homelab/generated-nginx" ]
}

@test "selfhosted_service_validate_should_check_config" {
    # Test that './selfhosted service validate' validates the services config
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service validate
    [ "$status" -eq 0 ]
    [[ "$output" == *"Services configuration is valid"* ]]
}

@test "selfhosted_service_info_should_show_service_details" {
    # Test that './selfhosted service info <service>' shows service details
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service info actual
    [ "$status" -eq 0 ]
    [[ "$output" == *"Actual Budget"* ]]
    [[ "$output" == *"finance"* ]]
    [[ "$output" == *"budget"* ]]
}

@test "selfhosted_service_help_should_show_service_commands" {
    # Test that './selfhosted service help' shows available service commands
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" service help
    [ "$status" -eq 0 ]
    [[ "$output" == *"list"* ]]
    [[ "$output" == *"generate"* ]]
    [[ "$output" == *"validate"* ]]
    [[ "$output" == *"info"* ]]
}

@test "selfhosted_deploy_compose_should_use_generated_files" {
    # Test that './selfhosted deploy compose' attempts to call compose function
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" deploy compose up --dry-run
    # Should either generate files and run compose, or show that docker-compose is missing
    [[ "$output" == *"Starting services with Docker Compose"* ]] || [[ "$output" == *"docker-compose: command not found"* ]]
}

@test "selfhosted_help_should_show_improved_usage" {
    # Test that './selfhosted help' shows the new command structure
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" help
    [ "$status" -eq 0 ]
    [[ "$output" == *"service"* ]]
    [[ "$output" == *"deploy"* ]]
    [[ "$output" == *"config"* ]]
}

@test "selfhosted_config_init_should_setup_environment" {
    # Test that './selfhosted config init' attempts to set up the environment
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" config init
    # May exit with 1 if .env needs editing, but should show initialization message
    [[ "$output" == *"Initializing selfhosted environment"* ]]
}

@test "selfhosted_unknown_command_should_show_helpful_error" {
    # Test that unknown commands show helpful error messages
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" unknown-command
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown command"* ]]
    [[ "$output" == *"Available commands:"* ]]
    [[ "$output" == *"service"* ]]
    [[ "$output" == *"deploy"* ]]
}
