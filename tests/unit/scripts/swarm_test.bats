#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export BASE_DOMAIN="test.example.com"

    # Create test certificate files structure
    mkdir -p "${TEST_TEMP_DIR}/certs/${BASE_DOMAIN}_ecc"
    mkdir -p "${TEST_TEMP_DIR}/certs"

    # Create mock certificate files
    echo "mock-fullchain-content" > "${TEST_TEMP_DIR}/certs/${BASE_DOMAIN}_ecc/fullchain.cer"
    echo "mock-key-content" > "${TEST_TEMP_DIR}/certs/${BASE_DOMAIN}_ecc/${BASE_DOMAIN}.key"
    echo "mock-ca-content" > "${TEST_TEMP_DIR}/certs/${BASE_DOMAIN}_ecc/ca.cer"
    echo "mock-dhparam-content" > "${TEST_TEMP_DIR}/certs/dhparam.pem"

    # Mock the load_env function
    load_env() {
        export BASE_DOMAIN="test.example.com"
    }

    # Source the swarm script with mocked wrapper functions
        source "${BATS_TEST_DIRNAME}/../../../scripts/wrappers/docker_wrapper.sh"
    source "${BATS_TEST_DIRNAME}/../../../scripts/wrappers/file_wrapper.sh"
    source "${BATS_TEST_DIRNAME}/../../../scripts/ssh.sh"
    source "${BATS_TEST_DIRNAME}/../../../scripts/deployments/swarm.sh"

    # Track docker commands called
    export DOCKER_COMMANDS_FILE="${TEST_TEMP_DIR}/docker_commands.log"
    # Clear any previous commands
    true > "$DOCKER_COMMANDS_FILE"

    # Mock docker wrapper functions
    docker_secret_create() {
        echo "docker secret create $1 $2" >> "$DOCKER_COMMANDS_FILE"
        echo "Creating secret: $1 from file: $2" >&2
        return 0
    }

    export -f load_env docker_secret_create
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "swarm_setup_certificates_should_create_docker_secrets_from_cert_files" {
    # Clear previous commands
    true > "$DOCKER_COMMANDS_FILE"

    # Change to test directory for relative file operations
    cd "$TEST_TEMP_DIR"

    run swarm_setup_certificates

    echo "Status: $status" >&2
    echo "Output: $output" >&2

    [ "$status" -eq 0 ]
    [[ "$output" == *"Creating swarm secrets for test.example.com"* ]]

    # Read the commands that were executed
    local commands_called
    if [ -f "$DOCKER_COMMANDS_FILE" ]; then
        commands_called=$(cat "$DOCKER_COMMANDS_FILE")
        echo "Commands called: $commands_called" >&2
    else
        echo "No commands file found at $DOCKER_COMMANDS_FILE" >&2
        return 1
    fi

    # Verify all four secrets were created with correct files
    [[ "$commands_called" == *"docker secret create ssl_full.pem ${TEST_TEMP_DIR}/certs/test.example.com_ecc/fullchain.cer"* ]]
    [[ "$commands_called" == *"docker secret create ssl_key.pem ${TEST_TEMP_DIR}/certs/test.example.com_ecc/test.example.com.key"* ]]
    [[ "$commands_called" == *"docker secret create ssl_ca.pem ${TEST_TEMP_DIR}/certs/test.example.com_ecc/ca.cer"* ]]
    [[ "$commands_called" == *"docker secret create ssl_dhparam.pem ${TEST_TEMP_DIR}/certs/dhparam.pem"* ]]
}

