#!/usr/bin/env bats

# Tests for Docker Swarm Cluster Management
# Part of Issue #39 - Docker Swarm Cluster Management
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
    export TEST_CONFIG="$TEST_DIR/homelab.yaml"
    export SWARM_TOKEN_FILE="$TEST_DIR/.swarm_token"
    export HOMELAB_CONFIG="$TEST_CONFIG"

    # Create test configuration
    create_test_swarm_config
}

teardown() {
    # Clean up temporary directories
    if [[ -n "$TEST_DIR" && -d "$TEST_DIR" ]]; then
        rm -rf "$TEST_DIR" 2>/dev/null || true
    fi
}

# Helper function to create test Swarm configuration with NEW format
create_test_swarm_config() {
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_swarm

environment:
  BASE_DOMAIN: test.local
  PROJECT_ROOT: /opt/homelab

machines:
  driver:
    ip: 192.168.1.100
    ssh_user: ubuntu
    role: manager
    labels:
      storage: ssd
      gpu: nvidia
  node-01:
    ip: 192.168.1.101
    ssh_user: ubuntu
    role: worker
    labels:
      storage: hdd
  node-02:
    ip: 192.168.1.102
    ssh_user: ubuntu
    role: worker
    labels:
      storage: ssd
  nas:
    ip: 192.168.1.50
    ssh_user: admin
    swarm_node: false

services:
  nginx:
    image: nginx:alpine
    ports: [80, 443]
    deploy: all

  web_app:
    image: nginx:alpine
    port: 8080
    deploy: any
    replicas: 3
EOF
}

# Helper function to create invalid configuration
create_invalid_config() {
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_compose

# Missing machines section for Swarm
services:
  nginx:
    image: nginx:alpine
EOF
}

# Mock docker commands for testing
mock_docker_swarm_init() {
    echo "Swarm initialized: $1"
    return 0
}

mock_docker_swarm_get_worker_token() {
    echo "SWMTKN-1-test-token-12345"
    return 0
}

mock_docker_node_update_label() {
    # Extract the label from the arguments (format: --label-add key=value nodename)
    local label="$2"
    echo "Mock: docker node update --label-add $label $3"
    return 0
}

mock_ssh_docker_command() {
    echo "SSH Docker command: $1 -> $2"
    return 0
}

# Export mock functions
export -f mock_docker_swarm_init
export -f mock_docker_swarm_get_worker_token
export -f mock_docker_node_update_label
export -f mock_ssh_docker_command

# ================================
# RED PHASE - Failing Tests First
# ================================

@test "swarm_cluster_manager.sh script exists and is executable" {
    local script_path="$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # This should FAIL initially (RED phase)
    [ -f "$script_path" ]
    [ -x "$script_path" ]
}

@test "get_manager_machine identifies manager from machines configuration" {
    # Source the script
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Create machines.yaml config
    cat > "$TEST_DIR/machines.yaml" << EOF
machines:
  manager:
    ip: 192.168.1.10
    user: admin
    role: manager
  worker-01:
    ip: 192.168.1.11
    user: admin
    role: worker
EOF

    # Valid configuration should return manager
    run get_manager_machine "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"manager"* ]]
}

@test "get_manager_machine returns first manager when multiple managers exist" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Create machines.yaml with 3 managers (for HA)
    cat > "$TEST_DIR/machines.yaml" << EOF
machines:
  manager1:
    ip: 192.168.1.10
    role: manager
  manager2:
    ip: 192.168.1.11
    role: manager
  manager3:
    ip: 192.168.1.12
    role: manager
  worker-01:
    ip: 192.168.1.20
    role: worker
EOF

    # Should return ONLY the first manager (for swarm init, etc.)
    run get_manager_machine "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    [ "$output" = "manager1" ]  # Exact match - only first manager, not all three
}

@test "get_worker_machines returns empty when config has no role fields" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Create machines.yaml WITHOUT role fields (invalid/legacy config)
    cat > "$TEST_DIR/machines.yaml" << EOF
machines:
  manager:
    ip: 192.168.1.10
    user: admin
    swarm_node: true
  worker-01:
    ip: 192.168.1.11
    user: admin
    swarm_node: true
  worker-02:
    ip: 192.168.1.12
    user: admin
    swarm_node: true
  nas:
    ip: 192.168.1.50
    user: admin
    swarm_node: false
