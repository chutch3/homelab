#!/usr/bin/env bats

# Tests for sync-nas-cert.sh

load test_helper

SCRIPT="$(dirname "$BATS_TEST_DIRNAME")/sync-nas-cert.sh"

setup() {
    ACME_DIR="$(temp_make)"
    export ACME_DIR

    MOCK_COMMON="$(temp_make)"
    export MOCK_COMMON

    # Stub omv.sh so SSH operations are never invoked
    mkdir -p "$MOCK_COMMON/nas"
    cat > "$MOCK_COMMON/nas/omv.sh" << 'EOF'
#!/usr/bin/env bash
omv_cert_install() {
    echo "STUB: omv_cert_install $*"
    return 0
}
export -f omv_cert_install
EOF

    export NAS_HOST="nas.example.com"
    export CERT_DOMAIN="nas.example.com"
}

teardown() {
    temp_del "$ACME_DIR"
    temp_del "$MOCK_COMMON"
}

_make_cert_dir() {
    local dir="$1"
    mkdir -p "$dir"
    echo "-----BEGIN CERTIFICATE-----" > "$dir/fullchain.cer"
    echo "-----BEGIN MOCK KEY-----" > "$dir/${CERT_DOMAIN}.key"
}

@test "uses ECC cert path when _ecc directory exists" {
    _make_cert_dir "${ACME_DIR}/${CERT_DOMAIN}_ecc"

    run bash -c "COMMON_DIR='$MOCK_COMMON' ACME_DIR='$ACME_DIR' NAS_HOST='$NAS_HOST' CERT_DOMAIN='$CERT_DOMAIN' bash '$SCRIPT'"
    assert_success
    assert_output --partial "ECC cert path"
}

@test "falls back to non-ECC path and logs it" {
    _make_cert_dir "${ACME_DIR}/${CERT_DOMAIN}"

    run bash -c "COMMON_DIR='$MOCK_COMMON' ACME_DIR='$ACME_DIR' NAS_HOST='$NAS_HOST' CERT_DOMAIN='$CERT_DOMAIN' bash '$SCRIPT'"
    assert_success
    assert_output --partial "non-ECC cert path"
}

@test "fails when neither cert directory exists" {
    run bash -c "COMMON_DIR='$MOCK_COMMON' ACME_DIR='$ACME_DIR' NAS_HOST='$NAS_HOST' CERT_DOMAIN='$CERT_DOMAIN' bash '$SCRIPT'"
    assert_failure
    assert_output --partial "not found"
}

@test "fails when fullchain.cer is missing" {
    mkdir -p "${ACME_DIR}/${CERT_DOMAIN}_ecc"
    echo "key content" > "${ACME_DIR}/${CERT_DOMAIN}_ecc/${CERT_DOMAIN}.key"

    run bash -c "COMMON_DIR='$MOCK_COMMON' ACME_DIR='$ACME_DIR' NAS_HOST='$NAS_HOST' CERT_DOMAIN='$CERT_DOMAIN' bash '$SCRIPT'"
    assert_failure
    assert_output --partial "fullchain.cer"
}

@test "fails when key file is missing" {
    mkdir -p "${ACME_DIR}/${CERT_DOMAIN}_ecc"
    echo "cert content" > "${ACME_DIR}/${CERT_DOMAIN}_ecc/fullchain.cer"

    run bash -c "COMMON_DIR='$MOCK_COMMON' ACME_DIR='$ACME_DIR' NAS_HOST='$NAS_HOST' CERT_DOMAIN='$CERT_DOMAIN' bash '$SCRIPT'"
    assert_failure
    assert_output --partial ".key"
}