@test "swarm_initialize_manager_should_init_swarm_with_manager_ip" {
    # Clear previous commands
    true > "$DOCKER_COMMANDS_FILE"

    # Change to test directory for relative file operations
    cd "$TEST_TEMP_DIR"

    # Create test machines.yml file
    cat > "machines.yml" <<EOF
machines:
  - host: manager.test.com
    role: manager
    ssh_user: testuser
EOF

    # Mock machines functions
    machines_parse() {
        local key=$1
        if [ "$key" = "manager" ]; then
            echo "manager.test.com"
        fi
    }

    machines_get_host_ip() {
        local host=$1
        if [ "$host" = "manager.test.com" ]; then
            echo "192.168.1.100"
        fi
    }

    # Mock docker wrapper functions
    docker_swarm_init() {
        echo "docker swarm init --advertise-addr $1" >> "$DOCKER_COMMANDS_FILE"
        echo "Swarm initialized successfully" >&2
        return 0
    }

    docker_swarm_get_worker_token() {
        echo "docker swarm join-token -q worker" >> "$DOCKER_COMMANDS_FILE"
        echo "SWMTKN-1-test-token-12345"
        return 0
    }

    export -f machines_parse machines_get_host_ip docker_swarm_init docker_swarm_get_worker_token

    run swarm_initialize_manager

    echo "Status: $status" >&2
    echo "Output: $output" >&2

    [ "$status" -eq 0 ]
    [[ "$output" == *"Initializing swarm on manager node"* ]]
    [[ "$output" == *"Resolved manager IP: 192.168.1.100"* ]]

    # Read the commands that were executed
    local commands_called
    if [ -f "$DOCKER_COMMANDS_FILE" ]; then
        commands_called=$(cat "$DOCKER_COMMANDS_FILE")
        echo "Commands called: $commands_called" >&2
    fi

    # Verify swarm was initialized with correct IP
    [[ "$commands_called" == *"docker swarm init --advertise-addr 192.168.1.100"* ]]
    [[ "$commands_called" == *"docker swarm join-token -q worker"* ]]

    # Verify token was saved to file
    [ -f ".swarm_token" ]
    local token_content
    token_content=$(cat ".swarm_token")
    [ "$token_content" = "SWMTKN-1-test-token-12345" ]
}

@test "swarm_add_worker_node_should_join_node_to_swarm" {
    # Clear previous commands
    true > "$DOCKER_COMMANDS_FILE"

    # Change to test directory for relative file operations
    cd "$TEST_TEMP_DIR"

    # Create test machines.yml file
    cat > "machines.yml" <<EOF
machines:
  - host: manager.test.com
    role: manager
    ssh_user: manager_user
  - host: worker1.test.com
    role: worker
    ssh_user: worker_user
EOF

    # Create test token file
    echo "SWMTKN-1-test-worker-token-67890" > ".swarm_token"

    # Track SSH commands called
    export SSH_COMMANDS_FILE="${TEST_TEMP_DIR}/ssh_commands.log"
    true > "$SSH_COMMANDS_FILE"

    # Mock machines functions
    machines_parse() {
        local key=$1
        if [ "$key" = "manager" ]; then
            echo "manager.test.com"
        fi
    }

    machines_get_host_ip() {
        local host=$1
        case "$host" in
            "manager.test.com") echo "192.168.1.100" ;;
            "worker1.test.com") echo "192.168.1.101" ;;
        esac
    }

    machines_get_ssh_user() {
        local host=$1
        case "$host" in
            "manager.test.com") echo "manager_user" ;;
            "worker1.test.com") echo "worker_user" ;;
        esac
    }

    # Mock file wrapper functions
    file_read() {
        local file_path="$1"
        if [ "$file_path" = ".swarm_token" ]; then
            echo "SWMTKN-1-test-worker-token-67890"
        fi
    }

    # Mock SSH wrapper functions
    ssh_docker_command() {
        echo "ssh_docker_command $1 $2" >> "$SSH_COMMANDS_FILE"
        echo "SSH Docker command executed on $1: $2" >&2
        return 0
    }

    export -f machines_parse machines_get_host_ip machines_get_ssh_user file_read ssh_docker_command

    run swarm_add_worker_node "worker1.test.com"

    echo "Status: $status" >&2
    echo "Output: $output" >&2

    [ "$status" -eq 0 ]
    [[ "$output" == *"Joining node worker1.test.com to swarm"* ]]

    # Read the SSH commands that were executed
    local ssh_commands_called
    if [ -f "$SSH_COMMANDS_FILE" ]; then
        ssh_commands_called=$(cat "$SSH_COMMANDS_FILE")
        echo "SSH commands called: $ssh_commands_called" >&2
    fi

    # Verify the worker node was joined with correct token and manager IP
    [[ "$ssh_commands_called" == *"ssh_docker_command worker_user@worker1.test.com docker swarm join --token SWMTKN-1-test-worker-token-67890 192.168.1.100:2377"* ]]
}