EOF

    # Should return empty since there are no machines with role: worker
    run get_worker_machines "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    # Output should be empty or whitespace only
    [[ -z "${output// /}" ]]
}

@test "get_worker_machines returns only machines with role: worker" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Create machines.yaml with multiple managers and workers (real-world scenario)
    cat > "$TEST_DIR/machines.yaml" << EOF
machines:
  manager-01:
    ip: 192.168.1.10
    ssh_user: admin
    role: manager
    swarm_node: true
  manager-02:
    ip: 192.168.1.11
    ssh_user: admin
    role: manager
    swarm_node: true
  manager-03:
    ip: 192.168.1.12
    ssh_user: admin
    role: manager
    swarm_node: true
  worker-01:
    ip: 192.168.1.20
    ssh_user: admin
    role: worker
    swarm_node: true
  worker-02:
    ip: 192.168.1.21
    ssh_user: admin
    role: worker
    swarm_node: true
  nas:
    ip: 192.168.1.50
    ssh_user: admin
    role: storage
    swarm_node: false
EOF

    # Should return ONLY machines with role: worker
    run get_worker_machines "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"worker-01"* ]]
    [[ "$output" == *"worker-02"* ]]
    # Should NOT include managers
    [[ "$output" != *"manager-01"* ]]
    [[ "$output" != *"manager-02"* ]]
    [[ "$output" != *"manager-03"* ]]
    # Should NOT include storage nodes
    [[ "$output" != *"nas"* ]]
}

@test "get_manager_machine identifies manager from configuration" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run get_manager_machine "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [ "$output" = "driver" ]
}


@test "get_machine_host extracts host IP from configuration" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run get_machine_host "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [ "$output" = "192.168.1.100" ]

    run get_machine_host "node-01" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [ "$output" = "192.168.1.101" ]
}

@test "get_machine_user extracts SSH user from configuration" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run get_machine_user "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [ "$output" = "ubuntu" ]
}

@test "get_machine_labels extracts labels from configuration" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run get_machine_labels "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" == *"storage=ssd"* ]]
    [[ "$output" == *"gpu=nvidia"* ]]
}

@test "initialize_swarm_cluster fails with invalid configuration" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    create_invalid_config
    run initialize_swarm_cluster "$TEST_CONFIG"
    [ "$status" -eq 1 ]
}

@test "initialize_swarm_cluster initializes manager node" {
    # Mock docker functions
    # shellcheck disable=SC2317
    docker_swarm_init() { mock_docker_swarm_init "$@"; }
    # shellcheck disable=SC2317
    docker_swarm_get_worker_token() { mock_docker_swarm_get_worker_token "$@"; }
    # shellcheck disable=SC2317
    ssh_docker_command() { mock_ssh_docker_command "$@"; }
    # shellcheck disable=SC2317
    docker_node_update_label() { mock_docker_node_update_label "$@"; }
    # shellcheck disable=SC2317
    machines_my_ip() { echo "127.0.0.1"; }

    export -f docker_swarm_init
    export -f docker_swarm_get_worker_token
    export -f ssh_docker_command
    export -f docker_node_update_label
    export -f machines_my_ip

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Re-define the mocks after sourcing to override any imported functions
    is_swarm_active() { return 1; }  # Swarm NOT active - needs initialization
    machines_my_ip() { echo "127.0.0.1"; }
    docker_swarm_init() { mock_docker_swarm_init "$@"; }
    docker_swarm_get_worker_token() { mock_docker_swarm_get_worker_token "$@"; }
    ssh_docker_command() { mock_ssh_docker_command "$@"; }
    docker_node_update_label() { mock_docker_node_update_label "$@"; }
    join_worker_nodes() { echo "TEST_SUCCESS_MESSAGE"; return 0; }
    label_swarm_nodes() { return 0; }
    export -f is_swarm_active machines_my_ip docker_swarm_init docker_swarm_get_worker_token ssh_docker_command docker_node_update_label join_worker_nodes label_swarm_nodes

    # Create machines.yaml config for local testing
    cat > "$TEST_DIR/machines.yaml" << 'EOF'
machines:
  manager:
    ip: 127.0.0.1
    ssh_user: testuser
    role: manager
EOF

    run initialize_swarm_cluster "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"TEST_SUCCESS_MESSAGE"* ]]

    # Check token file was created
    [ -f "$SWARM_TOKEN_FILE" ]
    [ "$(cat "$SWARM_TOKEN_FILE")" = "SWMTKN-1-test-token-12345" ]
}

