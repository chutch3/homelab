#!/usr/bin/env bats

# Tests for Docker Compose Translation Engine
# Part of Issue #35 - Docker Compose Translation Engine

load test_helper

setup() {
    # Set PROJECT_ROOT relative to test location
    local project_root_path
    project_root_path="$(cd "$(dirname "$BATS_TEST_FILENAME")/../../.." && pwd)"
    export PROJECT_ROOT="$project_root_path"

    # Create temporary directories for testing
    local test_dir
    test_dir=$(mktemp -d)
    export TEST_DIR="$test_dir"
    export TEST_CONFIG="$TEST_DIR/homelab.yaml"
    export TEST_OUTPUT="$TEST_DIR/output"
    export HOMELAB_CONFIG="$TEST_CONFIG"
    export OUTPUT_DIR="$TEST_OUTPUT"

    # Source the translation script
    source "$PROJECT_ROOT/scripts/translate_homelab_to_compose.sh"
}

teardown() {
    # Clean up temporary directories
    rm -rf "$TEST_DIR"
}

# Helper function to create a basic test homelab.yaml
create_test_config() {
    cat > "$TEST_CONFIG" <<EOF
version: "2.0"
deployment: docker_compose

machines:
  driver:
    host: "192.168.1.10"
    user: "admin"
  node-01:
    host: "192.168.1.11"
    user: "admin"

services:
  homepage:
    image: "ghcr.io/gethomepage/homepage:latest"
    port: 3000
    deploy: "driver"
    enabled: true

  jellyfin:
    image: "jellyfin/jellyfin:latest"
    port: 8096
    storage: true
    deploy: "all"
    enabled: true

  nginx:
    image: "nginx:alpine"
    port: 80
    deploy: "all"
    enabled: true
EOF
}

# Helper function to create invalid config
create_invalid_config() {
    cat > "$TEST_CONFIG" <<EOF
version: "2.0"
deployment: docker_swarm

machines:
  driver:
    host: "192.168.1.10"
    user: "admin"

services:
  test:
    image: "test:latest"
    port: 3000
EOF
}

@test "validate_homelab_config should succeed with valid docker_compose config" {
    create_test_config

    run validate_homelab_config_compose
    [ "$status" -eq 0 ]
    [[ "$output" =~ homelab.yaml\ validation\ passed ]]
}

@test "validate_homelab_config should fail when file does not exist" {
    # Don't create config file

    run validate_homelab_config_compose
    [ "$status" -eq 1 ]
    [[ "$output" =~ homelab.yaml\ not\ found ]]
}

@test "validate_homelab_config should fail with wrong deployment type" {
    create_invalid_config

    run validate_homelab_config_compose
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Invalid deployment type: 'docker_swarm'" ]]
}

@test "get_machine_list should return all machine names" {
    create_test_config

    run get_machine_list
    [ "$status" -eq 0 ]
    [[ "$output" =~ "driver" ]]
    [[ "$output" =~ "node-01" ]]
}

@test "get_services_for_machine should return correct services for driver" {
    create_test_config

    run get_services_for_machine "driver"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "homepage" ]]
    [[ "$output" =~ "jellyfin" ]]
    [[ "$output" =~ "nginx" ]]
}

@test "get_services_for_machine should return only 'all' services for node-01" {
    create_test_config

    run get_services_for_machine "node-01"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "jellyfin" ]]
    [[ "$output" =~ "nginx" ]]
    [[ ! "$output" =~ "homepage" ]]
}

@test "get_services_for_machine should handle disabled services" {
    create_test_config
    # Disable jellyfin
    yq '.services.jellyfin.enabled = false' "$TEST_CONFIG" > "${TEST_CONFIG}.tmp" && mv "${TEST_CONFIG}.tmp" "$TEST_CONFIG"

    run get_services_for_machine "driver"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "homepage" ]]
    [[ "$output" =~ "nginx" ]]
    [[ ! "$output" =~ "jellyfin" ]]
}

@test "generate_docker_compose_for_machine should create compose file" {
    create_test_config

    # Test the function directly - if it creates the file, it works
    generate_docker_compose_for_machine "driver"
    [ -f "$TEST_OUTPUT/driver/docker-compose.yaml" ]
}

@test "generated docker-compose.yaml should contain nginx-proxy service" {
    create_test_config
    generate_docker_compose_for_machine "driver"

    run grep -q "nginx-proxy:" "$TEST_OUTPUT/driver/docker-compose.yaml"
    [ "$status" -eq 0 ]
}

@test "generated docker-compose.yaml should contain correct services" {
    create_test_config
    generate_docker_compose_for_machine "driver"

    local compose_file="$TEST_OUTPUT/driver/docker-compose.yaml"

    # Should contain homepage and jellyfin (but not nginx as separate service)
    run grep -q "homepage:" "$compose_file"
    [ "$status" -eq 0 ]

    run grep -q "jellyfin:" "$compose_file"
    [ "$status" -eq 0 ]

    # Should not contain nginx as separate service (only nginx-proxy)
    run grep -c "  nginx:" "$compose_file"
    [ "$status" -eq 1 ]
}

