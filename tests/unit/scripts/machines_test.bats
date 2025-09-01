#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export PROJECT_ROOT="${TEST_TEMP_DIR}"

    # Create test machines.yaml file with new simplified format
    cat > "${TEST_TEMP_DIR}/machines.yaml" <<EOF
machines:
  manager:
    ip: 10.0.0.1
    role: manager
    ssh_user: admin1

  worker1:
    ip: 10.0.0.2
    role: worker
    ssh_user: admin2
    labels:
      storage: ssd

  worker2:
    ip: 10.0.0.3
    role: worker
    ssh_user: admin3
    labels:
      storage: hdd
EOF

    # Source the machines script with mocked functions
    source "${BATS_TEST_DIRNAME}/../../../scripts/machines.sh"

    # Mock getent to return test IPs for hostnames built from machine keys
    export BASE_DOMAIN="example.com"
    getent() {
        case "$2" in
            "manager.example.com") echo "10.0.0.1 manager.example.com" ;;
            "worker1.example.com") echo "10.0.0.2 worker1.example.com" ;;
            "worker2.example.com") echo "10.0.0.3 worker2.example.com" ;;
            "node-02.diyhub.dev") echo "10.0.0.3 node-02.diyhub.dev" ;;
            *) return 1 ;;
        esac
    }

    # Mock ssh-copy-id to always succeed
    ssh-copy-id() {
        return 0
    }
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "machines_parse reads yaml correctly" {
    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yaml"

    run machines_parse 'manager'
    echo "output: $output"
    [ "$status" -eq 0 ]
    [ "$output" = "manager" ]

    run machines_parse 'workers'
    echo "output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "worker1 worker2" ]]
}

@test "machines_parse handles missing file" {
    MACHINES_FILE="/nonexistent/path/machines.yaml"
    run machines_parse 'manager'
    [ "$status" -eq 1 ]
    [[ "$output" =~ "ERROR" ]]  # Should have error message
}