# ================================
# RED Phase - Idempotency Tests for initialize_swarm_cluster
# ================================

@test "initialize_swarm_cluster skips init when swarm already active" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock to show swarm is already active
    is_swarm_active() { return 0; }  # Swarm already active
    is_node_manager() { return 0; }  # Already manager
    machines_my_ip() { echo "127.0.0.1"; }

    # This should NOT be called if swarm is already active
    docker_swarm_init() {
        echo "ERROR: docker_swarm_init was called when swarm already active!"
        return 1  # This should cause test failure
    }
    export -f is_swarm_active is_node_manager machines_my_ip docker_swarm_init

    cat > "$TEST_DIR/machines.yaml" << 'EOF'
machines:
  manager:
    ip: 127.0.0.1
    ssh_user: testuser
    role: manager
EOF

    run initialize_swarm_cluster "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"already initialized"* ]]  # Should indicate skipping
    [[ "$output" != *"ERROR: docker_swarm_init was called"* ]]  # Should NOT call init
}

@test "initialize_swarm_cluster syncs labels even when swarm already active" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock swarm as already active
    is_swarm_active() { return 0; }  # Swarm already active
    is_node_manager() { return 0; }
    machines_my_ip() { echo "127.0.0.1"; }

    # Track if label_swarm_nodes was called
    label_swarm_nodes() {
        echo "LABEL_SYNC_CALLED"
        return 0
    }

    # Track if join_worker_nodes was called
    join_worker_nodes() {
        echo "JOIN_WORKERS_CALLED"
        return 0
    }

    # Get token should be called
    docker_swarm_get_worker_token() {
        echo "SWMTKN-1-existing-token"
        return 0
    }

    # Init should NOT be called
    docker_swarm_init() { echo "ERROR: should not init"; return 1; }

    export -f is_swarm_active is_node_manager machines_my_ip label_swarm_nodes docker_swarm_init join_worker_nodes docker_swarm_get_worker_token

    cat > "$TEST_DIR/machines.yaml" << 'EOF'
machines:
  manager:
    ip: 127.0.0.1
    ssh_user: testuser
    role: manager
    labels:
      dns-primary: true
EOF

    run initialize_swarm_cluster "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    # Should call join_worker_nodes even when swarm already active (idempotent)
    [[ "$output" == *"JOIN_WORKERS_CALLED"* ]]
    # Labels should ALWAYS be synced
    [[ "$output" == *"LABEL_SYNC_CALLED"* ]]
    # Should NOT try to init
    [[ "$output" != *"ERROR: should not init"* ]]
}

@test "initialize_swarm_cluster proceeds with init when swarm inactive" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock swarm state to be inactive (need to init)
    is_swarm_active() { return 1; }  # Swarm NOT active
    docker_swarm_init() { echo "Mock: docker swarm init $1"; return 0; }
    docker_swarm_get_worker_token() { echo "SWMTKN-1-new-token"; return 0; }
    join_worker_nodes() { return 0; }
    label_swarm_nodes() { return 0; }
    machines_my_ip() { echo "127.0.0.1"; }
    export -f is_swarm_active docker_swarm_init docker_swarm_get_worker_token join_worker_nodes label_swarm_nodes machines_my_ip

    cat > "$TEST_DIR/machines.yaml" << 'EOF'
machines:
  manager:
    ip: 127.0.0.1
    ssh_user: testuser
    role: manager
EOF

    run initialize_swarm_cluster "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"SWARM CLUSTER INITIALIZATION"* ]]
    [[ "$output" == *"docker swarm init"* ]]  # SHOULD attempt init
}

@test "join_worker_nodes joins workers to cluster" {
    # Mock functions
    # shellcheck disable=SC2317
    ssh_docker_command() { mock_ssh_docker_command "$@"; }
    export -f ssh_docker_command

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Re-define mocks after sourcing to override imports
    ssh_docker_command() { mock_ssh_docker_command "$@"; }
    export -f ssh_docker_command

    run join_worker_nodes "$TEST_CONFIG" "SWMTKN-1-test-token" "192.168.1.100"
    [ "$status" -eq 0 ]
    [[ "$output" == *"node-01"* ]]
    [[ "$output" == *"node-02"* ]]
}

