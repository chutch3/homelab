#!/usr/bin/env bats

# Tests for SSH-based Deployment Engine
# Part of Issue #37 - SSH-based Deployment Engine

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
    export BUNDLES_DIR="$TEST_OUTPUT"

    # Source the deployment script
    source "$PROJECT_ROOT/scripts/deploy_compose_bundles.sh"
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
  node-02:
    host: "192.168.1.12"
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

  actual:
    image: "actualbudget/actual-server:latest"
    port: 5006
    deploy: "node-01"
    enabled: true
EOF
}

# Helper function to mock SSH functions
mock_ssh_functions() {
    # Override SSH functions to simulate successful operations
    ssh_execute() {
        echo "Mock SSH execute: $1 -> $2"
        return 0
    }

    ssh_test_connection() {
        echo "Mock SSH test connection: $1"
        return 0
    }

    scp() {
        echo "Mock SCP: $*"
        return 0
    }

    export -f ssh_execute ssh_test_connection scp
}

@test "get_all_machines should return all machine names from config" {
    create_test_config

    run get_all_machines "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "driver" ]]
    [[ "$output" =~ "node-01" ]]
    [[ "$output" =~ "node-02" ]]
}

@test "get_machine_connection_info should return host and user for machine" {
    create_test_config

    run get_machine_connection_info "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ 192\.168\.1\.10 ]]
    [[ "$output" =~ "admin" ]]
}

@test "test_machine_connectivity should check SSH connection to machine" {
    create_test_config
    mock_ssh_functions

    run test_machine_connectivity "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Testing connectivity" ]]
}

@test "copy_bundle_to_machine should copy deployment files to remote machine" {
    create_test_config
    mock_ssh_functions

    # Create mock bundle directory
    mkdir -p "$TEST_OUTPUT/driver"
    echo "mock compose content" > "$TEST_OUTPUT/driver/docker-compose.yaml"
    mkdir -p "$TEST_OUTPUT/driver/nginx"
    echo "mock nginx config" > "$TEST_OUTPUT/driver/nginx/nginx.conf"

    run copy_bundle_to_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Copying bundle" ]]
}

@test "deploy_bundle_on_machine should execute deployment commands remotely" {
    create_test_config
    mock_ssh_functions

    run deploy_bundle_on_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Deploying bundle" ]]
}

@test "verify_deployment_on_machine should check if services are running" {
    create_test_config
    mock_ssh_functions

    run verify_deployment_on_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Verifying deployment" ]]
}

@test "deploy_to_single_machine should complete full deployment to one machine" {
    create_test_config
    mock_ssh_functions

    # Create mock bundle
    mkdir -p "$TEST_OUTPUT/driver"
    echo "mock compose" > "$TEST_OUTPUT/driver/docker-compose.yaml"

    run deploy_to_single_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ deployment.*driver ]]
}

@test "deploy_to_all_machines should deploy to every machine in config" {
    create_test_config
    mock_ssh_functions

    # Create mock bundles for all machines
    for machine in driver node-01 node-02; do
        mkdir -p "$TEST_OUTPUT/$machine"
        echo "mock compose for $machine" > "$TEST_OUTPUT/$machine/docker-compose.yaml"
    done

    run deploy_to_all_machines "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Deploying to all machines" ]]
    [[ "$output" =~ "driver" ]]
    [[ "$output" =~ "node-01" ]]
    [[ "$output" =~ "node-02" ]]
}

@test "check_deployment_status should report status across all machines" {
    create_test_config
    mock_ssh_functions

    run check_deployment_status "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "status" ]]
}

@test "deploy_with_dependencies should handle deployment order" {
    create_test_config
    mock_ssh_functions

    # Create mock bundles
    for machine in driver node-01 node-02; do
        mkdir -p "$TEST_OUTPUT/$machine"
        echo "mock compose for $machine" > "$TEST_OUTPUT/$machine/docker-compose.yaml"
    done

    run deploy_with_dependencies "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "dependencies" ]]
}

@test "rollback_deployment should undo deployment on machine" {
    create_test_config
    mock_ssh_functions

    run rollback_deployment "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
        [[ "$output" =~ Rolling\ back|Rollback\ completed ]]
}

@test "should handle SSH connection failures gracefully" {
    create_test_config

    # Override SSH to simulate failure
    ssh_test_connection() {
        return 1
    }
    export -f ssh_test_connection

    run test_machine_connectivity "driver" "$TEST_CONFIG"
    [ "$status" -eq 1 ]
    [[ "$output" =~ Failed|failed|error|cannot ]]
}

@test "should handle missing bundle files gracefully" {
    create_test_config
    mock_ssh_functions

    # Don't create bundle files
    run copy_bundle_to_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 1 ]
    [[ "$output" =~ not\ found|missing|error ]]
}

@test "should handle deployment failures gracefully" {
    create_test_config

    # Override SSH to simulate deployment failure
    ssh_execute() {
        if [[ "$2" =~ "docker compose up" ]]; then
            return 1
        fi
        return 0
    }
    export -f ssh_execute

    run deploy_bundle_on_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 1 ]
    [[ "$output" =~ Failed|failed|error ]]
}

@test "should validate homelab.yaml before deployment" {
    # Create invalid config
    echo "invalid yaml content" > "$TEST_CONFIG"

    run deploy_to_all_machines "$TEST_CONFIG"
    [ "$status" -eq 1 ]
    [[ "$output" =~ Invalid|invalid|Failed|failed|error ]]
}

@test "should generate bundles before deployment if missing" {
    create_test_config
    mock_ssh_functions

    # Don't create bundles directory
    run deploy_to_all_machines "$TEST_CONFIG"
    # Should pass because bundles get generated, even if deployment fails
    [[ "$output" =~ Generating\ bundles|translation|Generated\ files ]]
}

@test "should support dry-run mode without executing commands" {
    create_test_config
    mock_ssh_functions

    run deploy_to_all_machines "$TEST_CONFIG" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ dry.*run|would.*deploy ]]
}

@test "should support deploying to specific machines only" {
    create_test_config
    mock_ssh_functions

    mkdir -p "$TEST_OUTPUT/driver"
    echo "mock compose" > "$TEST_OUTPUT/driver/docker-compose.yaml"

    run deploy_to_specific_machines "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "driver" ]]
    [[ ! "$output" =~ "node-01" ]]
}

@test "should handle machine filtering and targeting" {
    create_test_config

    run filter_machines_by_role "manager" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    run filter_machines_by_labels "web" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
}

@test "should provide deployment progress reporting" {
    create_test_config
    mock_ssh_functions

    # Create mock bundles
    for machine in driver node-01 node-02; do
        mkdir -p "$TEST_OUTPUT/$machine"
        echo "mock compose" > "$TEST_OUTPUT/$machine/docker-compose.yaml"
    done

    run deploy_to_all_machines "$TEST_CONFIG" --progress
    [ "$status" -eq 0 ]
    [[ "$output" =~ progress|%|[0-9]/[0-9] ]]
}

@test "should collect and report deployment logs" {
    create_test_config
    mock_ssh_functions

    run collect_deployment_logs "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "logs" ]]
}