@test "machines_parse handles invalid yaml" {
    # create invalid yaml file
    cat > "${TEST_TEMP_DIR}/machines.yaml" <<EOF
machines:
  - host: manager.example.com
    role: manager
    invalid_yaml: [
EOF
    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yaml"
    run machines_parse 'manager'
    echo "output: $output"
    echo "status: $status"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Error" ]]
}

@test "machines_get_host_ip resolves hostname to IP" {
    run machines_get_host_ip "manager.example.com"
    [ "$status" -eq 0 ]
    [ "$output" = "10.0.0.1" ]
}

@test "machines_get_host_ip returns IP if given IP" {
    run machines_get_host_ip "192.168.1.101"
    [ "$status" -eq 0 ]
    [ "$output" = "192.168.1.101" ]
}

@test "machines_get_host_ip handles invalid IP format" {
    run machines_get_host_ip "256.256.256.256"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Invalid IP address" ]]
}

@test "machines_get_host_ip fails on unresolvable host" {
    run machines_get_host_ip "nonexistent.example.com"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Could not resolve IP for host" ]]
}

@test "machines_setup_ssh attempts to setup all hosts" {
    # Mock commands
    ssh() {
        echo "SSH: $*" >&2
        return 0
    }

    ssh-copy-id() {
        echo "Copying key: $*" >&2
        return 0
    }

    timeout() {
        "${@:2}"
    }

    # Mock machines_is_ssh_configured to return "not configured" for all hosts
    machines_is_ssh_configured() {
        return 1
    }

    export -f ssh ssh-copy-id timeout machines_is_ssh_configured

    run machines_setup_ssh
    echo "output: $output" >&2
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Setting up SSH access for manager (10.0.0.1)" ]]
}

@test "machines_setup_ssh handles ssh-copy-id failure" {
    ssh() {
        return 0
    }

    ssh-copy-id() {
        echo "Failed to copy key" >&2
        return 1
    }

    export -f ssh ssh-copy-id

    run machines_setup_ssh
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Failed to copy SSH key" ]]
}

@test "machines_test_connection checks all hosts" {
    # Mock SSH wrappers and timeout
    ssh_key_auth() {
        echo "SSH key auth called with args: $*" >&2
        return 0
    }

    timeout() {
        "${@:2}"
    }

    export -f ssh_key_auth timeout

    run machines_test_connection
    echo "output: $output" >&2
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Testing connection to worker1 (10.0.0.2)" ]]
    [[ "$output" =~ "✓ Successfully connected to worker1 (10.0.0.2)" ]]
}

@test "machines_test_connection shows failure for failed connections" {
    ssh_key_auth() {
        echo "SSH key auth called with args: $*" >&2
        return 1
    }

    timeout() {
        "${@:2}"
    }

    export -f ssh_key_auth timeout

    run machines_test_connection
    echo "output: $output" >&2
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Testing connection to worker1 (10.0.0.2)" ]]
    [[ "$output" =~ "✗ Failed to connect to worker1 (10.0.0.2)" ]]
}

@test "machines_get_ssh_user gets user for machine key" {
    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yaml"

    run machines_get_ssh_user "manager"
    [ "$status" -eq 0 ]
    [ "$output" = "admin1" ]

    run machines_get_ssh_user "worker1"
    [ "$status" -eq 0 ]
    [ "$output" = "admin2" ]

    run machines_get_ssh_user "worker2"
    [ "$status" -eq 0 ]
    [ "$output" = "admin3" ]
}

@test "machines_get_ssh_user handles missing user" {
    # Create test machines.yaml without SSH users
    cat > "${TEST_TEMP_DIR}/machines.yaml" <<EOF
machines:
  manager:
    role: manager
  worker1:
    role: worker
EOF

    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yaml"

    run machines_get_ssh_user "manager"
    [ "$status" -eq 0 ]
    [ "$output" = "null" ]  # yq returns "null" for missing fields
}

@test "machines_get_ssh_user handles invalid host" {
    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yaml"

    run machines_get_ssh_user "nonexistent"
    [ "$status" -eq 0 ]
    [ "$output" = "null" ]
}

@test "machines_get_ssh_user handles missing file" {
    MACHINES_FILE="/nonexistent/path/machines.yaml"

    run machines_get_ssh_user "manager"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "ERROR" ]]
}

@test "machines_setup_ssh handles permissions" {
    # Mock all SSH-related commands
    chmod() {
        echo "Setting permissions $1 on $2" >&2
        return 0
    }

    ssh_password_auth() {
        echo "Password auth called with args: $*" >&2
        return 0
    }

    ssh_key_auth() {
        echo "Key auth called with args: $*" >&2
        return 0
    }

    ssh_copy_id() {
        echo "Copy ID called with args: $*" >&2
        return 0
    }

    timeout() {
        "${@:2}"
    }

    # Mock machines_is_ssh_configured to return "not configured" for all hosts
    machines_is_ssh_configured() {
        return 1
    }

    export -f chmod ssh_password_auth ssh_key_auth ssh_copy_id timeout machines_is_ssh_configured

    run machines_setup_ssh
    echo "Output: $output" >&2
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Setting up SSH access for manager (10.0.0.1)" ]]
    [[ "$output" =~ "Successfully set up SSH access for manager (10.0.0.1)" ]]
}

@test "machines_setup_ssh skips local machine" {
    # Mock hostname to return one of our test hosts
    hostname() {
        echo "manager.example.com"
    }
    export -f hostname

    machines_my_ip() {
        echo "10.0.0.1"
    }
    export -f machines_my_ip

    # Mock machines_get_host_ip to handle IP resolution
    machines_get_host_ip() {
        case "$1" in
            "manager.example.com") echo "10.0.0.1" ;;
            "worker1.example.com") echo "10.0.0.2" ;;
            "worker2.example.com") echo "10.0.0.3" ;;
            *) return 1 ;;
        esac
    }
    export -f machines_get_host_ip

    # Mock other commands
    ssh() {
        echo "SSH: $*" >&2
        return 0
    }

    ssh-copy-id() {
        echo "Copying key: $*" >&2
        return 0
    }

    timeout() {
        "${@:2}"
    }

    # Mock machines_is_ssh_configured to return "not configured" for all hosts
    machines_is_ssh_configured() {
        return 1
    }

    export -f ssh ssh-copy-id timeout machines_is_ssh_configured

    run machines_setup_ssh
    echo "Output: $output" >&2

    [ "$status" -eq 0 ]
    [[ "$output" =~ "Skipping SSH setup for local machine: manager (10.0.0.1)" ]]
    [[ "$output" =~ "Setting up SSH access for worker1 (10.0.0.2)" ]]
}