# ================================
# RED Phase - Idempotent Worker Joining Tests
# ================================

@test "join_worker_nodes skips workers already in swarm" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock: worker-01 is already in swarm, worker-02 is not
    is_worker_in_swarm() {
        local worker_node="$1"
        if [[ "$worker_node" == *"192.168.1.101"* ]]; then
            return 0  # worker-01 is already in swarm
        else
            return 1  # worker-02 is NOT in swarm
        fi
    }

    # This should NOT be called for already-joined workers
    ssh_docker_command() {
        local node="$1"
        local cmd="$2"
        if [[ "$cmd" == *"swarm join"* ]]; then
            echo "Mock: Joining $node"
            return 0
        fi
        return 1
    }
    export -f is_worker_in_swarm ssh_docker_command

    # Create test config
    cat > "$TEST_DIR/machines.yaml" << 'EOF'
machines:
  manager:
    ip: 192.168.1.100
    ssh_user: testuser
    role: manager
  worker-01:
    ip: 192.168.1.101
    ssh_user: testuser
    role: worker
  worker-02:
    ip: 192.168.1.102
    ssh_user: testuser
    role: worker
EOF

    run join_worker_nodes "$TEST_DIR/machines.yaml" "SWMTKN-1-test-token" "192.168.1.100"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Found workers to join: worker-02"* ]]  # Should only include worker-02
    [[ "$output" == *"Joining worker: worker-02"* ]]  # Should only join worker-02
    [[ "$output" != *"worker-01"* ]]  # Should NOT include worker-01 anywhere
}

# ================================
# RED Phase - Worker Node Membership Checking Tests
# ================================

@test "is_worker_in_swarm detects node already in swarm" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock is_remote_node_in_swarm to return success (node in swarm)
    is_remote_node_in_swarm() { return 0; }
    export -f is_remote_node_in_swarm

    run is_worker_in_swarm "testuser@worker-01"
    [ "$status" -eq 0 ]
}

@test "is_worker_in_swarm detects node not in swarm" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock is_remote_node_in_swarm to return failure (node not in swarm)
    is_remote_node_in_swarm() { return 1; }
    export -f is_remote_node_in_swarm

    run is_worker_in_swarm "testuser@worker-01"
    [ "$status" -eq 1 ]
}

@test "get_workers_not_in_swarm returns only unjoined workers" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock worker status: worker-01 (IP .101) is in swarm, worker-02 (IP .102) is not
    is_remote_node_in_swarm() {
        local node="$1"
        if [[ "$node" == *"192.168.1.101"* ]]; then
            return 0  # worker-01 (IP .101) is in swarm
        else
            return 1  # worker-02 (IP .102) is NOT in swarm
        fi
    }
    export -f is_remote_node_in_swarm

    # Create config with two workers
    cat > "$TEST_DIR/machines.yaml" << 'EOF'
machines:
  manager:
    ip: 192.168.1.100
    ssh_user: testuser
    role: manager
  worker-01:
    ip: 192.168.1.101
    ssh_user: testuser
    role: worker
  worker-02:
    ip: 192.168.1.102
    ssh_user: testuser
    role: worker
EOF

    run get_workers_not_in_swarm "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"worker-02"* ]]      # Should include worker-02 (not in swarm)
    [[ "$output" != *"worker-01"* ]]      # Should NOT include worker-01 (already in swarm)
}

@test "check_all_workers_swarm_status provides comprehensive status" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock mixed worker status: worker-01 (IP .101) is in swarm, worker-02 (IP .102) is not
    is_remote_node_in_swarm() {
        local node="$1"
        if [[ "$node" == *"192.168.1.101"* ]]; then
            return 0  # worker-01 (IP .101) is in swarm
        else
            return 1  # worker-02 (IP .102) is NOT in swarm
        fi
    }
    export -f is_remote_node_in_swarm

    # Create config with two workers
    cat > "$TEST_DIR/machines.yaml" << 'EOF'
machines:
  manager:
    ip: 192.168.1.100
    ssh_user: testuser
    role: manager
  worker-01:
    ip: 192.168.1.101
    ssh_user: testuser
    role: worker
  worker-02:
    ip: 192.168.1.102
    ssh_user: testuser
    role: worker
