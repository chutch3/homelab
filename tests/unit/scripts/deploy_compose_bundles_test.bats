#!/usr/bin/env bats

# Tests for SSH-based Deployment Engine
# Part of Issue #37 - SSH-based Deployment Engine

load test_helper

setup() {
    # Set PROJECT_ROOT relative to test location
    local project_root_path
    project_root_path="$(cd "$(dirname "$BATS_TEST_FILENAME")/../../.." && pwd)"
    export PROJECT_ROOT="$project_root_path"

    load "${BATS_TEST_DIRNAME}/../../helpers/bats-support/load.bash"
    load "${BATS_TEST_DIRNAME}/../../helpers/bats-assert/load.bash"
    load "${BATS_TEST_DIRNAME}/../../helpers/homelab_builder"

    # Create temporary directories for testing
    TEST_TEMP_DIR="$(temp_make)"

    export TEST=true
    export PROJECT_ROOT="$TEST_TEMP_DIR"
    export HOMELAB_CONFIG="$TEST_TEMP_DIR/homelab.yaml"
    export BUNDLES_DIR="$TEST_TEMP_DIR/bundles"

    mkdir -p "$BUNDLES_DIR"

    # Source the deployment script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/deploy_compose_bundles.sh"

    create_multi_machine_homelab_config "$HOMELAB_CONFIG"
}

teardown() {
    # Clean up temporary directories
    rm -rf "$TEST_TEMP_DIR"
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


    run get_all_machines "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "driver" ]]
    [[ "$output" =~ "node-01" ]]
    [[ "$output" =~ "node-02" ]]
}

@test "get_machine_connection_info should return host and user for machine" {


    run get_machine_connection_info "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    assert_output --partial "192.168.1.10"
    assert_output --partial "testuser"
}

@test "test_machine_connectivity should check SSH connection to machine" {

    mock_ssh_functions

    run test_machine_connectivity "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Testing connectivity" ]]
}

@test "copy_bundle_to_machine should copy deployment files to remote machine" {

    mock_ssh_functions

    # Create mock bundle directory
    mkdir -p "$BUNDLES_DIR/driver"
    echo "mock compose content" > "$BUNDLES_DIR/driver/docker-compose.yaml"
    mkdir -p "$BUNDLES_DIR/driver/nginx"
    echo "mock nginx config" > "$BUNDLES_DIR/driver/nginx/nginx.conf"

    run copy_bundle_to_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Copying bundle" ]]
}

@test "deploy_bundle_on_machine should execute deployment commands remotely" {

    mock_ssh_functions

    run deploy_bundle_on_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Deploying bundle" ]]
}

@test "verify_deployment_on_machine should check if services are running" {

    mock_ssh_functions

    run verify_deployment_on_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Verifying deployment" ]]
}

@test "deploy_to_single_machine should complete full deployment to one machine" {

    mock_ssh_functions

    # Create mock bundle
    mkdir -p "$BUNDLES_DIR/driver"
    echo "mock compose" > "$BUNDLES_DIR/driver/docker-compose.yaml"

    run deploy_to_single_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ deployment.*driver ]]
}

@test "deploy_to_all_machines should deploy to every machine in config" {

    mock_ssh_functions

    # Create mock bundles for all machines
    for machine in driver node-01 node-02; do
        mkdir -p "$BUNDLES_DIR/$machine"
        echo "mock compose for $machine" > "$BUNDLES_DIR/$machine/docker-compose.yaml"
    done

    run deploy_to_all_machines "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Deploying to all machines" ]]
    [[ "$output" =~ "driver" ]]
    [[ "$output" =~ "node-01" ]]
    [[ "$output" =~ "node-02" ]]
}

@test "check_deployment_status should report status across all machines" {

    mock_ssh_functions

    run check_deployment_status "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "status" ]]
}

@test "deploy_with_dependencies should handle deployment order" {

    mock_ssh_functions

    # Create mock bundles
    for machine in driver node-01 node-02; do
        mkdir -p "$BUNDLES_DIR/$machine"
        echo "mock compose for $machine" > "$BUNDLES_DIR/$machine/docker-compose.yaml"
    done

    run deploy_with_dependencies "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "dependencies" ]]
}

@test "rollback_deployment should undo deployment on machine" {

    mock_ssh_functions

    run rollback_deployment "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
        [[ "$output" =~ Rolling\ back|Rollback\ completed ]]
}

@test "should handle SSH connection failures gracefully" {


    # Override SSH to simulate failure
    ssh_test_connection() {
        return 1
    }
    export -f ssh_test_connection

    run test_machine_connectivity "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 1 ]
    [[ "$output" =~ Failed|failed|error|cannot ]]
}

@test "should handle missing bundle files gracefully" {

    mock_ssh_functions

    # Don't create bundle files
    run copy_bundle_to_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 1 ]
    [[ "$output" =~ not\ found|missing|error ]]
}

@test "should handle deployment failures gracefully" {


    # Override SSH to simulate deployment failure
    ssh_execute() {
        if [[ "$2" =~ "docker compose up" ]]; then
            return 1
        fi
        return 0
    }
    export -f ssh_execute

    run deploy_bundle_on_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 1 ]
    [[ "$output" =~ Failed|failed|error ]]
}


@test "should generate bundles before deployment if missing" {

    mock_ssh_functions

    rm -rf "$BUNDLES_DIR"
    run deploy_to_all_machines "$HOMELAB_CONFIG"
    assert_output --partial "Generating bundles before deployment"
}

@test "should support dry-run mode without executing commands" {

    mock_ssh_functions

    run deploy_to_all_machines "$HOMELAB_CONFIG" --dry-run
    echo "output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ dry.*run|would.*deploy ]]
}

@test "should support deploying to specific machines only" {

    mock_ssh_functions

    mkdir -p "$BUNDLES_DIR/driver"
    echo "mock compose" > "$BUNDLES_DIR/driver/docker-compose.yaml"

    run deploy_to_specific_machines "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "driver" ]]
    [[ ! "$output" =~ "node-01" ]]
}

@test "should handle machine filtering and targeting" {


    run filter_machines_by_role "manager" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    run filter_machines_by_labels "web" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
}

@test "should provide deployment progress reporting" {

    mock_ssh_functions

    # Create mock bundles
    for machine in driver node-01 node-02; do
        mkdir -p "$BUNDLES_DIR/$machine"
        echo "mock compose" > "$BUNDLES_DIR/$machine/docker-compose.yaml"
    done

    run deploy_to_all_machines "$HOMELAB_CONFIG" --progress
    [ "$status" -eq 0 ]
    [[ "$output" =~ progress|%|[0-9]/[0-9] ]]
}

@test "should collect and report deployment logs" {

    mock_ssh_functions

    run collect_deployment_logs "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "logs" ]]
}