@test "machines_is_ssh_configured returns true when SSH key auth works" {
    ssh_key_auth() {
        echo "SSH key auth successful" >&2
        return 0
    }

    timeout() {
        "${@:2}"
    }

    export -f ssh_key_auth timeout

    run machines_is_ssh_configured "worker1.example.com" "admin2"
    echo "Output: $output" >&2
    [ "$status" -eq 0 ]
}

@test "machines_is_ssh_configured returns false when SSH key auth fails" {
    ssh_key_auth() {
        echo "SSH key auth failed" >&2
        return 1
    }

    timeout() {
        "${@:2}"
    }

    export -f ssh_key_auth timeout

    run machines_is_ssh_configured "worker1.example.com" "admin2"
    echo "Output: $output" >&2
    [ "$status" -eq 1 ]
}

@test "machines_setup_ssh skips hosts that are already configured" {
    # Mock machines_is_ssh_configured to return success for worker1, failure for worker2
    machines_is_ssh_configured() {
        case "$1" in
            "10.0.0.2") return 0 ;;  # worker1 - Already configured
            "10.0.0.3") return 1 ;;  # worker2 - Needs setup
            "10.0.0.1") return 1 ;;  # manager - Needs setup
            *) return 1 ;;
        esac
    }

    # Mock other SSH-related commands
    ssh_password_auth() {
        echo "Password auth called with args: $*" >&2
        return 0
    }

    ssh_key_auth() {
        echo "Key auth called with args: $*" >&2
        return 0
    }

    ssh_copy_id() {
        echo "Copy ID called with args: $*" >&2
        return 0
    }

    timeout() {
        "${@:2}"
    }

    export -f machines_is_ssh_configured ssh_password_auth ssh_key_auth ssh_copy_id timeout

    run machines_setup_ssh
    echo "Output: $output" >&2
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Skipping SSH setup for already configured machine: worker1 (10.0.0.2)" ]]
    [[ "$output" =~ "Setting up SSH access for worker2 (10.0.0.3)" ]]
    [[ "$output" =~ "Setting up SSH access for manager (10.0.0.1)" ]]
}

@test "machines_is_ssh_configured should allow debug mode" {
    # Mock ssh_key_auth to fail but show what command was attempted
    ssh_key_auth() {
        echo "SSH Key Auth attempted with: $*" >&2
        return 1
    }

    timeout() {
        echo "Timeout called with: $*" >&2
        "${@:2}"
    }

    export -f ssh_key_auth timeout

    # Test that when we add a debug parameter, we can see the SSH attempts
    run machines_is_ssh_configured "test.example.com" "testuser" "debug"
    echo "Status: $status" >&2
    echo "Output: $output" >&2
    [ "$status" -eq 1 ]
    [[ "$output" =~ "SSH Key Auth attempted with: testuser@test.example.com exit" ]]
}

@test "ssh functions should be available after sourcing ssh.sh" {
    # Test that sourcing ssh.sh makes functions available
    run bash -c "source scripts/ssh.sh 2>/dev/null && type ssh_key_auth"
    echo "Output: $output" >&2
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ssh_key_auth is a function" ]]
}

@test "machines_is_ssh_configured should work without timeout when SSH is configured" {
    # Mock ssh_key_auth to succeed
    ssh_key_auth() {
        echo "SSH Key Auth successful" >&2
        return 0
    }

    export -f ssh_key_auth

    # Test without timeout to verify our logic works
    run machines_is_ssh_configured_no_timeout "test.example.com" "testuser"
    echo "Output: $output" >&2
    [ "$status" -eq 0 ]
}