EOF

    run check_all_workers_swarm_status "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    [[ "$output" == *"worker-01: IN SWARM"* ]]
    [[ "$output" == *"worker-02: NOT IN SWARM"* ]]
}

@test "label_swarm_nodes applies machine labels" {
    # Mock functions
    # shellcheck disable=SC2317
    docker_node_update_label() { mock_docker_node_update_label "$@"; }
    # shellcheck disable=SC2317
    docker_node_ls() { echo "driver"; }  # Mock node exists
    export -f docker_node_update_label
    export -f docker_node_ls

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Re-define mocks after sourcing to override imports
    docker_node_update_label() { mock_docker_node_update_label "$@"; }
    docker_node_ls() { echo "driver"; }
    export -f docker_node_update_label docker_node_ls

    run label_swarm_nodes "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" == *"machine.id=driver"* ]]        # NEW: Expect machine ID label
    [[ "$output" == *"machine.role=manager"* ]]     # KEEP: Existing role label
    [[ "$output" == *"storage=ssd"* ]]              # KEEP: Custom labels
    [[ "$output" == *"gpu=nvidia"* ]]               # KEEP: Custom labels
}

# ================================
# RED Phase - Node Label Idempotency Tests
# ================================

@test "node_has_label detects existing labels correctly" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock docker node inspect to return existing labels
    docker_node_inspect() {
        local node="$1"
        local format="$2"
        if [[ "$format" == *"Spec.Labels"* ]]; then
            echo "machine.id=worker-01,storage=ssd,gpu=nvidia"
        fi
        return 0
    }
    export -f docker_node_inspect

    run node_has_label "worker-01" "storage=ssd"
    [ "$status" -eq 0 ]  # Should find existing label

    run node_has_label "worker-01" "missing=label"
    [ "$status" -eq 1 ]  # Should NOT find non-existent label
}

@test "get_node_labels returns all labels from a node" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock docker node inspect to return existing labels
    docker_node_inspect() {
        local node="$1"
        local format="$2"
        if [[ "$format" == *"Spec.Labels"* ]]; then
            echo "machine.id=driver machine.role=manager storage=ssd "
        fi
        return 0
    }
    export -f docker_node_inspect

    run get_node_labels "driver"
    [ "$status" -eq 0 ]
    [[ "$output" == *"machine.id=driver"* ]]
    [[ "$output" == *"machine.role=manager"* ]]
    [[ "$output" == *"storage=ssd"* ]]
}

@test "label_swarm_nodes skips labels that already exist" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock: node already has some labels
    node_has_label() {
        local node="$1"
        local label="$2"
        case "$label" in
            "machine.id=driver"|"storage=ssd")
                return 0  # These labels already exist
                ;;
            *)
                return 1  # Other labels don't exist
                ;;
        esac
    }

    # Track which labels are attempted to be added
    docker_node_update_label() {
        local action="$1"
        local label="$2"
        local node="$3"
        echo "Mock: $action $label $node"
        return 0
    }

    docker_node_ls() { echo "driver"; }
    export -f node_has_label docker_node_update_label docker_node_ls

    run label_swarm_nodes "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    # Labels are skipped silently for cleaner output
    [[ "$output" != *"Mock: --label-add machine.id=driver"* ]]  # Should NOT add existing label
    [[ "$output" != *"Mock: --label-add storage=ssd"* ]]  # Should NOT add existing label
    [[ "$output" == *"Mock: --label-add gpu=nvidia"* ]]  # SHOULD add missing label
}

@test "label_swarm_nodes removes labels no longer in config" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Create config WITHOUT the 'obsolete' label
    cat > "$TEST_DIR/machines.yaml" << 'EOF'
machines:
  driver:
    ip: 192.168.1.100
    ssh_user: ubuntu
    role: manager
    labels:
      storage: ssd
EOF

    # Mock: node has an extra label 'obsolete=true' that's not in config
    node_has_label() {
        local node="$1"
        local label="$2"
        case "$label" in
            "machine.id=driver"|"machine.role=manager"|"storage=ssd"|"obsolete=true")
                return 0  # All these exist on node
                ;;
            *)
                return 1
                ;;
        esac
    }

    # Mock: return existing labels on node (includes 'obsolete' which is not in config)
    get_node_labels() {
        echo "machine.id=driver machine.role=manager storage=ssd obsolete=true"
    }

    # Track label operations
    docker_node_update_label() {
        local action="$1"
        local label="$2"
        local node="$3"
        echo "LABEL_OP: $action $label $node"
        return 0
    }

    docker_node_ls() { echo "driver"; }
    export -f node_has_label get_node_labels docker_node_update_label docker_node_ls

    run label_swarm_nodes "$TEST_DIR/machines.yaml"
    [ "$status" -eq 0 ]
    # Should remove the obsolete label that's no longer in config
    [[ "$output" == *"LABEL_OP: --label-rm obsolete driver"* ]]
}

