#!/usr/bin/env bats

# Tests for scripts/common/nas/omv.sh

load test_helper

setup() {
    export TEST=true
    local scripts_dir="${BATS_TEST_DIRNAME}/../../../scripts"
    # shellcheck disable=SC1091
    source "${scripts_dir}/common/ssh.sh"
    # shellcheck disable=SC1091
    source "${scripts_dir}/common/cert.sh"
    # shellcheck disable=SC1091
    source "${scripts_dir}/common/nas/omv.sh"

    TEST_DIR="$(temp_make)"
    export TEST_DIR

    echo "-----BEGIN CERTIFICATE-----" > "${TEST_DIR}/cert.pem"
    echo "Mock Certificate Data" >> "${TEST_DIR}/cert.pem"
    echo "-----END CERTIFICATE-----" >> "${TEST_DIR}/cert.pem"

    echo "-----BEGIN MOCK KEY-----" > "${TEST_DIR}/key.pem"
    echo "Mock Private Key Data" >> "${TEST_DIR}/key.pem"
    echo "-----END MOCK KEY-----" >> "${TEST_DIR}/key.pem"
}

teardown() {
    temp_del "${TEST_DIR}"
}

@test "omv_cert_install exists as a function" {
    type -t omv_cert_install
}

@test "omv_cert_install validates certificate files before upload" {
    rm "${TEST_DIR}/cert.pem"

    run omv_cert_install "nas.example.com" "${TEST_DIR}"
    assert_failure
}

@test "omv_cert_install validates NAS hostname is provided" {
    run omv_cert_install "" "${TEST_DIR}"
    assert_failure
    assert_output --partial "hostname"
}

@test "omv_cert_install validates cert directory is provided" {
    run omv_cert_install "nas.example.com" ""
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

@test "omv_cert_copy_files uses NAS_USER for the connection" {
    NAS_USER="admin" run omv_cert_copy_files "nas.example.com" "${TEST_DIR}"
    assert_success
    assert_output --partial "admin@nas.example.com"
}

@test "omv_cert_copy_files defaults NAS_USER to root" {
    unset NAS_USER
    run omv_cert_copy_files "nas.example.com" "${TEST_DIR}"
    assert_success
    assert_output --partial "root@nas.example.com"
}

@test "omv_cert_install uses NAS_USER for the connection" {
    NAS_USER="admin" run omv_cert_install "nas.example.com" "${TEST_DIR}"
    assert_success
    assert_output --partial "admin@nas.example.com"
}

@test "omv_cert_install defaults NAS_USER to root" {
    unset NAS_USER
    run omv_cert_install "nas.example.com" "${TEST_DIR}"
    assert_success
    assert_output --partial "root@nas.example.com"
}
