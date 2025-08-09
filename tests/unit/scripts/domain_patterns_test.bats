#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load ../scripts/test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export PROJECT_ROOT="$TEST_TEMP_DIR"
    export BASE_DOMAIN="example.com"

    # Create test services config with various domain patterns
    mkdir -p "$TEST_TEMP_DIR/config"
    cat > "$TEST_TEMP_DIR/config/services.yaml" <<EOF
version: "1.0"
categories:
  finance: "Finance & Budgeting"
  core: "Core Infrastructure"
services:
  actual:
    name: "Actual Budget"
    description: "Personal finance application"
    category: finance
    domain: "budget"
    compose:
      image: "actualbudget/actual-server:latest"
      ports: ["5006:5006"]
    nginx:
      upstream: "actual:5006"
  dashboard:
    name: "Homepage Dashboard"
    description: "Central dashboard"
    category: core
    domain: "home"
    compose:
      image: "ghcr.io/gethomepage/homepage:latest"
      ports: ["3000:3000"]
    nginx:
      upstream: "dashboard:3000"
  multi-word-service:
    name: "Multi Word Service"
    description: "Service with dashes in name"
    category: core
    domain: "multi-word"
    compose:
      image: "nginx:alpine"
      ports: ["8080:80"]
    nginx:
      upstream: "multi-word-service:8080"
EOF

    # Change to test directory
    cd "$TEST_TEMP_DIR" || return

    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "generate_domains_should_create_consistent_variable_names" {
    # Test that domain variables follow consistent naming patterns
    generate_domains_from_services

    # Check that variables are properly formatted
    run grep "DOMAIN_ACTUAL=budget.example.com" "$PROJECT_ROOT/.domains"
    [ "$status" -eq 0 ]

    run grep "DOMAIN_DASHBOARD=home.example.com" "$PROJECT_ROOT/.domains"
    [ "$status" -eq 0 ]

    run grep "DOMAIN_MULTI_WORD_SERVICE=multi-word.example.com" "$PROJECT_ROOT/.domains"
    [ "$status" -eq 0 ]
}

@test "validate_domain_patterns_should_check_naming_conventions" {
    # Test domain pattern validation
    run validate_domain_patterns
    [ "$status" -eq 0 ]
    [[ "$output" == *"Domain patterns are valid"* ]]
}

@test "normalize_service_name_should_handle_special_characters" {
    # Test service name normalization for environment variables
    run normalize_service_name_for_env "multi-word-service"
    [ "$status" -eq 0 ]
    [[ "$output" == "MULTI_WORD_SERVICE" ]]

    run normalize_service_name_for_env "actual"
    [ "$status" -eq 0 ]
    [[ "$output" == "ACTUAL" ]]

    run normalize_service_name_for_env "some_complex-service.name"
    [ "$status" -eq 0 ]
    [[ "$output" == "SOME_COMPLEX_SERVICE_NAME" ]]
}

@test "generate_nginx_should_use_consistent_server_names" {
    # Test that nginx templates use consistent server name patterns
    generate_nginx_from_services

        # Check actual service nginx template
    run grep "server_name \${DOMAIN_ACTUAL}" "$PROJECT_ROOT/generated-nginx/actual.template"
    [ "$status" -eq 0 ]

    # Check dashboard service nginx template
    run grep "server_name \${DOMAIN_DASHBOARD}" "$PROJECT_ROOT/generated-nginx/dashboard.template"
    [ "$status" -eq 0 ]

    # Check multi-word service nginx template
    run grep "server_name \${DOMAIN_MULTI_WORD_SERVICE}" "$PROJECT_ROOT/generated-nginx/multi-word-service.template"
    [ "$status" -eq 0 ]
}

@test "suggest_domain_name_should_provide_recommendations" {
    # Test domain name suggestion functionality
    run suggest_domain_name "Actual Budget Application"
    [ "$status" -eq 0 ]
    [[ "$output" == *"budget"* ]]

    run suggest_domain_name "Home Assistant"
    [ "$status" -eq 0 ]
    [[ "$output" == *"home"* ]]

    run suggest_domain_name "Photo Management Service"
    [ "$status" -eq 0 ]
    [[ "$output" == *"photo"* ]]
}

@test "validate_domain_uniqueness_should_detect_conflicts" {
    # Test domain uniqueness validation
    cat > "$TEST_TEMP_DIR/config/conflicting-services.yaml" <<EOF
version: "1.0"
services:
  service1:
    name: "Service One"
    domain: "app"
    compose:
      image: "nginx:alpine"
    nginx:
      upstream: "service1:80"
  service2:
    name: "Service Two"
    domain: "app"
    compose:
      image: "nginx:alpine"
    nginx:
      upstream: "service2:80"
EOF

    export SERVICES_CONFIG="$TEST_TEMP_DIR/config/conflicting-services.yaml"
    run validate_domain_uniqueness
    [ "$status" -eq 1 ]
    [[ "$output" == *"Duplicate domain"* ]]
    [[ "$output" == *"app"* ]]
}

@test "generate_domain_mapping_should_create_reference_file" {
    # Test that domain mapping creates a human-readable reference
    run generate_domain_mapping
    [ "$status" -eq 0 ]
    [ -f "$PROJECT_ROOT/DOMAINS.md" ]

    # Check that it contains service mappings from our test config
    run grep "Actual Budget.*budget.*budget.example.com" "$PROJECT_ROOT/DOMAINS.md"
    [ "$status" -eq 0 ]

    # Check for environment variables section
    run grep "DOMAIN_ACTUAL=budget.example.com" "$PROJECT_ROOT/DOMAINS.md"
    [ "$status" -eq 0 ]

    # Check for multi-word service handling
    run grep "DOMAIN_MULTI_WORD_SERVICE" "$PROJECT_ROOT/DOMAINS.md"
    [ "$status" -eq 0 ]
}