@test "monitor_swarm_cluster shows cluster status" {
    # Mock functions
    docker_node_list() {
        if [[ "$1" == "table"* ]]; then
            echo -e "HOSTNAME\tSTATUS\tAVAILABILITY\tMANAGER STATUS"
            echo -e "driver\tReady\tActive\tLeader"
            echo -e "node-01\tReady\tActive\t"
        else
            echo -e "driver\nnode-01"
        fi
    }

    docker_node_inspect() {
        echo "ready"
    }

    docker_service_list() {
        echo -e "ID\tNAME\tMODE\tREPLICAS"
        echo -e "abc123\tnginx\tglobal\t2/2"
    }

    export -f docker_node_list
    export -f docker_node_inspect
    export -f docker_service_list

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Re-define mocks after sourcing to override imports
    docker_node_list() {
        if [[ "$1" == "table"* ]]; then
            echo -e "HOSTNAME\tSTATUS\tAVAILABILITY\tMANAGER STATUS"
            echo -e "driver\tReady\tActive\tLeader"
            echo -e "node-01\tReady\tActive\t"
        else
            echo -e "driver\nnode-01"
        fi
    }
    docker_node_inspect() { echo "ready"; }
    docker_service_list() {
        echo -e "ID\tNAME\tMODE\tREPLICAS"
        echo -e "abc123\tnginx\tglobal\t2/2"
    }
    export -f docker_node_list docker_node_inspect docker_service_list

    run monitor_swarm_cluster
    [ "$status" -eq 0 ]
    [[ "$output" == *"Swarm Cluster Topology"* ]]
    [[ "$output" == *"All nodes healthy"* ]]
    [[ "$output" == *"Swarm Services"* ]]
}

@test "monitor_swarm_cluster should not have template artifacts in output" {
    # Mock docker command directly
    docker() {
        case "$1 $2 $3" in
            "node ls --format")
                if [[ "$4" == "table"* ]]; then
                    echo "HOSTNAME             STATUS    AVAILABILITY   MANAGER STATUS"
                    echo "cody-X570-GAMING-X   Ready     Active         Leader"
                    echo "giant                Ready     Active         "
                else
                    echo "cody-X570-GAMING-X"
                    echo "giant"
                fi
                ;;
            "service ls")
                echo "ID        NAME    MODE      REPLICAS"
                echo "abc123    nginx   global    2/2"
                ;;
        esac
    }

    docker_node_inspect() {
        echo "ready"
    }

    export -f docker docker_node_inspect

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Re-export mocks after sourcing
    export -f docker docker_node_inspect

    run monitor_swarm_cluster
    [ "$status" -eq 0 ]

    # Should NOT contain template artifacts like }}
    [[ "$output" != *"}}"* ]]

    # Should contain proper node names without artifacts
    [[ "$output" == *"cody-X570-GAMING-X"* ]]
    [[ "$output" == *"giant"* ]]
}

@test "script shows usage when called with --help" {
    run "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"init-cluster"* ]]
    [[ "$output" == *"join-workers"* ]]
    [[ "$output" == *"monitor-cluster"* ]]
}

@test "script fails with unknown command" {
    run "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh" invalid-command
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown command"* ]]
}

@test "init-cluster command works end-to-end" {
    skip "End-to-end test requires real SSH environment or integration test setup"

    # Note: This test executes the script as a subprocess, so mocked functions
    # defined in the test environment don't carry over. This test should be
    # moved to an integration test suite or the script should be modified to
    # support test mode detection.

    # Mock all docker functions
    docker_swarm_init() { mock_docker_swarm_init "$@"; }
    docker_swarm_get_worker_token() { mock_docker_swarm_get_worker_token "$@"; }
    ssh_docker_command() { mock_ssh_docker_command "$@"; }
    docker_node_update_label() { mock_docker_node_update_label "$@"; }

    export -f docker_swarm_init
    export -f docker_swarm_get_worker_token
    export -f ssh_docker_command
    export -f docker_node_update_label

    # Create localhost config
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_swarm

machines:
  driver:
    ip: 127.0.0.1
    ssh_user: testuser
    role: manager
EOF

    # Override mocks after loading
    machines_my_ip() { echo "127.0.0.1"; }
    export -f machines_my_ip

    run "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh" init-cluster -c "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Swarm cluster initialization complete"* ]]
}

