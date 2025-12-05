#!/usr/bin/env bats

load ../test_helper

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

@test "deploy_stack should use --resolve-image never for multi-architecture support" {
    # The docker stack deploy command must include --resolve-image never
    # to allow each swarm node to pull the correct architecture image
    # for its platform (amd64, arm64, etc.)

    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Verify the script exists
    [ -f "$deploy_script" ]

    # Check that docker stack deploy uses --resolve-image never
    run grep -E "docker stack deploy.*--resolve-image never" "$deploy_script"
    [ "$status" -eq 0 ]
}

@test "deploy_cluster should have --skip-infra flag and conditional logic" {
    # Test: Verify --skip-infra flag exists and has conditional logic to skip infrastructure
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check the flag is parsed
    run grep -q "skip_infra=true" "$deploy_script"
    [ "$status" -eq 0 ]

    # Check that infrastructure setup is wrapped in conditional
    run grep -B2 "PHASE 1: MACHINE & SWARM SETUP" "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "skip_infra" ]]
}

@test "deploy_cluster should parse --skip-apps flag correctly" {
    # Test: Verify --skip-apps flag is parsed and stored in array
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check flag is recognized in case statement
    run grep -A8 "^\s*--skip-apps)" "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "IFS=',' read -r -a skip_apps" ]]
}

@test "deploy_cluster should skip apps specified in --skip-apps" {
    # Test: Verify skip_apps logic filters out specified apps
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check that skip_apps array is checked in deployment loop
    run grep 'skip_apps\[\*\]' "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "stack_name" ]]

    # Verify the log message for skipped apps
    run grep "Skipping app stack as requested" "$deploy_script"
    [ "$status" -eq 0 ]
}

@test "deploy_cluster should parse --only-apps flag correctly" {
    # Test: Verify --only-apps flag is parsed and stored in array
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check flag is recognized in case statement
    run grep -A8 "^\s*--only-apps)" "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "IFS=',' read -r -a only_apps" ]]
}

@test "deploy_cluster should deploy only apps specified in --only-apps" {
    # Test: Verify only_apps logic filters to only specified apps
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check that only_apps array is checked in deployment loop
    run grep 'only_apps\[\*\]' "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "stack_name" ]]
}

@test "deploy_cluster should error on unknown flags" {
    # Test: Verify unknown flags trigger an error
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check that default case in flag parsing shows error
    run grep -A3 '^\s*\*)$' "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Unknown option" ]]
    [[ "$output" =~ "exit 1" ]]
}

@test "deploy_cluster should validate --only-apps has argument" {
    # Test: Verify --only-apps requires an argument
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check that --only-apps validates $2 exists
    run grep -A5 "^\s*--only-apps)" "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "only_apps requires an argument" || "$output" =~ "\${2:-}" || "$output" =~ "if.*\$2" ]]
}

@test "deploy_cluster should validate --skip-apps has argument" {
    # Test: Verify --skip-apps requires an argument
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check that --skip-apps validates $2 exists
    run grep -A5 "^\s*--skip-apps)" "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "skip_apps requires an argument" || "$output" =~ "\${2:-}" || "$output" =~ "if.*\$2" ]]
}

@test "deploy_cluster should use configure_dns_records function not old script" {
    # Test: Verify DNS configuration uses the function from dns.sh
    # instead of the outdated configure_dns_records.sh script
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check that old script is NOT referenced
    run grep "configure_dns_records.sh" "$deploy_script"
    [ "$status" -ne 0 ]

    # Check that configure_dns_records function IS called
    run grep "configure_dns_records" "$deploy_script"
    [ "$status" -eq 0 ]
    # Verify it's a function call (not a script path)
    [[ ! "$output" =~ ".sh" ]]
}

@test "deploy_cluster should source cluster.sh at top of script before conditionals" {
    # Test: Verify deploy.sh sources cluster.sh at the top with other common utilities
    # This ensures monitor_swarm_cluster is available even when --skip-infra is used
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check that cluster.sh is sourced in the first 30 lines (with other source statements)
    run head -n 30 "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "source".*"cluster.sh" ]] || [[ "$output" =~ ".".*"cluster.sh" ]]

    # Check that monitor_swarm_cluster function is called
    run grep "monitor_swarm_cluster" "$deploy_script"
    [ "$status" -eq 0 ]
}

@test "deploy_cluster should source monitoring.sh at top of script" {
    # Test: Verify deploy.sh sources monitoring.sh with other utilities
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check that monitoring.sh is sourced in the first 30 lines
    run head -n 30 "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "source".*"monitoring.sh" ]] || [[ "$output" =~ ".".*"monitoring.sh" ]]
}

@test "deploy_cluster should configure Docker daemon metrics during infrastructure setup" {
    # Test: Verify Docker daemon metrics are configured before deploying services
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Check that configure_all_nodes is called in PHASE 1 or PHASE 2
    run grep -A50 "PHASE 1: MACHINE & SWARM SETUP" "$deploy_script"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "configure_all_nodes" ]] || {
        # If not in PHASE 1, check PHASE 2
        run grep -A30 "PHASE 2: CORE INFRASTRUCTURE" "$deploy_script"
        [ "$status" -eq 0 ]
        [[ "$output" =~ "configure_all_nodes" ]]
    }
}

@test "deploy_cluster should skip monitoring configuration when --skip-infra is used" {
    # Test: Verify monitoring configuration is inside skip_infra conditional
    local deploy_script="${BATS_TEST_DIRNAME}/../../../../scripts/docker_swarm/deploy.sh"

    # Find the line with configure_all_nodes
    local config_line
    config_line=$(grep -n "configure_all_nodes" "$deploy_script" | head -1 | cut -d: -f1)

    # Verify line number was found
    [ -n "$config_line" ]

    # Check that there's a skip_infra conditional before configure_all_nodes
    run grep -B20 "configure_all_nodes" "$deploy_script"
    assert_success
    # Match either == "false" or other skip_infra checks
    [[ "$output" =~ skip_infra.*false ]] || [[ "$output" =~ 'if'.*skip_infra ]]
}
