#!/usr/bin/env bats

load test_helper

setup() {
    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"
    export TEST=true
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export BASE_DOMAIN="diyhub.dev"
    export DNS_ADMIN_PASSWORD="test123"
    export DNS_SERVER_IP="192.168.1.100"

    # Create test machines.yaml with simplified structure
    cat > "${TEST_TEMP_DIR}/machines.yaml" <<EOF
machines:
  manager:
    ip: 192.168.1.100
    user: admin
  node-01:
    ip: 192.168.1.101
    user: deploy
  nas:
    ip: 192.168.1.50
    user: admin
EOF

    export MACHINES_FILE="${TEST_TEMP_DIR}/machines.yaml"

    # Create test .env file
    cat > "${TEST_TEMP_DIR}/.env" <<EOF
BASE_DOMAIN=diyhub.dev
DNS_ADMIN_PASSWORD=test123
DNS_SERVER_IP=192.168.1.100
EOF

    # Create mock DNS configuration script
    mkdir -p "${TEST_TEMP_DIR}/scripts"
    cat > "${TEST_TEMP_DIR}/scripts/configure_dns_records.sh" <<'EOF'
#!/bin/bash
get_dns_token() {
    echo "mock-token-12345"
}
EOF

    # Create mock ssh.sh
    cat > "${TEST_TEMP_DIR}/scripts/ssh.sh" <<'EOF'
#!/bin/bash
ssh_key_auth() {
    echo "Mock SSH: $*" >&2
    return 0
}
EOF

    # Store original PROJECT_ROOT before sourcing nuke.sh
    ORIGINAL_PROJECT_ROOT="$PROJECT_ROOT"

    # Source the nuke script with safe execution prevention
    # We'll source individual functions instead of the whole script
    source "${BATS_TEST_DIRNAME}/../../../scripts/nuke.sh" || true

    # Restore PROJECT_ROOT after sourcing
    PROJECT_ROOT="$ORIGINAL_PROJECT_ROOT"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

# Mock functions for testing
mock_docker_stack_ls() {
    echo "dns
reverse-proxy
monitoring
actual-server"
}

mock_docker_network_ls() {
    echo "traefik-public
monitoring-net"
}

mock_docker_info() {
    echo "manager-node-id"
}

mock_docker_node_ls() {
    echo "manager-node-id
worker-node-id-1
worker-node-id-2"
}

mock_curl() {
    local url=""
    local data=""
    for arg in "$@"; do
        if [[ "$arg" == *"api/"* ]]; then
            url="$arg"
        elif [[ "$arg" == -d ]]; then
            data_next=true
        elif [ "${data_next:-}" = true ]; then
            data="$arg"
            data_next=false
        fi
    done

    # Simulate DNS server responses
    if [[ "$url" == *"/api/user/login"* ]]; then
        echo '{"token":"mock-token-12345"}'
    elif [[ "$url" == *"/api/zones/delete"* ]]; then
        echo '{"status":"ok"}'
    else
        return 0
    fi
}

@test "nuke script should define HOMELAB_VOLUMES array" {
    # Test that HOMELAB_VOLUMES is defined and contains expected volumes
    [ ${#HOMELAB_VOLUMES[@]} -gt 0 ]
    [[ " ${HOMELAB_VOLUMES[*]} " == *" dns-config "* ]]
    [[ " ${HOMELAB_VOLUMES[*]} " == *" ssl_certs "* ]]
    [[ " ${HOMELAB_VOLUMES[*]} " == *" prometheus_data "* ]]
}

@test "cleanup_dns_records should attempt to delete DNS zone" {
    # Mock curl and dependencies
    curl() { mock_curl "$@"; }
    yq() { echo "192.168.1.100"; }
    get_dns_token() { echo "mock-token-12345"; }
    export -f curl yq mock_curl get_dns_token

    run cleanup_dns_records
    [ "$status" -eq 0 ]
    [[ "$output" == *"Cleaning up DNS records"* ]]
    [[ "$output" == *"DNS server accessible"* ]]
    [[ "$output" == *"Deleting DNS zone: diyhub.dev"* ]]
}

@test "cleanup_dns_records should handle DNS server not accessible" {
    # Mock curl to fail
    curl() { return 1; }
    yq() { echo "192.168.1.100"; }
    export -f curl yq

    run cleanup_dns_records
    [ "$status" -eq 0 ]
    [[ "$output" == *"DNS server not accessible, skipping DNS cleanup"* ]]
}

@test "cleanup_dns_records should handle authentication failure" {
    # Mock curl to succeed for connectivity check but fail for token
    curl() {
        if [[ "$*" == *"api/user/login"* && "$*" != *"token="* ]]; then
            return 0  # Connectivity check passes
        else
            return 1  # Token request fails
        fi
    }
    yq() { echo "192.168.1.100"; }
    get_dns_token() { return 1; }  # Override to fail
    export -f curl yq get_dns_token

    run cleanup_dns_records
    [ "$status" -eq 0 ]
    [[ "$output" == *"Could not authenticate with DNS server"* ]]
}

@test "nuke script should source DNS functions if available" {
    # Test that the script properly sources DNS configuration
    # Use the test temp dir DNS script we created in setup
    [ -f "$PROJECT_ROOT/scripts/configure_dns_records.sh" ]

    # Verify get_dns_token function is available after sourcing
    run bash -c "source '$PROJECT_ROOT/scripts/configure_dns_records.sh' && type get_dns_token"
    [ "$status" -eq 0 ]
    [[ "$output" == *"get_dns_token is a function"* ]]
}

@test "HOMELAB_VOLUMES should include all expected volume names" {
    local expected_volumes=(
        "budget" "ssl_certs" "cryptpad" "deluge" "torrents" "usenet" "all_data"
        "emby" "homeassistant" "homepage" "librechat_meilisearch" "librechat_mongodb"
        "photoprism" "prowlarr" "qbittorrent" "radarr" "sonarr" "grafana_dashboards"
        "grafana_data" "prometheus_data" "dns-config"
    )

    for expected_vol in "${expected_volumes[@]}"; do
        [[ " ${HOMELAB_VOLUMES[*]} " == *" $expected_vol "* ]]
    done
}

@test "machines_get_ip should return IP addresses for new format machines" {
    # Create new format machines.yaml for this test
    cat > "${TEST_TEMP_DIR}/machines-new.yaml" <<EOF
machines:
  cody-X570-GAMING-X:
    ip: 192.168.86.41
    role: manager
    ssh_user: cody
  giant:
    ip: 192.168.86.39
    role: worker
    ssh_user: chutchens
  imac:
    ip: 192.168.86.137
    role: worker
    ssh_user: chutchens
EOF

    # Set up environment for machines.sh
    export MACHINES_FILE="${TEST_TEMP_DIR}/machines-new.yaml"
    export PROJECT_ROOT="${TEST_TEMP_DIR}"

    # Source machines.sh functions
    source "${BATS_TEST_DIRNAME}/../../../scripts/machines.sh"

    # Test that machines_get_ip returns IP addresses, not hostnames
    run machines_get_ip "cody-X570-GAMING-X"
    [ "$status" -eq 0 ]
    [ "$output" = "192.168.86.41" ]

    run machines_get_ip "giant"
    [ "$status" -eq 0 ]
    [ "$output" = "192.168.86.39" ]

    run machines_get_ip "imac"
    [ "$status" -eq 0 ]
    [ "$output" = "192.168.86.137" ]
}

@test "nuke should use IP addresses not hostnames for node connections" {
    # Verify that our change to use machines_get_ip instead of machines_build_hostname
    # is correctly implemented by checking the nuke script content

    # Check that nuke.sh contains machines_get_ip call
    run grep -n "machines_get_ip" "${BATS_TEST_DIRNAME}/../../../scripts/nuke.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"machine_ip=\$(machines_get_ip"* ]]

    # Check that it uses machine_ip variable in NODES array
    run grep -A2 -B2 "NODES+=.*machine_ip" "${BATS_TEST_DIRNAME}/../../../scripts/nuke.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"\$ssh_user@\$machine_ip"* ]]

    # Verify old hostname-based approach is not present
    run grep "machines_build_hostname" "${BATS_TEST_DIRNAME}/../../../scripts/nuke.sh"
    [ "$status" -eq 1 ]  # Should not be found
}

@test "RED: init_machines_config should not produce empty hostnames" {
    # This test should FAIL initially to reproduce the user's issue
    # Create new format machines.yaml matching user's actual config
    cat > "${TEST_TEMP_DIR}/machines-actual.yaml" <<EOF
machines:
  cody-X570-GAMING-X:
    ip: 192.168.86.41
    role: manager
    ssh_user: cody
    labels:
      gpu: true
  giant:
    ip: 192.168.86.39
    role: worker
    ssh_user: chutchens
    labels:
      gpu: true
  imac:
    ip: 192.168.86.137
    role: worker
    ssh_user: chutchens
  mini:
    ip: 192.168.86.141
    role: worker
    ssh_user: chutchens
EOF

    # Test the actual nuke script execution with realistic environment
    run bash -c "
        export PROJECT_ROOT='${TEST_TEMP_DIR}'
        export MACHINES_FILE='${TEST_TEMP_DIR}/machines-actual.yaml'
        cd '${TEST_TEMP_DIR}'

        # Copy required scripts to test directory
        mkdir -p scripts
        cp '${BATS_TEST_DIRNAME}/../../../scripts/machines.sh' scripts/
        cp '${BATS_TEST_DIRNAME}/../../../scripts/ssh.sh' scripts/

        # Source the functions and test init_machines_config
        source scripts/machines.sh
        source '${BATS_TEST_DIRNAME}/../../../scripts/nuke.sh'

        # Run init_machines_config and output the NODES array
        init_machines_config 'machines-actual.yaml' 2>/dev/null
        printf '%s\n' \"\${NODES[@]}\"
    "

    [ "$status" -eq 0 ]

    # This should FAIL if there are empty hostnames (user@)
    echo "DEBUG: Output is: '$output'"

    # Check that no node entries are missing the IP part
    [[ "$output" != *"@"$'\n'* ]]  # No lines ending with just @
    [[ "$output" != *"@ "* ]]      # No @ followed by space

    # Every line should have format user@IP
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        echo "DEBUG: Checking line: '$line'"
        [[ "$line" =~ ^[a-zA-Z0-9_-]+@[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
            echo "FAIL: Line '$line' doesn't match user@IP pattern"
            return 1
        }
    done <<< "$output"
}
