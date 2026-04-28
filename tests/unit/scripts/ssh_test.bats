#!/usr/bin/env bats

# Tests for scripts/common/ssh.sh

load test_helper

setup() {
    export TEST=true

    STUB_BIN="$(temp_make)"
    export STUB_BIN
    export SSH_KEY_FILE="$STUB_BIN/test_key"
    touch "$SSH_KEY_FILE"

    export PATH="$STUB_BIN:$PATH"

    # Source after SSH_KEY_FILE is set to suppress the warning
    # shellcheck disable=SC1091
    source "${BATS_TEST_DIRNAME}/../../../scripts/common/ssh.sh"
}

teardown() {
    temp_del "$STUB_BIN"
}

_stub_timeout() {
    cat > "$STUB_BIN/timeout" << 'EOF'
#!/usr/bin/env bash
shift  # remove duration
"$@"
EOF
    chmod +x "$STUB_BIN/timeout"
}

# --- scp_copy_file ---

@test "scp_copy_file exists as a function" {
    type -t scp_copy_file
}

@test "scp_copy_file uses StrictHostKeyChecking=accept-new" {
    _stub_timeout
    cat > "$STUB_BIN/scp" << 'EOF'
#!/usr/bin/env bash
echo "scp $*"
EOF
    chmod +x "$STUB_BIN/scp"

    run scp_copy_file "/tmp/cert.pem" "root@host:/tmp/nas_cert.pem"
    assert_success
    assert_output --partial "StrictHostKeyChecking=accept-new"
}

@test "scp_copy_file does not use StrictHostKeyChecking=no" {
    _stub_timeout
    cat > "$STUB_BIN/scp" << 'EOF'
#!/usr/bin/env bash
echo "scp $*"
EOF
    chmod +x "$STUB_BIN/scp"

    run scp_copy_file "/tmp/cert.pem" "root@host:/tmp/nas_cert.pem"
    assert_success
    refute_output --partial "StrictHostKeyChecking=no"
}

@test "scp_copy_file passes source and destination to scp" {
    _stub_timeout
    cat > "$STUB_BIN/scp" << 'EOF'
#!/usr/bin/env bash
echo "scp $*"
EOF
    chmod +x "$STUB_BIN/scp"

    run scp_copy_file "/tmp/cert.pem" "root@host:/tmp/nas_cert.pem"
    assert_success
    assert_output --partial "/tmp/cert.pem"
    assert_output --partial "root@host:/tmp/nas_cert.pem"
}

@test "scp_copy_file returns failure when scp fails" {
    _stub_timeout
    cat > "$STUB_BIN/scp" << 'EOF'
#!/usr/bin/env bash
exit 1
EOF
    chmod +x "$STUB_BIN/scp"

    run scp_copy_file "/tmp/cert.pem" "root@host:/tmp/nas_cert.pem"
    assert_failure
}

# --- ssh_execute_script ---

@test "ssh_execute_script exists as a function" {
    type -t ssh_execute_script
}

@test "ssh_execute_script pipes script file contents to ssh" {
    _stub_timeout
    local script_file="$STUB_BIN/test_script.sh"
    echo "echo hello-from-script" > "$script_file"

    cat > "$STUB_BIN/ssh" << 'EOF'
#!/usr/bin/env bash
cat
EOF
    chmod +x "$STUB_BIN/ssh"

    run ssh_execute_script "root@host" "$script_file"
    assert_success
    assert_output --partial "hello-from-script"
}

@test "ssh_execute_script uses StrictHostKeyChecking=accept-new" {
    _stub_timeout
    local script_file="$STUB_BIN/test_script.sh"
    echo "echo hello" > "$script_file"

    cat > "$STUB_BIN/ssh" << 'EOF'
#!/usr/bin/env bash
echo "ssh $*"
EOF
    chmod +x "$STUB_BIN/ssh"

    run ssh_execute_script "root@host" "$script_file"
    assert_success
    assert_output --partial "StrictHostKeyChecking=accept-new"
    refute_output --partial "StrictHostKeyChecking=no"
}

@test "ssh_execute_script returns failure when ssh fails" {
    _stub_timeout
    local script_file="$STUB_BIN/test_script.sh"
    echo "echo hello" > "$script_file"

    cat > "$STUB_BIN/ssh" << 'EOF'
#!/usr/bin/env bash
exit 1
EOF
    chmod +x "$STUB_BIN/ssh"

    run ssh_execute_script "root@host" "$script_file"
    assert_failure
}
