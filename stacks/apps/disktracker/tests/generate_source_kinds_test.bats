#!/usr/bin/env bats

# Tests for scripts/generate-source-kinds.sh, with uv stubbed on PATH.

bats_require_minimum_version 1.5.0

load test_helper

setup() {
    TEST_DIR="$(temp_make)"
    export TEST_DIR
    export DISKTRACKER_APP_DIR="${TEST_DIR}/app"
    mkdir -p "${DISKTRACKER_APP_DIR}/backend/disktracker" "${DISKTRACKER_APP_DIR}/collector" "${TEST_DIR}/bin"

    # uv: stands in for the collector describing its readers; records how it was asked.
    cat > "${TEST_DIR}/bin/uv" <<'EOF'
#!/usr/bin/env bash
echo "$*" > "${TEST_DIR}/uv.args"
pwd > "${TEST_DIR}/uv.cwd"
echo "${STUB_KINDS:-{\"shopify\": {\"label\": \"Shopify\"}}}"
EOF
    chmod +x "${TEST_DIR}/bin/uv"
    export PATH="${TEST_DIR}/bin:${PATH}"
    SCRIPT="${BATS_TEST_DIRNAME}/../scripts/generate-source-kinds.sh"
    KINDS="${DISKTRACKER_APP_DIR}/backend/disktracker/source_kinds.json"
}

teardown() {
    temp_del "${TEST_DIR}"
}

@test "writes what the collector's readers describe into the backend" {
    run "${SCRIPT}"

    assert_success
    assert_equal "$(cat "${KINDS}")" '{"shopify": {"label": "Shopify"}}'
    assert_equal "$(cat "${TEST_DIR}/uv.args")" "run --frozen python -m collector.kinds"
    assert_equal "$(cat "${TEST_DIR}/uv.cwd")" "${DISKTRACKER_APP_DIR}/collector"
}

@test "check passes when the committed description matches" {
    "${SCRIPT}"

    run "${SCRIPT}" --check

    assert_success
}

@test "check fails and leaves the committed description alone when it is out of date" {
    "${SCRIPT}"

    STUB_KINDS='{"shopify": {"label": "Changed"}}' run --separate-stderr "${SCRIPT}" --check

    assert_failure 1
    assert_equal "$(cat "${KINDS}")" '{"shopify": {"label": "Shopify"}}'
    [[ "${stderr}" == *"out of date"*"scripts/generate-source-kinds.sh"* ]]
}

@test "a description that cannot be generated leaves the committed one alone" {
    "${SCRIPT}"
    cat > "${TEST_DIR}/bin/uv" <<'EOF'
#!/usr/bin/env bash
echo "half a descr"
exit 3
EOF

    run "${SCRIPT}"

    assert_failure 3
    assert_equal "$(cat "${KINDS}")" '{"shopify": {"label": "Shopify"}}'
}

@test "an unknown argument prints usage and generates nothing" {
    run --separate-stderr "${SCRIPT}" --force

    assert_failure 2
    [[ "${stderr}" == "usage: generate-source-kinds.sh [--check]" ]]
    assert [ ! -e "${TEST_DIR}/uv.args" ]
}
