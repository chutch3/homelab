#!/usr/bin/env bats

load ../test_helper

setup() {
    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"
    export PROJECT_ROOT="$TEST_TEMP_DIR"
    export TEST=true
}

teardown() {
    temp_del "$TEST_TEMP_DIR"
}

@test "volume.sh should exist in docker_swarm directory" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"
    [ -f "$volume_script" ]
}

@test "volume.sh should define volume_ls function" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that volume_ls function is defined
    run grep -q "^volume_ls()" "$volume_script"
    [ "$status" -eq 0 ]
}

@test "volume.sh should define volume_inspect function" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that volume_inspect function is defined
    run grep -q "^volume_inspect()" "$volume_script"
    [ "$status" -eq 0 ]
}

@test "volume_ls should list all volumes when no service specified" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that volume_ls uses docker volume ls
    run grep "docker volume ls" "$volume_script"
    [ "$status" -eq 0 ]
}

@test "volume_inspect should accept service name as parameter" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that volume_inspect uses service parameter
    run grep -A5 "^volume_inspect()" "$volume_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "service" || "$output" =~ "\$1" ]]
}

@test "volume.sh should define volume_diff function" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that volume_diff function is defined
    run grep -q "^volume_diff()" "$volume_script"
    [ "$status" -eq 0 ]
}

@test "volume_diff should require service name parameter" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that volume_diff validates service parameter
    run grep -A10 "^volume_diff()" "$volume_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "service" ]]
}

@test "volume_diff should check for compose file existence" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that volume_diff looks for docker-compose.yml
    run grep "docker-compose.yml" "$volume_script"
    [ "$status" -eq 0 ]
}

@test "volume.sh should define volume_recreate function" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that volume_recreate function is defined
    run grep -q "^volume_recreate()" "$volume_script"
    [ "$status" -eq 0 ]
}

@test "volume_recreate should require service name parameter" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that volume_recreate validates service parameter
    run grep -A10 "^volume_recreate()" "$volume_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "service" ]]
}

@test "volume_recreate should have confirmation prompt logic" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check for confirmation or force flag logic
    run grep -A30 "^volume_recreate()" "$volume_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "force" || "$output" =~ "confirm" ]]
}

@test "volume_recreate should reference docker stack rm" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that it removes the stack to stop the service
    run grep "docker stack rm" "$volume_script"
    [ "$status" -eq 0 ]
}

@test "volume_recreate should reference docker volume rm" {
    local volume_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/volume.sh"

    # Check that it removes volumes
    run grep "docker volume rm" "$volume_script"
    [ "$status" -eq 0 ]
}