@test "swarm_sync_should_add_missing_nodes" {
    # Clear previous commands
    true > "$DOCKER_COMMANDS_FILE"

    # Change to test directory for relative file operations
    cd "$TEST_TEMP_DIR"

    # Create test machines.yml file with manager and 2 workers
    cat > "machines.yml" <<EOF
machines:
  - host: manager.test.com
    role: manager
    ssh_user: manager_user
  - host: worker1.test.com
    role: worker
    ssh_user: worker1_user
  - host: worker2.test.com
    role: worker
    ssh_user: worker2_user
EOF

    # Track SSH commands called
    export SSH_COMMANDS_FILE="${TEST_TEMP_DIR}/ssh_commands.log"
    true > "$SSH_COMMANDS_FILE"

    # Mock current swarm state - only has worker1, missing worker2
    docker_node_list() {
        local format="${1:-{{.Hostname}}}"
        case "$format" in
            "{{.Hostname}}")
                # Return current nodes in swarm (manager + worker1)
                echo "manager.test.com"
                echo "worker1.test.com"
                ;;
        esac
    }

    # Mock grep command to properly filter out manager from node list and check node existence
    grep() {
        local args=("$@")
        if [[ "${args[0]}" == "-v" && "${args[1]}" == "manager.test.com" ]]; then
            # Filter out manager.test.com, leaving only worker1.test.com
            echo "worker1.test.com"
        elif [[ "${args[0]}" == "-q" ]]; then
            # Check if node exists in swarm - worker1 exists, worker2 doesn't
            local search_term="${args[1]}"
            case "$search_term" in
                "worker1.test.com") return 0 ;;  # Found
                "worker2.test.com") return 1 ;;  # Not found
                *) return 1 ;;
            esac
        else
            # Fall back to system grep for other cases
            command grep "$@"
        fi
    }

    # Mock machines functions
    machines_parse() {
        local key=$1
        case "$key" in
            "manager") echo "manager.test.com" ;;
            "workers") echo "worker1.test.com worker2.test.com" ;;
        esac
    }

    machines_get_host_ip() {
        local host=$1
        case "$host" in
            "manager.test.com") echo "192.168.1.100" ;;
            "worker1.test.com") echo "192.168.1.101" ;;
            "worker2.test.com") echo "192.168.1.102" ;;
        esac
    }

    machines_get_ssh_user() {
        local host=$1
        case "$host" in
            "manager.test.com") echo "manager_user" ;;
            "worker1.test.com") echo "worker1_user" ;;
            "worker2.test.com") echo "worker2_user" ;;
        esac
    }

    # Mock file_read for .swarm_token
    file_read() {
        local file_path="$1"
        if [ "$file_path" = ".swarm_token" ]; then
            echo "SWMTKN-1-test-add-token-99999"
        fi
    }

    # Mock ssh_docker_command to track calls
    ssh_docker_command() {
        echo "ssh_docker_command $1 $2" >> "$SSH_COMMANDS_FILE"
        echo "SSH Docker command executed on $1: $2" >&2
        return 0
    }

    # Mock swarm_add_worker_node to track calls
    swarm_add_worker_node() {
        echo "swarm_add_worker_node $1" >> "$DOCKER_COMMANDS_FILE"
        echo "Adding worker node: $1" >&2
        return 0
    }

    # Mock docker_node_inspect and other node operations (not used in this test)
    docker_node_inspect() { echo ""; }
    docker_node_update_label() { return 0; }
    swarm_display_status() { echo "Display status called"; }

    export -f docker_node_list grep machines_parse machines_get_host_ip machines_get_ssh_user
    export -f file_read ssh_docker_command swarm_add_worker_node
    export -f docker_node_inspect docker_node_update_label swarm_display_status

    run swarm_sync_nodes

    echo "Status: $status" >&2
    echo "Output: $output" >&2

    [ "$status" -eq 0 ]
    [[ "$output" == *"Syncing swarm nodes with machines.yml configuration"* ]]
    [[ "$output" == *"Adding new node worker2.test.com to swarm"* ]]

    # Read the commands that were executed
    local commands_called
    if [ -f "$DOCKER_COMMANDS_FILE" ]; then
        commands_called=$(cat "$DOCKER_COMMANDS_FILE")
        echo "Commands called: $commands_called" >&2
    fi

    # Verify that worker2 was added (worker1 already exists, so shouldn't be added)
    [[ "$commands_called" == *"swarm_add_worker_node worker2.test.com"* ]]
    [[ "$commands_called" != *"swarm_add_worker_node worker1.test.com"* ]]
}