@test "machines_build_hostname constructs hostname from machine key" {
    BASE_DOMAIN="diyhub.dev"
    export BASE_DOMAIN

    run machines_build_hostname "manager"
    [ "$status" -eq 0 ]
    [ "$output" = "manager.diyhub.dev" ]

    run machines_build_hostname "node-01"
    [ "$status" -eq 0 ]
    [ "$output" = "node-01.diyhub.dev" ]

    run machines_build_hostname "nas"
    [ "$status" -eq 0 ]
    [ "$output" = "nas.diyhub.dev" ]
}

@test "machines_get_ip should work with simplified machine key structure" {
    # Create simplified machines.yaml structure (no host field)
    cat > "${TEST_TEMP_DIR}/machines.yaml" <<EOF
machines:
  manager:
    ip: 192.168.1.100
    user: admin
  node-01:
    ip: 192.168.1.101
    user: deploy
  node-02:
    user: deploy
    # No IP field - should fall back to hostname resolution
EOF

    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yaml"
    BASE_DOMAIN="diyhub.dev"
    export BASE_DOMAIN

    # Test IP field is used when present for machine key
    run machines_get_ip "manager"
    [ "$status" -eq 0 ]
    [ "$output" = "192.168.1.100" ]

    # Test IP field is used when present for machine key
    run machines_get_ip "node-01"
    [ "$status" -eq 0 ]
    [ "$output" = "192.168.1.101" ]

    # Test fallback to hostname resolution when IP field missing
    # Should resolve node-02.diyhub.dev via DNS
    run machines_get_ip "node-02"
    [ "$status" -eq 0 ]
    [ "$output" = "10.0.0.3" ]  # From mocked getent for constructed hostname
}

@test "machines_setup_ssh should use IP addresses not hostnames" {
    # RED: This test should fail initially because current code uses hostnames
    # Mock commands to verify IP addresses are used
    ssh_password_auth() {
        echo "SSH password auth called with: $1" >&2
        # Verify the connection string uses IP address not hostname
        [[ "$1" =~ ^[a-zA-Z0-9_]+@[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]
        return 0
    }

    ssh_copy_id() {
        echo "SSH copy ID called with: $1" >&2
        # Verify the connection string uses IP address not hostname
        [[ "$1" =~ ^[a-zA-Z0-9_]+@[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]
        return 0
    }

    ssh_key_auth() {
        local target="$1"
        echo "SSH key auth called with: $target" >&2
        # Verify the connection string uses IP address not hostname
        [[ "$target" =~ ^[a-zA-Z0-9_]+@[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]
        return 0
    }

    timeout() {
        "${@:2}"
    }

    # Mock machines_is_ssh_configured to return "not configured" for all
    machines_is_ssh_configured() {
        return 1
    }

    export -f ssh_password_auth ssh_copy_id ssh_key_auth timeout machines_is_ssh_configured

    # This test should verify that all SSH operations use IPs not hostnames
    run machines_setup_ssh
    [ "$status" -eq 0 ]

    # GREEN: Verify the output mentions IP addresses, not hostnames
    [[ "$output" =~ "Setting up SSH access for worker1 (10.0.0.2)" ]]
    [[ "$output" =~ "Setting up SSH access for worker2 (10.0.0.3)" ]]
    # Should NOT contain hostname references in connection attempts
    [[ ! "$output" =~ "worker1.example.com" ]]
    [[ ! "$output" =~ "worker2.example.com" ]]
}

@test "machines_get_ip can find machine by role" {
    # Create a machines.yaml where the manager is not keyed by "manager"
    cat > "${PROJECT_ROOT}/machines.yaml" <<EOF
machines:
  main-server:
    ip: 10.0.0.99
    role: manager
  worker-bee:
    ip: 10.0.0.2
    role: worker
EOF

    MACHINES_FILE="${PROJECT_ROOT}/machines.yaml"

    # This should fail because machines_get_ip looks for a key "manager"
    # instead of looking for a machine with the role "manager".
    run machines_get_ip "manager"
    [ "$status" -eq 0 ]
    [ "$output" = "10.0.0.99" ]
}
