#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export BASE_DOMAIN="test.local"
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export DOMAIN_FILE="${TEST_TEMP_DIR}/.domains"

    # Create test enabled-services file
    mkdir -p "${TEST_TEMP_DIR}"
    echo "cryptpad
actual_budget" >"${TEST_TEMP_DIR}/.enabled-services"

    # Create test .env file
    echo "BASE_DOMAIN=test.local" >"${TEST_TEMP_DIR}/.env"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT
}

@test "build_domain.sh creates .domains file with correct variables" {
    # Run the script
    run "${BATS_TEST_DIRNAME}/../../scripts/build_domain.sh"

    # Check exit status
    [ "$status" -eq 0 ]

    # Verify .domains file exists
    [ -f "${DOMAIN_FILE}" ]

    # Check for required variables
    run grep "^BASE_DOMAIN=test.local$" "${DOMAIN_FILE}"
    [ "$status" -eq 0 ]

    run grep "^DOMAIN_CRYPTPAD=drive.test.local$" "${DOMAIN_FILE}"
    [ "$status" -eq 0 ]

    run grep "^DOMAIN_CRYPTPAD_SANDBOX=sandbox.drive.test.local$" "${DOMAIN_FILE}"
    [ "$status" -eq 0 ]

    run grep "^DOMAIN_BUDGET=budget.test.local$" "${DOMAIN_FILE}"
    [ "$status" -eq 0 ]
}

@test "build_domain.sh fails when BASE_DOMAIN is not set" {
    # Unset BASE_DOMAIN
    unset BASE_DOMAIN

    # Run the script
    run "${BATS_TEST_DIRNAME}/../../scripts/build_domain.sh"

    # Check that script failed
    [ "$status" -eq 1 ]

    # Verify error message
    [[ "${output}" =~ "BASE_DOMAIN is not set" ]]
}

@test "build_domain.sh uses default pattern for unknown services" {
    # Add unknown service to enabled-services
    echo "unknown_service" >>"${TEST_TEMP_DIR}/.enabled-services"

    # Run the script
    run "${BATS_TEST_DIRNAME}/../../scripts/build_domain.sh"

    # Check exit status
    [ "$status" -eq 0 ]

    # Verify default pattern was used
    run grep "^DOMAIN_UNKNOWN_SERVICE=unknown_service.test.local$" "${DOMAIN_FILE}"
    [ "$status" -eq 0 ]
}

@test "build_domain.sh sources variables into current shell" {
    # Run the script with source
    source "${BATS_TEST_DIRNAME}/../../scripts/build_domain.sh"

    # Verify variables are set in current environment
    [ "$BASE_DOMAIN" = "test.local" ]
    [ "$DOMAIN_CRYPTPAD" = "drive.test.local" ]
    [ "$DOMAIN_CRYPTPAD_SANDBOX" = "sandbox.drive.test.local" ]
    [ "$DOMAIN_BUDGET" = "budget.test.local" ]
}
