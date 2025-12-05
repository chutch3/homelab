#!/usr/bin/env bats

# Tests for Docker Swarm Monitoring Configuration
# Following TDD workflow: RED phase - write failing tests first

load ../test_helper

setup() {
    # Set TEST mode to skip Docker validation during script sourcing
    export TEST=1

    # Set PROJECT_ROOT relative to test location
    local project_root_path
    project_root_path="$(cd "$(dirname "$BATS_TEST_FILENAME")/../../../.." && pwd)"
    export PROJECT_ROOT="$project_root_path"

    # Create temporary directories for testing
    local test_dir
    test_dir=$(mktemp -d)
    export TEST_DIR="$test_dir"
    export TEST_CONFIG="$TEST_DIR/machines.yaml"
    export HOMELAB_CONFIG="$TEST_CONFIG"

    # Create test configuration
    create_test_config

    # Set MACHINES_FILE to point to test config
    export MACHINES_FILE="$TEST_CONFIG"

    # Mock common utility functions before sourcing monitoring script
    machines_get_ssh_user() {
        echo "ubuntu"
    }
    export -f machines_get_ssh_user

    machines_get_ip() {
        local machine=$1
        case "$machine" in
            manager-01) echo "192.168.1.100" ;;
            worker-01) echo "192.168.1.101" ;;
            *) echo "" ;;
        esac
    }
    export -f machines_get_ip

    machines_parse() {
        local config_file="${1:-$MACHINES_FILE}"
        if [ "$config_file" = "$TEST_CONFIG" ] || [ "$config_file" = "swarm" ]; then
            echo "manager-01 worker-01"
        else
            echo ""
        fi
    }
    export -f machines_parse

    # Source the monitoring script
    source "$PROJECT_ROOT/scripts/docker_swarm/monitoring.sh"
}

teardown() {
    # Clean up temporary directories
    if [[ -n "$TEST_DIR" && -d "$TEST_DIR" ]]; then
        rm -rf "$TEST_DIR" 2>/dev/null || true
    fi
}

# Helper function to create test configuration
create_test_config() {
    cat > "$TEST_CONFIG" << 'EOF'
machines:
  manager-01:
    ip: 192.168.1.100
    ssh_user: ubuntu
    role: manager
    swarm_node: true
    labels:
      monitoring: true
  worker-01:
    ip: 192.168.1.101
    ssh_user: ubuntu
    role: worker
    swarm_node: true
    labels:
      storage: true
  nas:
    ip: 192.168.1.50
    ssh_user: admin
    swarm_node: false
EOF
}

# --- Test: Script Loading ---

@test "monitoring.sh: script loads without errors" {
    run bash -c "source '$PROJECT_ROOT/scripts/docker_swarm/monitoring.sh'"
    assert_success
}

@test "monitoring.sh: exports required functions" {
    run bash -c "source '$PROJECT_ROOT/scripts/docker_swarm/monitoring.sh' && declare -F configure_docker_metrics"
    assert_success
    assert_output --partial "configure_docker_metrics"
}

# --- Test: Docker Daemon Configuration ---

@test "monitoring.sh: configure_docker_metrics creates daemon.json when missing" {
    # Mock SSH commands
    ssh_execute() {
        local user_host=$1
        local command=$2

        case "$command" in
            "test -f /etc/docker/daemon.json")
                return 1  # File doesn't exist
                ;;
            "sudo mkdir -p /etc/docker")
                return 0
                ;;
            "sudo tee /etc/docker/daemon.json > /dev/null")
                # Simulate writing file
                cat > "$TEST_DIR/daemon.json"
                return 0
                ;;
            "sudo systemctl restart docker")
                return 0
                ;;
            "docker info > /dev/null 2>&1")
                return 0
                ;;
            *)
                return 0
                ;;
        esac
    }
    export -f ssh_execute

    run configure_docker_metrics "manager-01"
    assert_success
    assert_output --partial "Creating new daemon.json"
    assert_output --partial "Docker daemon reloaded on manager-01"
}

@test "monitoring.sh: configure_docker_metrics merges with existing daemon.json" {
    # Mock SSH commands
    ssh_execute() {
        local user_host=$1

        local command=$2

        case "$command" in
            "test -f /etc/docker/daemon.json")
                return 0  # File exists
                ;;
            "cat /etc/docker/daemon.json")
                echo '{"log-driver": "json-file"}'
                ;;
            "sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup")
                return 0
                ;;
            "sudo tee /etc/docker/daemon.json > /dev/null")
                cat > "$TEST_DIR/daemon.json"
                return 0
                ;;
            "sudo systemctl restart docker")
                return 0
                ;;
            "docker info > /dev/null 2>&1")
                return 0
                ;;
            *)
                return 0
                ;;
        esac
    }
    export -f ssh_execute

    # Mock jq command
    jq() {
        if [[ "$1" == '. + {"metrics-addr": "0.0.0.0:9323", "experimental": true}' ]]; then
            echo '{"log-driver":"json-file","metrics-addr":"0.0.0.0:9323","experimental":true}'
        fi
    }
    export -f jq

    run configure_docker_metrics "manager-01"
    assert_success
    assert_output --partial "Merging metrics configuration"
}