@test "swarm_sync_should_remove_extra_nodes" {
    # Clear previous commands
    true > "$DOCKER_COMMANDS_FILE"

    # Change to test directory for relative file operations
    cd "$TEST_TEMP_DIR"

    # Create test machines.yml file with manager and only 1 worker
    cat > "machines.yml" <<EOF
machines:
  - host: manager.test.com
    role: manager
    ssh_user: manager_user
  - host: worker1.test.com
    role: worker
    ssh_user: worker1_user
EOF

    # Track SSH commands called
    export SSH_COMMANDS_FILE="${TEST_TEMP_DIR}/ssh_commands.log"
    true > "$SSH_COMMANDS_FILE"

    # Mock current swarm state - has both worker1 and worker2, but config only wants worker1
    docker_node_list() {
        local format="${1:-{{.Hostname}}}"
        case "$format" in
            "{{.Hostname}}")
                # Return current nodes in swarm (manager + worker1 + worker2)
                echo "manager.test.com"
                echo "worker1.test.com"
                echo "worker2.test.com"
                ;;
        esac
    }

    # Mock grep command to properly filter out manager and check node existence
    grep() {
        local args=("$@")
        if [[ "${args[0]}" == "-v" && "${args[1]}" == "manager.test.com" ]]; then
            # Filter out manager.test.com, leaving worker1 and worker2
            echo "worker1.test.com"
            echo "worker2.test.com"
        elif [[ "${args[0]}" == "-q" ]]; then
            # Check if node exists in desired list
            local search_term="${args[1]}"
            local desired_list="worker1.test.com"
            echo "$desired_list" | command grep -q "$search_term"
        else
            # Fall back to system grep for other cases
            command grep "$@"
        fi
    }

    # Mock machines functions
    machines_parse() {
        local key=$1
        case "$key" in
            "manager") echo "manager.test.com" ;;
            "workers") echo "worker1.test.com" ;;  # Only worker1 is desired
        esac
    }

    machines_get_ssh_user() {
        local host=$1
        case "$host" in
            "worker1.test.com") echo "worker1_user" ;;
            "worker2.test.com") echo "worker2_user" ;;
        esac
    }

    # Mock docker wrapper functions for node removal
    docker_node_update_availability() {
        echo "docker_node_update_availability $1 $2" >> "$DOCKER_COMMANDS_FILE"
        echo "Node $2 availability set to $1" >&2
        return 0
    }

    docker_node_remove() {
        echo "docker_node_remove $1 $2" >> "$DOCKER_COMMANDS_FILE"
        echo "Node $1 removed with flags $2" >&2
        return 0
    }

    # Mock ssh_docker_command to track calls
    ssh_docker_command() {
        echo "ssh_docker_command $1 $2" >> "$SSH_COMMANDS_FILE"
        echo "SSH Docker command executed on $1: $2" >&2
        return 0
    }

    # Mock sleep to speed up test
    sleep() {
        echo "sleep $1" >> "$DOCKER_COMMANDS_FILE"
        return 0
    }

    # Mock other functions not used in removal test
    swarm_add_worker_node() { return 0; }
    docker_node_inspect() { echo ""; }
    docker_node_update_label() { return 0; }
    swarm_display_status() { echo "Display status called"; }

    export -f docker_node_list grep machines_parse machines_get_ssh_user
    export -f docker_node_update_availability docker_node_remove ssh_docker_command sleep
    export -f swarm_add_worker_node docker_node_inspect docker_node_update_label swarm_display_status

    run swarm_sync_nodes

    echo "Status: $status" >&2
    echo "Output: $output" >&2

    [ "$status" -eq 0 ]
    [[ "$output" == *"Syncing swarm nodes with machines.yml configuration"* ]]
    [[ "$output" == *"Removing node worker2.test.com from swarm"* ]]

    # Read the commands that were executed
    local commands_called
    if [ -f "$DOCKER_COMMANDS_FILE" ]; then
        commands_called=$(cat "$DOCKER_COMMANDS_FILE")
        echo "Commands called: $commands_called" >&2
    fi

    # Read the SSH commands that were executed
    local ssh_commands_called
    if [ -f "$SSH_COMMANDS_FILE" ]; then
        ssh_commands_called=$(cat "$SSH_COMMANDS_FILE")
        echo "SSH commands called: $ssh_commands_called" >&2
    fi

    # Verify that worker2 was removed (drain, remove, leave)
    [[ "$commands_called" == *"docker_node_update_availability drain worker2.test.com"* ]]
    [[ "$commands_called" == *"sleep 5"* ]]
    [[ "$commands_called" == *"docker_node_remove worker2.test.com --force"* ]]
    [[ "$ssh_commands_called" == *"ssh_docker_command worker2_user@worker2.test.com docker swarm leave --force"* ]]
}