# ================================
# RED Phase - Swarm State Detection Tests
# ================================

@test "is_swarm_active returns 0 when swarm is active" {
    # Mock docker info to return active swarm state
    docker() {
        if [[ "$1" == "info" && "$2" == "--format" && "$3" == "{{.Swarm.LocalNodeState}}" ]]; then
            echo "active"
            return 0
        fi
        return 1
    }
    export -f docker

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run is_swarm_active
    [ "$status" -eq 0 ]
}

@test "is_swarm_active returns 1 when swarm is inactive" {
    # Mock docker info to return inactive swarm state
    docker() {
        if [[ "$1" == "info" && "$2" == "--format" && "$3" == "{{.Swarm.LocalNodeState}}" ]]; then
            echo "inactive"
            return 0
        fi
        return 1
    }
    export -f docker

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run is_swarm_active
    [ "$status" -eq 1 ]
}

@test "is_node_manager returns 0 when node is manager" {
    # Mock docker info to return manager status
    docker() {
        if [[ "$1" == "info" && "$2" == "--format" && "$3" == "{{.Swarm.ControlAvailable}}" ]]; then
            echo "true"
            return 0
        fi
        return 1
    }
    export -f docker

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run is_node_manager
    [ "$status" -eq 0 ]
}

@test "is_node_manager returns 1 when node is worker" {
    # Mock docker info to return worker status
    docker() {
        if [[ "$1" == "info" && "$2" == "--format" && "$3" == "{{.Swarm.ControlAvailable}}" ]]; then
            echo "false"
            return 0
        fi
        return 1
    }
    export -f docker

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run is_node_manager
    [ "$status" -eq 1 ]
}

@test "get_swarm_status returns correct status information" {
    # Mock docker info to return comprehensive swarm info
    docker() {
        if [[ "$1" == "info" && "$2" == "--format" ]]; then
            case "$3" in
                "{{.Swarm.LocalNodeState}}")
                    echo "active"
                    return 0
                    ;;
                "{{.Swarm.ControlAvailable}}")
                    echo "true"
                    return 0
                    ;;
                "{{.Swarm.NodeID}}")
                    echo "test-node-id-123"
                    return 0
                    ;;
            esac
        fi
        return 1
    }
    export -f docker

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run get_swarm_status
    [ "$status" -eq 0 ]
    [[ "$output" == *"active"* ]]
    [[ "$output" == *"manager"* ]]
    [[ "$output" == *"test-node-id-123"* ]]
}

@test "is_remote_node_in_swarm checks remote node via SSH" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock SSH command AFTER sourcing to override the real function
    ssh_execute() {
        local node="$1"
        local cmd="$2"
        if [[ "$cmd" == *"docker info"* && "$cmd" == *"LocalNodeState"* ]]; then
            echo "active"
            return 0
        fi
        return 1
    }
    export -f ssh_execute

    run is_remote_node_in_swarm "testuser@testhost"
    [ "$status" -eq 0 ]
}

# ================================
# Integration Tests (More Complex)
# ================================


@test "swarm_cluster_manager uses machines_get_ip for IP-first resolution" {
    # Verify that swarm_cluster_manager.sh contains the IP-first function call
    run grep "machines_get_ip" "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"machines_get_ip"* ]]

    # Verify it's NOT using the old function
    run grep "machines_get_host_ip" "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"
    [ "$status" -eq 1 ]  # Should not find it
}

@test "get_machine_host should work with new machines.yaml format" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # This should FAIL initially - testing with new format
    run get_machine_host "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [ "$output" = "192.168.1.100" ]

    run get_machine_host "node-01" "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [ "$output" = "192.168.1.101" ]
}

# =======================
# Network Creation Idempotency Tests
# =======================

