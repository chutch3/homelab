#!/usr/bin/env bats

# Tests for scripts/generate-api-client.sh, with uv, uvx and npx stubbed on PATH.

bats_require_minimum_version 1.5.0

load test_helper

setup() {
    TEST_DIR="$(temp_make)"
    export TEST_DIR
    export DISKTRACKER_APP_DIR="${TEST_DIR}/app"
    mkdir -p "${DISKTRACKER_APP_DIR}/backend" "${DISKTRACKER_APP_DIR}/collector" \
        "${DISKTRACKER_APP_DIR}/frontend/src" "${TEST_DIR}/bin"

    # uv: stands in for exporting the backend's OpenAPI spec.
    cat > "${TEST_DIR}/bin/uv" <<'EOF'
#!/usr/bin/env bash
echo '{"openapi": "3.1.0", "info": {"title": "stub"}}'
EOF
    # uvx: records its arguments and the spec it was given, then writes a one-file client.
    cat > "${TEST_DIR}/bin/uvx" <<'EOF'
#!/usr/bin/env bash
echo "$*" > "${TEST_DIR}/uvx.args"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --path) cp "$2" "${TEST_DIR}/spec.json"; shift 2 ;;
        --output-path) output="$2"; shift 2 ;;
        *) shift ;;
    esac
done
mkdir -p "${output}"
echo "${STUB_CLIENT:-generated}" > "${output}/__init__.py"
EOF
    # npx: records where it ran, its arguments and the spec it was given, then writes the types.
    cat > "${TEST_DIR}/bin/npx" <<'EOF'
#!/usr/bin/env bash
pwd > "${TEST_DIR}/npx.dir"
echo "$*" > "${TEST_DIR}/npx.args"
for argument in "$@"; do
    if [[ -f "${argument}" ]]; then cp "${argument}" "${TEST_DIR}/types-spec.json"; fi
done
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift 2 ;;
        *) shift ;;
    esac
done
echo "${STUB_TYPES:-export interface paths {}}" > "${output}"
EOF
    chmod +x "${TEST_DIR}/bin/uv" "${TEST_DIR}/bin/uvx" "${TEST_DIR}/bin/npx"
    export PATH="${TEST_DIR}/bin:${PATH}"
    SCRIPT="${BATS_TEST_DIRNAME}/../scripts/generate-api-client.sh"
    CLIENT="${DISKTRACKER_APP_DIR}/collector/disktracker_api"
    TYPES="${DISKTRACKER_APP_DIR}/frontend/src/api-schema.ts"
}

teardown() {
    temp_del "${TEST_DIR}"
}

@test "generates the client from the exported spec with the pinned generator" {
    run "${SCRIPT}"

    assert_success
    assert_equal "$(cat "${CLIENT}/__init__.py")" "generated"
    assert_equal "$(cat "${TEST_DIR}/spec.json")" '{"openapi": "3.1.0", "info": {"title": "stub"}}'
    run cat "${TEST_DIR}/uvx.args"
    assert_output --partial "--from openapi-python-client==0.29.1 openapi-python-client generate"
    assert_output --partial "--meta none --config ${DISKTRACKER_APP_DIR}/collector/api-client.yml"
}

@test "generates the frontend's types from the same spec with the frontend's own generator" {
    run "${SCRIPT}"

    assert_success
    assert_equal "$(cat "${TYPES}")" "export interface paths {}"
    assert_equal "$(cat "${TEST_DIR}/types-spec.json")" '{"openapi": "3.1.0", "info": {"title": "stub"}}'
    # The generator pinned in the frontend's package.json, never one fetched on the spot.
    assert_equal "$(cat "${TEST_DIR}/npx.dir")" "${DISKTRACKER_APP_DIR}/frontend"
    run cat "${TEST_DIR}/npx.args"
    assert_output --regexp "^--no-install openapi-typescript .* --output ${TYPES}\$"
    # A field is optional exactly when the spec says so: the spec already says which defaults
    # the API always gives back.
    assert_output --partial " --default-non-nullable false "
}

@test "regenerating replaces the whole client, dropping files that are no longer generated" {
    mkdir -p "${CLIENT}"
    echo "stale" > "${CLIENT}/removed_endpoint.py"

    run "${SCRIPT}"

    assert_success
    assert [ ! -e "${CLIENT}/removed_endpoint.py" ]
}

@test "check passes when the committed client matches, ignoring bytecode caches" {
    "${SCRIPT}"
    mkdir -p "${CLIENT}/__pycache__"
    touch "${CLIENT}/__pycache__/__init__.cpython-312.pyc"

    run "${SCRIPT}" --check

    assert_success
}

@test "check fails and leaves the committed client alone when it is out of date" {
    "${SCRIPT}"

    STUB_CLIENT="changed" run --separate-stderr "${SCRIPT}" --check

    assert_failure 1
    assert_equal "$(cat "${CLIENT}/__init__.py")" "generated"
    [[ "${stderr}" == *"out of date"*"scripts/generate-api-client.sh"* ]]
}

@test "check fails and leaves the frontend's types alone when they are out of date" {
    "${SCRIPT}"

    STUB_TYPES="changed" run --separate-stderr "${SCRIPT}" --check

    assert_failure 1
    assert_equal "$(cat "${TYPES}")" "export interface paths {}"
    [[ "${stderr}" == *"frontend's API types are out of date"*"scripts/generate-api-client.sh"* ]]
}

@test "an unknown argument prints usage" {
    run --separate-stderr "${SCRIPT}" --force

    assert_failure 2
    [[ "${stderr}" == "usage: generate-api-client.sh [--check]" ]]
}