@test "generated docker-compose.yaml should have correct image references" {
    create_test_config
    generate_docker_compose_for_machine "driver"

    local compose_file="$TEST_OUTPUT/driver/docker-compose.yaml"

    run grep -q "image: ghcr.io/gethomepage/homepage:latest" "$compose_file"
    [ "$status" -eq 0 ]

    run grep -q "image: jellyfin/jellyfin:latest" "$compose_file"
    [ "$status" -eq 0 ]
}

@test "generated docker-compose.yaml should include volumes for services with storage" {
    create_test_config
    generate_docker_compose_for_machine "driver"

    local compose_file="$TEST_OUTPUT/driver/docker-compose.yaml"

    # Should have volumes section
    run grep -q "volumes:" "$compose_file"
    [ "$status" -eq 0 ]

    # Should have jellyfin_data volume
    run grep -q "jellyfin_data:" "$compose_file"
    [ "$status" -eq 0 ]
}

@test "generate_nginx_config_for_machine should create nginx directory" {
    create_test_config

    run generate_nginx_config_for_machine "driver"
    [ "$status" -eq 0 ]
    [ -d "$TEST_OUTPUT/driver/nginx" ]
    [ -f "$TEST_OUTPUT/driver/nginx/nginx.conf" ]
}

@test "generate_deployment_script_for_machine should create executable script" {
    create_test_config

    run generate_deployment_script_for_machine "driver"
    [ "$status" -eq 0 ]
    [ -f "$TEST_OUTPUT/driver/deploy.sh" ]
    [ -x "$TEST_OUTPUT/driver/deploy.sh" ]
}

@test "deployment script should contain correct machine information" {
    create_test_config
    generate_deployment_script_for_machine "driver"

    local deploy_script="$TEST_OUTPUT/driver/deploy.sh"

    run grep -q 'MACHINE_HOST="192.168.1.10"' "$deploy_script"
    [ "$status" -eq 0 ]

    run grep -q 'MACHINE_USER="admin"' "$deploy_script"
    [ "$status" -eq 0 ]
}

@test "translate_homelab_to_compose should process all machines" {
    create_test_config

    # Test the function directly - check for expected outputs
    translate_homelab_to_compose

    # Should create directories for all machines
    [ -d "$TEST_OUTPUT/driver" ]
    [ -d "$TEST_OUTPUT/node-01" ]

    # Should create master deployment script
    [ -f "$TEST_OUTPUT/deploy-all.sh" ]
    [ -x "$TEST_OUTPUT/deploy-all.sh" ]
}

@test "master deployment script should reference all machines" {
    create_test_config
    translate_homelab_to_compose

    local master_script="$TEST_OUTPUT/deploy-all.sh"

    run grep -q "driver/deploy.sh" "$master_script"
    [ "$status" -eq 0 ]

    run grep -q "node-01/deploy.sh" "$master_script"
    [ "$status" -eq 0 ]
}

@test "should handle machine with no services gracefully" {
    create_test_config
    # Remove all services for node-01 by setting all to driver only
    yq '.services.jellyfin.deploy = "driver"' "$TEST_CONFIG" > "${TEST_CONFIG}.tmp" && mv "${TEST_CONFIG}.tmp" "$TEST_CONFIG"
    yq '.services.nginx.deploy = "driver"' "$TEST_CONFIG" > "${TEST_CONFIG}.tmp" && mv "${TEST_CONFIG}.tmp" "$TEST_CONFIG"

    # Test the function directly - it should handle gracefully by not creating files for machines with no services
    generate_docker_compose_for_machine "node-01"
}

@test "should handle missing machines gracefully" {
    create_test_config

    run get_services_for_machine "nonexistent"
    [ "$status" -eq 0 ]
    # Should not contain any actual service names
    [[ ! "$output" =~ "actual" ]]
    [[ ! "$output" =~ "homepage" ]]
    [[ ! "$output" =~ "homeassistant" ]]
}

@test "deployment strategies should work correctly" {
    create_test_config

    # Add service with 'any' strategy
    yq '.services.test_any = {"image": "test:latest", "port": 9000, "deploy": "any", "enabled": true}' "$TEST_CONFIG" > "${TEST_CONFIG}.tmp" && mv "${TEST_CONFIG}.tmp" "$TEST_CONFIG"

    # Add service with 'random' strategy
    yq '.services.test_random = {"image": "test2:latest", "port": 9001, "deploy": "random", "enabled": true}' "$TEST_CONFIG" > "${TEST_CONFIG}.tmp" && mv "${TEST_CONFIG}.tmp" "$TEST_CONFIG"

    # 'any' and 'random' should deploy to first machine (driver)
    run get_services_for_machine "driver"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "test_any" ]]
    [[ "$output" =~ "test_random" ]]

    # Should not deploy to other machines
    run get_services_for_machine "node-01"
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "test_any" ]]
    [[ ! "$output" =~ "test_random" ]]
}