@test "network_exists returns true when network exists" {
    # Mock docker network ls
    # shellcheck disable=SC2317
    docker() {
        if [[ "$1" == "network" && "$2" == "ls" ]]; then
            echo "homelab-net"
        fi
    }
    export -f docker

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run network_exists "homelab-net"
    [ "$status" -eq 0 ]
}

@test "network_exists returns false when network does not exist" {
    # Mock docker network ls to return empty
    # shellcheck disable=SC2317
    docker() {
        if [[ "$1" == "network" && "$2" == "ls" ]]; then
            echo ""
        fi
    }
    export -f docker

    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run network_exists "nonexistent-net"
    [ "$status" -eq 1 ]
}

@test "ensure_overlay_network creates network when it does not exist" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock docker commands after sourcing
    # shellcheck disable=SC2317
    docker() {
        if [[ "$1" == "network" && "$2" == "ls" ]]; then
            echo ""  # Network doesn't exist
        elif [[ "$1" == "network" && "$2" == "create" ]]; then
            echo "MOCK_CREATE_CALLED"  # Use output to verify create was called
        fi
    }
    export -f docker

    run ensure_overlay_network "test-net"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Creating overlay network"* ]]
}

@test "ensure_overlay_network skips creation when network exists" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock docker commands after sourcing
    # shellcheck disable=SC2317
    docker() {
        if [[ "$1" == "network" && "$2" == "ls" ]]; then
            echo "test-net"  # Network exists
        elif [[ "$1" == "network" && "$2" == "create" ]]; then
            echo "MOCK_CREATE_SHOULD_NOT_BE_CALLED"
        fi
    }
    export -f docker

    run ensure_overlay_network "test-net"
    [ "$status" -eq 0 ]
    [[ "$output" == *"already exists"* ]]
    [[ "$output" != *"MOCK_CREATE_SHOULD_NOT_BE_CALLED"* ]]
}

# =======================
# Pre-flight Validation Tests
# =======================

@test "validate_config_file returns true for valid configuration" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run validate_config_file "$TEST_CONFIG"
    [ "$status" -eq 0 ]
}

@test "validate_config_file returns false for missing file" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    run validate_config_file "/nonexistent/config.yaml"
    [ "$status" -eq 1 ]
    [[ "$output" == *"not found"* ]]
}

@test "validate_ssh_connectivity checks only swarm machines" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock ssh_test_connection
    # shellcheck disable=SC2317
    ssh_test_connection() {
        echo "SSH connectivity check for $1"
        return 0  # Success
    }
    export -f ssh_test_connection

    run validate_ssh_connectivity "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" == *"ubuntu@192.168.1.100"* ]]  # Should check driver
    [[ "$output" == *"ubuntu@192.168.1.101"* ]]  # Should check node-01
    [[ "$output" == *"ubuntu@192.168.1.102"* ]]  # Should check node-02
    [[ "$output" != *"admin@192.168.1.50"* ]]    # Should NOT check nas
}

@test "validate_docker_availability checks Docker only on swarm machines" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock ssh_check_docker
    # shellcheck disable=SC2317
    ssh_check_docker() {
        echo "Docker check for $1"
        return 0  # Docker is running
    }
    export -f ssh_check_docker

    run validate_docker_availability "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" == *"ubuntu@192.168.1.100"* ]]  # Should check driver
    [[ "$output" == *"ubuntu@192.168.1.101"* ]]  # Should check node-01
    [[ "$output" == *"ubuntu@192.168.1.102"* ]]  # Should check node-02
    [[ "$output" != *"admin@192.168.1.50"* ]]    # Should NOT check nas
}

@test "run_preflight_checks validates all requirements" {
    source "$PROJECT_ROOT/scripts/docker_swarm/cluster.sh"

    # Mock all validation functions to succeed
    # shellcheck disable=SC2317
    validate_config_file() {
        echo "Config validation passed"
        return 0
    }
    # shellcheck disable=SC2317
    validate_ssh_connectivity() {
        echo "SSH validation passed"
        return 0
    }
    # shellcheck disable=SC2317
    validate_docker_availability() {
        echo "Docker validation passed"
        return 0
    }
    export -f validate_config_file validate_ssh_connectivity validate_docker_availability

    run run_preflight_checks "$TEST_CONFIG"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Config validation passed"* ]]
    [[ "$output" == *"SSH validation passed"* ]]
    [[ "$output" == *"Docker validation passed"* ]]
}
