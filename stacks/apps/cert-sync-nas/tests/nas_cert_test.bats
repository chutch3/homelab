#!/usr/bin/env bats

# Tests for OpenMediaVault certificate installation functions

load test_helper

setup() {
    # Source scripts we're testing
    export TEST=true
    SCRIPTS_DIR="$(dirname "$BATS_TEST_DIRNAME")/../../../scripts"
    # shellcheck disable=SC1091
    source "${SCRIPTS_DIR}/common/ssh.sh"
    # shellcheck disable=SC1091
    source "${SCRIPTS_DIR}/common/cert.sh"
    # shellcheck disable=SC1091
    source "${SCRIPTS_DIR}/common/nas/omv.sh"

    # Create temporary test directory
    TEST_DIR="$(temp_make)"
    export TEST_DIR

    # Create mock certificate files
    echo "-----BEGIN CERTIFICATE-----" > "${TEST_DIR}/cert.pem"
    echo "Mock Certificate Data" >> "${TEST_DIR}/cert.pem"
    echo "-----END CERTIFICATE-----" >> "${TEST_DIR}/cert.pem"

    echo "-----BEGIN MOCK KEY-----" > "${TEST_DIR}/key.pem"
    echo "Mock Private Key Data" >> "${TEST_DIR}/key.pem"
    echo "-----END MOCK KEY-----" >> "${TEST_DIR}/key.pem"
}

teardown() {
    # Clean up test directory
    temp_del "${TEST_DIR}"
}

@test "omv_cert_install exists as a function" {
    type -t omv_cert_install
}

@test "omv_cert_install validates certificate files before upload" {
    # Remove certificate file
    rm "${TEST_DIR}/cert.pem"

    run omv_cert_install "nas.diyhub.dev" "${TEST_DIR}"
    assert_failure
}

@test "omv_cert_install validates NAS hostname is provided" {
    run omv_cert_install "" "${TEST_DIR}"
    assert_failure
    assert_output --partial "hostname"
}

@test "omv_cert_install validates cert directory is provided" {
    run omv_cert_install "nas.diyhub.dev" ""
    assert_failure
    assert_output --partial "directory"
}

@test "omv_cert_generate_rpc_command generates correct RPC command" {
    run omv_cert_generate_rpc_command "${TEST_DIR}/cert.pem" "${TEST_DIR}/key.pem"
    assert_success
    assert_output --partial "omv-rpc"
    assert_output --partial "CertificateMgmt"
}

@test "omv_cert_copy_files validates source files exist" {
    rm "${TEST_DIR}/cert.pem"

    run omv_cert_copy_files "test_host" "${TEST_DIR}"
    assert_failure
}