@test "swarm_sync_should_update_node_labels" {
    # Clear previous commands
    true > "$DOCKER_COMMANDS_FILE"

    # Change to test directory for relative file operations
    cd "$TEST_TEMP_DIR"

    # Create test machines.yml file with workers that have labels
    cat > "machines.yml" <<EOF
machines:
  - host: manager.test.com
    role: manager
    ssh_user: manager_user
  - host: worker1.test.com
    role: worker
    ssh_user: worker1_user
    labels:
      - storage=ssd
      - env=production
  - host: worker2.test.com
    role: worker
    ssh_user: worker2_user
    labels:
      - storage=hdd
      - env=staging
EOF

    # Mock current swarm state - both workers exist, no extra nodes
    docker_node_list() {
        local format="${1:-{{.Hostname}}}"
        case "$format" in
            "{{.Hostname}}")
                echo "manager.test.com"
                echo "worker1.test.com"
                echo "worker2.test.com"
                ;;
        esac
    }

    # Mock grep command
    grep() {
        local args=("$@")
        if [[ "${args[0]}" == "-v" && "${args[1]}" == "manager.test.com" ]]; then
            # Filter out manager.test.com
            echo "worker1.test.com"
            echo "worker2.test.com"
        elif [[ "${args[0]}" == "-q" ]]; then
            # All nodes exist, so return success
            return 0
        else
            command grep "$@"
        fi
    }

    # Mock machines functions
    machines_parse() {
        local key=$1
        case "$key" in
            "manager") echo "manager.test.com" ;;
            "workers") echo "worker1.test.com worker2.test.com" ;;
            ".workers[] | select(.host == \"worker1.test.com\") | .labels") echo "storage=ssd env=production" ;;
            ".workers[] | select(.host == \"worker2.test.com\") | .labels") echo "storage=hdd env=staging" ;;
        esac
    }

    # Mock docker_node_inspect to return existing labels that need to be removed
    docker_node_inspect() {
        local node="$1"
        local format="$2"
        case "$node:$format" in
            "worker1.test.com:{{range \$k,\$v := .Spec.Labels}}{{\$k}}{{end}}")
                echo "old_label1 old_label2"
                ;;
            "worker2.test.com:{{range \$k,\$v := .Spec.Labels}}{{\$k}}{{end}}")
                echo "old_label3"
                ;;
        esac
    }

    # Mock docker_node_update_label to track label operations
    docker_node_update_label() {
        echo "docker_node_update_label $1 $2 $3" >> "$DOCKER_COMMANDS_FILE"
        echo "Label operation: $1 $2 on node $3" >&2
        return 0
    }

    # Mock other functions not used in this test
    docker_node_update_availability() { return 0; }
    docker_node_remove() { return 0; }
    ssh_docker_command() { return 0; }
    swarm_add_worker_node() { return 0; }
    swarm_display_status() { echo "Display status called"; }

    export -f docker_node_list grep machines_parse docker_node_inspect docker_node_update_label
    export -f docker_node_update_availability docker_node_remove ssh_docker_command
    export -f swarm_add_worker_node swarm_display_status

    run swarm_sync_nodes

    echo "Status: $status" >&2
    echo "Output: $output" >&2

    [ "$status" -eq 0 ]
    [[ "$output" == *"Updating labels for node worker1.test.com"* ]]
    [[ "$output" == *"Updating labels for node worker2.test.com"* ]]

    # Read the commands that were executed
    local commands_called
    if [ -f "$DOCKER_COMMANDS_FILE" ]; then
        commands_called=$(cat "$DOCKER_COMMANDS_FILE")
        echo "Commands called: $commands_called" >&2
    fi

    # Verify that old labels were removed and new labels were added for worker1
    [[ "$commands_called" == *"docker_node_update_label --label-rm old_label1 worker1.test.com"* ]]
    [[ "$commands_called" == *"docker_node_update_label --label-rm old_label2 worker1.test.com"* ]]
    [[ "$commands_called" == *"docker_node_update_label --label-add storage=ssd worker1.test.com"* ]]
    [[ "$commands_called" == *"docker_node_update_label --label-add env=production worker1.test.com"* ]]

    # Verify that old labels were removed and new labels were added for worker2
    [[ "$commands_called" == *"docker_node_update_label --label-rm old_label3 worker2.test.com"* ]]
    [[ "$commands_called" == *"docker_node_update_label --label-add storage=hdd worker2.test.com"* ]]
    [[ "$commands_called" == *"docker_node_update_label --label-add env=staging worker2.test.com"* ]]
}

