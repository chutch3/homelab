#!/usr/bin/env bats

load test_helper

setup() {
    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"
    export PROJECT_ROOT="$TEST_TEMP_DIR"

    # Create test machines.yaml with new format
    cat > "$TEST_TEMP_DIR/machines.yaml" <<EOF
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
  imac:
    ip: 192.168.86.137
    role: worker
    ssh_user: chutchens
EOF

    export MACHINES_FILE="$TEST_TEMP_DIR/machines.yaml"
    export TEST=true
}

teardown() {
    temp_del "$TEST_TEMP_DIR"
}

@test "_remove_service_volumes should remove all service volumes from all accessible nodes" {
    # Setup: Create test service with volumes
    mkdir -p "$TEST_TEMP_DIR/stacks/apps/testservice"

    cat > "$TEST_TEMP_DIR/stacks/apps/testservice/docker-compose.yml" <<EOF
version: '3.8'
services:
  app:
    image: nginx
volumes:
  data:
  logs:
  config:
EOF

    # Setup environment
    export PROJECT_ROOT="$TEST_TEMP_DIR"
    # export APPS_DIR="$TEST_TEMP_DIR/stacks/apps"
    # export MACHINES_FILE="$TEST_TEMP_DIR/machines.yaml"

    # Create machines file with multiple nodes
    cat > "$TEST_TEMP_DIR/machines.yaml" <<EOF
machines:
  manager:
    ip: 192.168.1.10
    role: manager
    ssh_user: user1
  worker1:
    ip: 192.168.1.11
    role: worker
    ssh_user: user2
  worker2:
    ip: 192.168.1.12
    role: worker
    ssh_user: user3
EOF

    # Source the script to access functions
    source "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"

    # Mock ssh_execute to log commands to a file
    local ssh_log="${TEST_TEMP_DIR}/ssh_execute.log"
    ssh_execute() {
        echo "$@" >> "$ssh_log"
        return 0
    }

    # Execute the function
    _remove_service_volumes "testservice"

    # Assert: Check the log file for expected commands
    run cat "$ssh_log"
    [ "$status" -eq 0 ]
    [[ "$output" == *"user1@192.168.1.10 docker volume inspect testservice_data"* ]]
    [[ "$output" == *"user1@192.168.1.10 docker volume rm --force testservice_data"* ]]
    [[ "$output" == *"user2@192.168.1.11 docker volume inspect testservice_data"* ]]
    [[ "$output" == *"user2@192.168.1.11 docker volume rm --force testservice_data"* ]]
    [[ "$output" == *"user3@192.168.1.12 docker volume inspect testservice_data"* ]]
    [[ "$output" == *"user3@192.168.1.12 docker volume rm --force testservice_data"* ]]
}
