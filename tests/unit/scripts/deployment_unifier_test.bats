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
    export HOMELAB_CONFIG="$TEST_TEMP_DIR/homelab.yaml"

    # Create test services config with deployment-specific configurations
    mkdir -p "$TEST_TEMP_DIR/config"
    cat > "$HOMELAB_CONFIG" <<EOF
version: "1.0"
categories:
  database: "Database Services"
  finance: "Finance & Budgeting"

services:
  mariadb:
    name: "MariaDB"
    description: "Database server"
    category: database
    domain: "db"
    port: 3306
    volumes:
      - name: "data"
        description: "Database files"
        type: "application_data"
        backup_priority: "high"
    # Shared container configuration
    container:
      image: "mariadb:latest"
      environment:
        MYSQL_ROOT_PASSWORD: "\${MYSQL_ROOT_PASSWORD:-changeme}"
        MYSQL_DATABASE: "appdb"
      resources:
        cpu_request: "0.5"
        cpu_limit: "1.0"
        memory_request: "512Mi"
        memory_limit: "1Gi"
    # Docker Compose specific
    compose:
      restart: unless-stopped
      networks:
        - database
    # Docker Swarm specific
    swarm:
      deploy:
        mode: replicated
        replicas: 1
        placement:
          constraints:
            - node.role == manager
        resources:
          reservations:
            cpus: "0.5"
            memory: 512M
          limits:
            cpus: "1.0"
            memory: 1G
    # Kubernetes specific
    kubernetes:
      deployment:
        replicas: 1
        strategy:
          type: RollingUpdate
      service:
        type: ClusterIP
      persistentVolumeClaim:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 10Gi

  actual:
    name: "Actual Budget"
    description: "Personal finance application"
    category: finance
    domain: "budget"
    port: 5006
    depends_on:
      - mariadb
    volumes:
      - name: "data"
        description: "Application data"
        type: "application_data"
        backup_priority: "high"
    # Shared container configuration
    container:
      image: "actualbudget/actual-server:latest"
      environment:
        DATABASE_URL: "mysql://root:\${MYSQL_ROOT_PASSWORD:-changeme}@mariadb:3306/appdb"
      resources:
        cpu_request: "0.1"
        cpu_limit: "0.5"
        memory_request: "128Mi"
        memory_limit: "512Mi"
    # Docker Compose specific
    compose:
      restart: unless-stopped
      networks:
        - database
        - reverseproxy
    # Docker Swarm specific
    swarm:
      deploy:
        mode: replicated
        replicas: 1
        resources:
          reservations:
            cpus: "0.1"
            memory: 128M
          limits:
            cpus: "0.5"
            memory: 512M
    # Kubernetes specific
    kubernetes:
      deployment:
        replicas: 2
        strategy:
          type: RollingUpdate
          rollingUpdate:
            maxUnavailable: 1
            maxSurge: 1
      service:
        type: ClusterIP
      ingress:
        enabled: true
        className: nginx
EOF

    # Source the deployment unifier script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/deployment_unifier.sh"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST PROJECT_ROOT BASE_DOMAIN HOMELAB_CONFIG
}

@test "deployment_unifier_script_should_exist" {
    # Test that the deployment unifier script exists
    [ -f "${BATS_TEST_DIRNAME}/../../../scripts/deployment_unifier.sh" ]
}

@test "extract_shared_container_config_should_get_common_settings" {
    # Test extracting shared container configuration
    run extract_shared_container_config "mariadb"
    [ "$status" -eq 0 ]
    [[ "$output" == *"mariadb:latest"* ]]
    [[ "$output" == *"MYSQL_ROOT_PASSWORD"* ]]
}

@test "generate_unified_compose_should_merge_shared_and_specific_config" {
    # Skip this test - legacy deployment unifier superseded by unified homelab.yaml configuration (Issue #40)
    skip "Legacy deployment unifier superseded by unified configuration in Issue #40"
}

@test "generate_unified_swarm_should_merge_shared_and_swarm_config" {
    # Skip this test - legacy deployment unifier superseded by unified homelab.yaml configuration (Issue #40)
    skip "Legacy deployment unifier superseded by unified configuration in Issue #40"
}

@test "generate_unified_kubernetes_should_create_k8s_manifests" {
    # Skip this test - legacy deployment unifier superseded by unified homelab.yaml configuration (Issue #40)
    skip "Legacy deployment unifier superseded by unified configuration in Issue #40"
}

@test "validate_resource_specifications_should_check_consistency" {
    # Test validating resource specifications across platforms
    run validate_resource_specifications
    [ "$status" -eq 0 ]
    [[ "$output" == *"Resource specifications are consistent"* ]]
}

@test "convert_resources_to_compose_should_transform_resource_format" {
    # Test converting unified resource specs to Docker Compose format
    run convert_resources_to_compose "mariadb"
    [ "$status" -eq 0 ]
    [[ "$output" == *"cpus:"* ]]
    [[ "$output" == *"memory:"* ]]
}

@test "convert_resources_to_swarm_should_transform_to_swarm_format" {
    # Test converting unified resource specs to Docker Swarm format
    run convert_resources_to_swarm "mariadb"
    [ "$status" -eq 0 ]
    [[ "$output" == *"reservations:"* ]]
    [[ "$output" == *"limits:"* ]]
}

@test "convert_resources_to_kubernetes_should_create_k8s_resources" {
    # Test converting unified resource specs to Kubernetes format
    run convert_resources_to_kubernetes "mariadb"
    [ "$status" -eq 0 ]
    [[ "$output" == *"requests:"* ]]
    [[ "$output" == *"limits:"* ]]
}

@test "generate_platform_comparison_should_show_differences" {
    # Test generating platform comparison report
    run generate_platform_comparison
    [ "$status" -eq 0 ]
    [ -f "$PROJECT_ROOT/platform-comparison.md" ]

    # Check comparison includes all platforms
    run grep "Docker Compose" "$PROJECT_ROOT/platform-comparison.md"
    [ "$status" -eq 0 ]

    run grep "Docker Swarm" "$PROJECT_ROOT/platform-comparison.md"
    [ "$status" -eq 0 ]

    run grep "Kubernetes" "$PROJECT_ROOT/platform-comparison.md"
    [ "$status" -eq 0 ]
}

@test "migrate_between_platforms_should_preserve_configuration" {
    # Test migration between deployment platforms
    export SOURCE_PLATFORM="compose"
    export TARGET_PLATFORM="swarm"

    run migrate_between_platforms
    [ "$status" -eq 0 ]
    [[ "$output" == *"Migration from compose to swarm completed"* ]]
}

@test "validate_platform_compatibility_should_check_feature_support" {
    # Test validating platform compatibility for service features
    run validate_platform_compatibility "mariadb" "kubernetes"
    [ "$status" -eq 0 ]
    [[ "$output" == *"compatible with kubernetes"* ]]
}

@test "generate_deployment_matrix_should_create_all_formats" {
    # Skip this test - legacy deployment unifier superseded by unified homelab.yaml configuration (Issue #40)
    skip "Legacy deployment matrix superseded by unified configuration in Issue #40"
}
