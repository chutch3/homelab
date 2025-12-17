#!/usr/bin/env bats

# Tests for scripts/common/cert.sh

load test_helper

setup() {
    # Source the script we're testing
    export TEST=true
    # shellcheck disable=SC1091
    source "$(dirname "$BATS_TEST_DIRNAME")/../../../scripts/common/cert.sh"

    # Create temporary test directory
    TEST_DIR="$(mktemp -d)"
    export TEST_DIR
}

teardown() {
    # Clean up test directory
    rm -rf "${TEST_DIR}"
}

@test "cert_validate_files exists as a function" {
    type -t cert_validate_files
}

@test "cert_validate_files succeeds with valid certificate files" {
    # Create valid cert files
    echo "cert content" > "${TEST_DIR}/cert.pem"
    echo "key content" > "${TEST_DIR}/key.pem"

    run cert_validate_files "${TEST_DIR}"
    assert_success
}

@test "cert_validate_files fails with missing certificate" {
    echo "key content" > "${TEST_DIR}/key.pem"

    run cert_validate_files "${TEST_DIR}"
    assert_failure
}

@test "cert_validate_files fails with missing key" {
    echo "cert content" > "${TEST_DIR}/cert.pem"

    run cert_validate_files "${TEST_DIR}"
    assert_failure
}

@test "cert_validate_files fails with empty certificate" {
    touch "${TEST_DIR}/cert.pem"
    echo "key content" > "${TEST_DIR}/key.pem"

    run cert_validate_files "${TEST_DIR}"
    assert_failure
}

@test "cert_validate_files fails with empty key" {
    echo "cert content" > "${TEST_DIR}/cert.pem"
    touch "${TEST_DIR}/key.pem"

    run cert_validate_files "${TEST_DIR}"
    assert_failure
}
