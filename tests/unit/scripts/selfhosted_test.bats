#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true

    # Change to test directory
    cd "$TEST_TEMP_DIR" || return
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "selfhosted_script_should_show_usage_for_unknown_command" {
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" unknown
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown command: unknown"* ]]
    [[ "$output" == *"Available commands:"* ]]
    [[ "$output" == *"service"* ]]
    [[ "$output" == *"deploy"* ]]
    [[ "$output" == *"config"* ]]
}

@test "selfhosted_script_should_show_usage_for_no_arguments" {
    run bash "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"USAGE:"* ]]
    [[ "$output" == *"service"* ]]
    [[ "$output" == *"deploy"* ]]
    [[ "$output" == *"config"* ]]
}

@test "selfhosted_script_should_have_correct_shebang" {
    # Check that script starts with #!/bin/bash (the second shebang)
    run head -n1 "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == "#!/bin/bash" ]]
}

@test "selfhosted_script_should_be_executable" {
    # Check that the script has executable permissions
    [ -x "${BATS_TEST_DIRNAME}/../../../selfhosted.sh" ]
}

@test "selfhosted_script_should_contain_case_statement" {
    # Test that the script contains the main case statement with service command
    run grep -A 20 "case.*\$1.*in" "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"service"* ]]

    # Check for modern commands exist in the script
    run grep "deploy)" "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
    [ "$status" -eq 0 ]

    run grep "config)" "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
    [ "$status" -eq 0 ]
}

@test "selfhosted_script_should_source_required_files" {
    # Test that the script sources required dependencies
    run grep "source.*scripts" "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"scripts/common.sh"* ]]
    [[ "$output" == *"scripts/machines.sh"* ]]
}

@test "selfhosted_script_should_handle_deployment_targets" {
    # Test that the script contains logic for deployment commands
    run grep -A 5 "enhanced_deploy" "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"deploy"* ]]

    # Check for service generator integration
    run grep "service_generator" "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
    [ "$status" -eq 0 ]
}
