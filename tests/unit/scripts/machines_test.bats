#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export PROJECT_ROOT="${TEST_TEMP_DIR}"

    # Create test machines.yml file with new format
    cat > "${TEST_TEMP_DIR}/machines.yml" <<EOF
machines:
  - host: manager.example.com
    role: manager
    ssh_user: admin1

  - host: worker1.example.com
    role: worker
    ssh_user: admin2
    labels:
      storage: ssd

  - host: worker2.example.com
    role: worker
    ssh_user: admin3
    labels:
      storage: hdd
EOF

    # Source the machines script with mocked functions
    source "${BATS_TEST_DIRNAME}/../../../scripts/machines.sh"

    # Mock getent to return test IPs
    getent() {
        case "$2" in
            "manager.example.com") echo "10.0.0.1 manager.example.com" ;;
            "worker2.example.com") echo "10.0.0.3 worker2.example.com" ;;
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
    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yml"

    run machines_parse 'manager'
    echo "output: $output"
    [ "$status" -eq 0 ]
    [ "$output" = "manager.example.com" ]

    run machines_parse 'workers'
    echo "output: $output"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "worker1.example.com worker2.example.com" ]]
}

@test "machines_parse handles missing file" {
    MACHINES_FILE="/nonexistent/path/machines.yml"
    run machines_parse 'manager'
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Error" ]]  # Should have error message
}

@test "machines_parse handles invalid yaml" {
    # create invalid yaml file
    cat > "${TEST_TEMP_DIR}/machines.yml" <<EOF
machines:
  - host: manager.example.com
    role: manager
    invalid_yaml: [
EOF
    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yml"
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
    [[ "$output" =~ "Error: Invalid IP address" ]]
}

@test "machines_get_host_ip fails on unresolvable host" {
    run machines_get_host_ip "nonexistent.example.com"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Error: Could not resolve IP for host" ]]
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
    [[ "$output" =~ "Setting up SSH access for manager.example.com" ]]
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
    [[ "$output" =~ "Testing connection to worker1.example.com" ]]
    [[ "$output" =~ "✓ Successfully connected to worker1.example.com" ]]
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
    [[ "$output" =~ "Testing connection to worker1.example.com" ]]
    [[ "$output" =~ "✗ Failed to connect to worker1.example.com" ]]
}

@test "machines_get_ssh_user gets user for host" {
    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yml"

    run machines_get_ssh_user "manager.example.com"
    [ "$status" -eq 0 ]
    [ "$output" = "admin1" ]

    run machines_get_ssh_user "worker1.example.com"
    [ "$status" -eq 0 ]
    [ "$output" = "admin2" ]

    run machines_get_ssh_user "worker2.example.com"
    [ "$status" -eq 0 ]
    [ "$output" = "admin3" ]
}

@test "machines_get_ssh_user handles missing user" {
    # Create test machines.yml without SSH users
    cat > "${TEST_TEMP_DIR}/machines.yml" <<EOF
machines:
  - host: manager.example.com
    role: manager
  - host: worker1.example.com
    role: worker
EOF

    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yml"

    run machines_get_ssh_user "manager.example.com"
    [ "$status" -eq 0 ]
    [ "$output" = "null" ]  # yq returns "null" for missing fields
}

@test "machines_get_ssh_user handles invalid host" {
    MACHINES_FILE="${TEST_TEMP_DIR}/machines.yml"

    run machines_get_ssh_user "nonexistent"
    [ "$status" -eq 0 ]
    [ "$output" = "null" ]
}

@test "machines_get_ssh_user handles missing file" {
    MACHINES_FILE="/nonexistent/path/machines.yml"

    run machines_get_ssh_user "manager"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Error" ]]
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
    [[ "$output" =~ "Setting up SSH access for manager.example.com" ]]
    [[ "$output" =~ "Successfully set up SSH access for manager.example.com" ]]
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
    [[ "$output" =~ "Skipping SSH setup for local machine: manager.example.com" ]]
    [[ "$output" =~ "Setting up SSH access for worker1.example.com" ]]
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
            "worker1.example.com") return 0 ;;  # Already configured
            "worker2.example.com") return 1 ;;  # Needs setup
            "manager.example.com") return 1 ;;  # Needs setup
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
    [[ "$output" =~ "Skipping SSH setup for already configured host: worker1.example.com" ]]
    [[ "$output" =~ "Setting up SSH access for worker2.example.com" ]]
    [[ "$output" =~ "Setting up SSH access for manager.example.com" ]]
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