@test "swarm_display_status_should_show_nodes_and_services" {
    # Clear previous commands
    true > "$DOCKER_COMMANDS_FILE"

    # Change to test directory for relative file operations
    cd "$TEST_TEMP_DIR"

    # Mock docker wrapper functions to track what's called
    docker_node_list() {
        echo "docker_node_list" >> "$DOCKER_COMMANDS_FILE"
        echo "HOSTNAME    STATUS    AVAILABILITY   MANAGER STATUS"
        echo "manager     Ready     Active         Leader"
        echo "worker1     Ready     Active"
        echo "worker2     Ready     Active"
        return 0
    }

    docker_service_list() {
        echo "docker_service_list" >> "$DOCKER_COMMANDS_FILE"
        echo "ID       NAME        MODE         REPLICAS"
        echo "abc123   nginx       replicated   2/2"
        echo "def456   redis       replicated   1/1"
        return 0
    }

    export -f docker_node_list docker_service_list

    run swarm_display_status

    echo "Status: $status" >&2
    echo "Output: $output" >&2

    [ "$status" -eq 0 ]
    [[ "$output" == *"Swarm Nodes:"* ]]
    [[ "$output" == *"HOSTNAME    STATUS    AVAILABILITY   MANAGER STATUS"* ]]
    [[ "$output" == *"manager     Ready     Active         Leader"* ]]
    [[ "$output" == *"worker1     Ready     Active"* ]]
    [[ "$output" == *"worker2     Ready     Active"* ]]
    [[ "$output" == *"Swarm Services:"* ]]
    [[ "$output" == *"ID       NAME        MODE         REPLICAS"* ]]
    [[ "$output" == *"nginx       replicated   2/2"* ]]
    [[ "$output" == *"redis       replicated   1/1"* ]]

    # Read the commands that were executed
    local commands_called
    if [ -f "$DOCKER_COMMANDS_FILE" ]; then
        commands_called=$(cat "$DOCKER_COMMANDS_FILE")
        echo "Commands called: $commands_called" >&2
    fi

    # Verify both docker commands were called
    [[ "$commands_called" == *"docker_node_list"* ]]
    [[ "$commands_called" == *"docker_service_list"* ]]
}
