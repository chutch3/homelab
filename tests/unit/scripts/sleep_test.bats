#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

        # Set up test environment variables
    export TEST=true
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "sleep_script_should_output_start_message" {
    run bash "${BATS_TEST_DIRNAME}/../../../scripts/sleep.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Sleeping for 10 seconds"* ]]
}

@test "sleep_script_should_output_end_message" {
    run bash "${BATS_TEST_DIRNAME}/../../../scripts/sleep.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Done sleeping"* ]]
}

@test "sleep_script_should_contain_sleep_command" {
    # Test that the script contains the expected sleep command
    run grep "sleep 10" "${BATS_TEST_DIRNAME}/../../../scripts/sleep.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"sleep 10"* ]]
}

@test "sleep_script_should_be_executable" {
    # Check that the script has executable permissions
    [ -x "${BATS_TEST_DIRNAME}/../../../scripts/sleep.sh" ]
}

@test "sleep_script_should_have_correct_shebang" {
    # Check that script starts with #!/bin/sh
    run head -n1 "${BATS_TEST_DIRNAME}/../../../scripts/sleep.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == "#!/bin/sh" ]]
}