@test "monitoring.sh: configure_docker_metrics skips when already configured" {
    # Mock SSH commands
    ssh_execute() {
        local user_host=$1

        local command=$2

        case "$command" in
            "test -f /etc/docker/daemon.json")
                return 0
                ;;
            "cat /etc/docker/daemon.json")
                echo '{"metrics-addr": "0.0.0.0:9323", "experimental": true}'
                ;;
            *)
                return 0
                ;;
        esac
    }
    export -f ssh_execute

    run configure_docker_metrics "manager-01"
    assert_success
    assert_output --partial "Metrics already configured"
}

@test "monitoring.sh: configure_docker_metrics handles restart failure" {
    # Mock SSH commands
    ssh_execute() {
        local user_host=$1

        local command=$2

        case "$command" in
            "test -f /etc/docker/daemon.json")
                return 1
                ;;
            "sudo systemctl restart docker")
                return 1  # Fail restart
                ;;
            *)
                return 0
                ;;
        esac
    }
    export -f ssh_execute

    run configure_docker_metrics "manager-01"
    assert_failure
    assert_output --partial "Failed to restart Docker daemon"
}

@test "monitoring.sh: configure_docker_metrics waits for Docker to be ready" {
    local attempt_count=0

    # Mock SSH commands
    ssh_execute() {
        local user_host=$1

        local command=$2

        case "$command" in
            "test -f /etc/docker/daemon.json")
                return 1
                ;;
            "sudo systemctl restart docker")
                return 0
                ;;
            "docker info > /dev/null 2>&1")
                attempt_count=$((attempt_count + 1))
                if [ $attempt_count -ge 3 ]; then
                    return 0  # Ready after 3 attempts
                fi
                return 1
                ;;
            *)
                return 0
                ;;
        esac
    }
    export -f ssh_execute

    run configure_docker_metrics "manager-01"
    assert_success
    assert_output --partial "Waiting for Docker to be ready"
    assert_output --partial "Docker is ready"
}

# --- Test: Configure All Nodes ---

@test "monitoring.sh: configure_all_nodes processes all Swarm nodes" {
    local configured_nodes=()

    # Mock configure_docker_metrics to log which nodes it processes
    configure_docker_metrics() {
        echo "Processing: $1"
        configured_nodes+=("$1")
        return 0
    }
    export -f configure_docker_metrics

    run configure_all_nodes "$TEST_CONFIG"
    assert_success
    assert_output --partial "Processing: manager-01"
    assert_output --partial "Processing: worker-01"
    refute_output --partial "nas"  # Not a Swarm node
}

@test "monitoring.sh: configure_all_nodes handles failures" {
    # Mock configure_docker_metrics to fail for worker-01
    configure_docker_metrics() {
        if [[ "$1" == "worker-01" ]]; then
            return 1
        fi
        return 0
    }
    export -f configure_docker_metrics

    run configure_all_nodes "$TEST_CONFIG"
    assert_failure
    assert_output --partial "Failed to configure metrics on: worker-01"
}

@test "monitoring.sh: configure_all_nodes fails when config file missing" {
    run configure_all_nodes "$TEST_DIR/missing.yaml"
    assert_failure
    assert_output --partial "Configuration file not found"
}

# --- Test: Metrics Verification ---

@test "monitoring.sh: verify_metrics checks all endpoints" {
    # Mock curl command
    curl() {
        if [[ "$*" == *"9323/metrics"* ]] || [[ "$*" == *"9100/metrics"* ]]; then
            return 0  # Success
        fi
        return 1
    }
    export -f curl

    run verify_metrics "$TEST_CONFIG"
    assert_success
    assert_output --partial "Docker metrics accessible on manager-01"
    assert_output --partial "Node Exporter accessible on manager-01"
}

@test "monitoring.sh: verify_metrics handles failed Docker metrics" {
    # Mock curl command to fail for Docker metrics
    curl() {
        if [[ "$*" == *"9323/metrics"* ]]; then
            return 1  # Fail Docker metrics
        fi
        return 0
    }
    export -f curl

    run verify_metrics "$TEST_CONFIG"
    assert_failure
    assert_output --partial "Docker metrics NOT accessible"
}

@test "monitoring.sh: verify_metrics warns on missing Node Exporter" {
    # Mock curl command to fail for Node Exporter
    curl() {
        if [[ "$*" == *"9100/metrics"* ]]; then
            return 1  # Node Exporter not running
        fi
        return 0
    }
    export -f curl

    run verify_metrics "$TEST_CONFIG"
    assert_output --partial "Node Exporter NOT accessible"
    assert_output --partial "(may not be deployed yet)"
}

# --- Test: Main Command Router ---

@test "monitoring.sh: main function routes configure command" {
    configure_all_nodes() {
        echo "CONFIGURE_CALLED"
        return 0
    }
    export -f configure_all_nodes

    run main "configure"
    assert_success
    assert_output --partial "CONFIGURE_CALLED"
}

@test "monitoring.sh: main function routes verify command" {
    verify_metrics() {
        echo "VERIFY_CALLED"
        return 0
    }
    export -f verify_metrics

    run main "verify"
    assert_success
    assert_output --partial "VERIFY_CALLED"
}

@test "monitoring.sh: main function shows help" {
    run main "help"
    assert_success
    assert_output --partial "Usage: monitoring.sh"
    assert_output --partial "configure"
    assert_output --partial "verify"
}

@test "monitoring.sh: main function handles unknown command" {
    run main "unknown"
    assert_failure
    assert_output --partial "Unknown command: unknown"
}
