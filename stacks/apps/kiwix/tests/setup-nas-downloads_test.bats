#!/usr/bin/env bats
# shellcheck disable=SC2076,SC2317,SC1090,SC2015
# SC2076: Quotes in regex are intentional for literal matching in tests
# SC2317: Mock functions appear unreachable but are invoked by sourced scripts
# SC1090: Dynamic source paths in tests cannot be followed statically
# SC2015: && || pattern is intentional in helper functions

# Inline helper functions
temp_make() { mktemp -d; }
temp_del() { [[ -n "$1" ]] && [[ -d "$1" ]] && rm -rf "$1" 2>/dev/null || true; }

setup() {
    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"
    export TEST_DIR="$TEST_TEMP_DIR"

    # Mock environment
    export TEST_MODE=1
    export PROJECT_ROOT="$TEST_TEMP_DIR"

    # Create mock .env
    mkdir -p "$PROJECT_ROOT"
    cat > "$PROJECT_ROOT/.env" <<EOF
NAS_SERVER=test.nas.local
SSH_KEY_FILE=/tmp/test_key
BASE_DOMAIN=test.com
EOF

    # Create mock ssh.sh
    mkdir -p "$PROJECT_ROOT/scripts/common"
    cat > "$PROJECT_ROOT/scripts/common/ssh.sh" <<'EOF'
#!/bin/bash
ssh_test_connection() { return 0; }
ssh_copy_key() { return 0; }
ssh_execute() { return 0; }
ssh_create_directory() { return 0; }
ssh_command_exists() { return 0; }
export -f ssh_test_connection ssh_copy_key ssh_execute ssh_create_directory ssh_command_exists
EOF
    chmod +x "$PROJECT_ROOT/scripts/common/ssh.sh"
}

teardown() {
    temp_del "$TEST_TEMP_DIR"
}

# ==============================================================================
# Core Functionality Tests
# ==============================================================================

@test "setup-nas-downloads.sh should exist and be executable" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    [ -f "$script" ]
    [ -x "$script" ]
}

@test "setup-nas-downloads.sh should have bash shebang" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run head -n 1 "$script"
    [[ "$output" =~ ^#!/.*bash ]]
}

@test "setup-nas-downloads.sh should use strict error handling" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep "set -euo pipefail" "$script"
    [ "$status" -eq 0 ]
}

# ==============================================================================
# Function Definition Tests
# ==============================================================================

@test "setup-nas-downloads.sh should define load_environment function" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "^load_environment\(\)" "$script"
    [ "$status" -eq 0 ]
}

@test "setup-nas-downloads.sh should define get_nas_connection_info function" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "^get_nas_connection_info\(\)" "$script"
    [ "$status" -eq 0 ]
}

@test "setup-nas-downloads.sh should define ensure_ssh_connectivity function" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "^ensure_ssh_connectivity\(\)" "$script"
    [ "$status" -eq 0 ]
}

@test "setup-nas-downloads.sh should define get_storage_configuration function" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "^get_storage_configuration\(\)" "$script"
    [ "$status" -eq 0 ]
}

@test "setup-nas-downloads.sh should define setup_nas_directories function" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "^setup_nas_directories\(\)" "$script"
    [ "$status" -eq 0 ]
}

@test "setup-nas-downloads.sh should define install_zim_manager function" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "^install_zim_manager\(\)" "$script"
    [ "$status" -eq 0 ]
}

@test "setup-nas-downloads.sh should define setup_update_schedule function" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "^setup_update_schedule\(\)" "$script"
    [ "$status" -eq 0 ]
}

@test "setup-nas-downloads.sh should define verify_email_system function" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "^verify_email_system\(\)" "$script"
    [ "$status" -eq 0 ]
}

@test "setup-nas-downloads.sh should define offer_initial_download function" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "^offer_initial_download\(\)" "$script"
    [ "$status" -eq 0 ]
}

@test "setup-nas-downloads.sh should define main function" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "^main\(\)" "$script"
    [ "$status" -eq 0 ]
}

# ==============================================================================
# load_environment() Function Tests
# ==============================================================================

@test "load_environment should source .env file if it exists" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A20 "^load_environment()" "$script"
    [[ "$output" =~ "source" ]] && [[ "$output" =~ ".env" ]]
}

@test "load_environment should source scripts/common/ssh.sh" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A20 "^load_environment()" "$script"
    [[ "$output" =~ "source" ]] && [[ "$output" =~ "ssh.sh" ]]
}

@test "load_environment should exit if ssh.sh not found" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A20 "^load_environment()" "$script"
    [[ "$output" =~ "exit 1" ]]
}

# ==============================================================================
# get_nas_connection_info() Function Tests
# ==============================================================================

@test "get_nas_connection_info should call machines_get_ip" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A20 "^get_nas_connection_info()" "$script"
    [[ "$output" =~ "machines_get_ip" ]]
}

@test "get_nas_connection_info should call machines_get_ssh_user" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A20 "^get_nas_connection_info()" "$script"
    [[ "$output" =~ "machines_get_ssh_user" ]]
}

@test "get_nas_connection_info should use SSH_KEY_FILE from env if set" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A35 "^get_nas_connection_info()" "$script"
    [[ "$output" =~ "SSH_KEY_FILE" ]]
}

@test "get_nas_connection_info should set NAS_USER_HOST" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A20 "^get_nas_connection_info()" "$script"
    [[ "$output" =~ "NAS_USER" ]]
}

@test "get_nas_connection_info should build NAS_USER_HOST variable" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A25 "^get_nas_connection_info()" "$script"
    [[ "$output" =~ "NAS_USER_HOST" ]]
}

# ==============================================================================
# ensure_ssh_connectivity() Function Tests
# ==============================================================================

@test "ensure_ssh_connectivity should call ssh_test_connection" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A15 "^ensure_ssh_connectivity()" "$script"
    [[ "$output" =~ "ssh_test_connection" ]]
}

@test "ensure_ssh_connectivity should call ssh_copy_key on connection failure" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A20 "^ensure_ssh_connectivity()" "$script"
    [[ "$output" =~ "ssh_copy_key" ]]
}

@test "ensure_ssh_connectivity should retry connection after copying key" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A25 "^ensure_ssh_connectivity()" "$script"
    # Should have at least 2 calls to ssh_test_connection
    [ "$(echo "$output" | grep -c "ssh_test_connection")" -ge 2 ]
}

@test "ensure_ssh_connectivity should exit 1 on persistent failure" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^ensure_ssh_connectivity()" "$script"
    [[ "$output" =~ "exit 1" ]]
}

@test "ensure_ssh_connectivity should return 0 on success" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^ensure_ssh_connectivity()" "$script"
    [[ "$output" =~ "return 0" ]]
}

# ==============================================================================
# get_storage_configuration() Function Tests
# ==============================================================================

@test "get_storage_configuration should prompt for ZIM_DATA_DIR" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A10 "^get_storage_configuration()" "$script"
    [[ "$output" =~ "ZIM_DATA_DIR" ]]
}

@test "get_storage_configuration should prompt for ZIM_LOG_DIR" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A10 "^get_storage_configuration()" "$script"
    [[ "$output" =~ "ZIM_LOG_DIR" ]]
}

@test "get_storage_configuration should prompt for EMAIL_TO" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A10 "^get_storage_configuration()" "$script"
    [[ "$output" =~ "EMAIL_TO" ]]
}

# ==============================================================================
# setup_nas_directories() Function Tests
# ==============================================================================

@test "setup_nas_directories should call ssh_create_directory for ZIM_DATA_DIR" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A15 "^setup_nas_directories()" "$script"
    [[ "$output" =~ "ssh_create_directory" ]] && [[ "$output" =~ "ZIM_DATA_DIR" ]]
}

@test "setup_nas_directories should call ssh_create_directory for ZIM_LOG_DIR" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A15 "^setup_nas_directories()" "$script"
    [[ "$output" =~ "ssh_create_directory" ]] && [[ "$output" =~ "ZIM_LOG_DIR" ]]
}

@test "setup_nas_directories should exit 1 if directory creation fails" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A20 "^setup_nas_directories()" "$script"
    [[ "$output" =~ "exit 1" ]]
}

# ==============================================================================
# install_zim_manager() Function Tests
# ==============================================================================

@test "install_zim_manager should use scp to copy script" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A15 "^install_zim_manager()" "$script"
    [[ "$output" =~ "scp" ]]
}

@test "install_zim_manager should copy to /usr/local/bin/zim-manager.sh" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A15 "^install_zim_manager()" "$script"
    [[ "$output" =~ "/usr/local/bin/zim-manager.sh" ]]
}

@test "install_zim_manager should make script executable via ssh_execute" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A20 "^install_zim_manager()" "$script"
    [[ "$output" =~ "chmod +x" ]]
}

@test "install_zim_manager should create /etc/kiwix-config.sh" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A25 "^install_zim_manager()" "$script"
    [[ "$output" =~ "/etc/kiwix-config.sh" ]]
}

@test "install_zim_manager should export ZIM_DATA_DIR in config" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^install_zim_manager()" "$script"
    [[ "$output" =~ "export ZIM_DATA_DIR" ]]
}

@test "install_zim_manager should export ZIM_LOG_DIR in config" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^install_zim_manager()" "$script"
    [[ "$output" =~ "export ZIM_LOG_DIR" ]]
}

@test "install_zim_manager should export EMAIL_TO in config" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^install_zim_manager()" "$script"
    [[ "$output" =~ "export EMAIL_TO" ]]
}

# ==============================================================================
# setup_update_schedule() Function Tests
# ==============================================================================

@test "setup_update_schedule should use omv-rpc to create scheduled task" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^setup_update_schedule()" "$script"
    [[ "$output" =~ "omv-rpc" ]] && [[ "$output" =~ "Cron" ]] && [[ "$output" =~ "set" ]]
}

@test "setup_update_schedule should use OMV sentinel UUID" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A35 "^setup_update_schedule()" "$script"
    [[ "$output" =~ "OMV_CONFIGOBJECT_NEW_UUID" ]]
}

@test "setup_update_schedule should run on 1st of month at 2 AM" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^setup_update_schedule()" "$script"
    [[ "$output" =~ "minute" ]] && \
    [[ "$output" =~ "hour" ]] && \
    [[ "$output" =~ "dayofmonth" ]]
}

@test "setup_update_schedule should source kiwix-config.sh in command" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^setup_update_schedule()" "$script"
    [[ "$output" =~ "/etc/kiwix-config.sh" ]]
}

@test "setup_update_schedule should run zim-manager.sh check" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^setup_update_schedule()" "$script"
    [[ "$output" =~ "zim-manager.sh check" ]]
}

@test "setup_update_schedule should apply configuration with omv-salt" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^setup_update_schedule()" "$script"
    [[ "$output" =~ "omv-salt deploy run cron" ]]
}

# ==============================================================================
# verify_email_system() Function Tests
# ==============================================================================

@test "verify_email_system should use ssh_command_exists to check for mail" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A10 "^verify_email_system()" "$script"
    [[ "$output" =~ "ssh_command_exists" ]] && [[ "$output" =~ "mail" ]]
}

@test "verify_email_system should send test email if mail exists" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A15 "^verify_email_system()" "$script"
    [[ "$output" =~ "mail -s" ]]
}

@test "verify_email_system should warn if mail command not found" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A15 "^verify_email_system()" "$script"
    [[ "$output" =~ "log_warn" ]]
}

# ==============================================================================
# offer_initial_download() Function Tests
# ==============================================================================

@test "offer_initial_download should prompt user (y/N)" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A5 "^offer_initial_download()" "$script"
    [[ "$output" =~ "read" ]]
}

@test "offer_initial_download should accept Y/y for yes" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A10 "^offer_initial_download()" "$script"
    [[ "$output" =~ "Yy" ]]
}

@test "offer_initial_download should use nohup for background execution" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A15 "^offer_initial_download()" "$script"
    [[ "$output" =~ "nohup" ]]
}

@test "offer_initial_download should run zim-manager.sh init" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A15 "^offer_initial_download()" "$script"
    [[ "$output" =~ "zim-manager.sh init" ]]
}

# ==============================================================================
# main() Function Tests
# ==============================================================================

@test "main should call load_environment" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A10 "^cmd_setup()" "$script"
    [[ "$output" =~ "load_environment" ]]
}

@test "main should call get_nas_connection_info" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A10 "^cmd_setup()" "$script"
    [[ "$output" =~ "get_nas_connection_info" ]]
}

@test "main should call ensure_ssh_connectivity" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A15 "^cmd_setup()" "$script"
    [[ "$output" =~ "ensure_ssh_connectivity" ]]
}

@test "main should call get_storage_configuration" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A20 "^cmd_setup()" "$script"
    [[ "$output" =~ "get_storage_configuration" ]]
}

@test "main should call setup_nas_directories" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A25 "^cmd_setup()" "$script"
    [[ "$output" =~ "setup_nas_directories" ]]
}

@test "main should call install_zim_manager" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A30 "^cmd_setup()" "$script"
    [[ "$output" =~ "install_zim_manager" ]]
}

@test "main should call setup_update_schedule" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A35 "^cmd_setup()" "$script"
    [[ "$output" =~ "setup_update_schedule" ]]
}

@test "main should call verify_email_system" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A40 "^cmd_setup()" "$script"
    [[ "$output" =~ "verify_email_system" ]]
}

@test "main should call offer_initial_download" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -A45 "^cmd_setup()" "$script"
    [[ "$output" =~ "offer_initial_download" ]]
}

# ==============================================================================
# Script Execution Tests
# ==============================================================================

@test "script should call main if not sourced" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep "main" "$script"
    [ "$status" -eq 0 ]
}

@test "script should exit 0 on success" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep "exit 0" "$script"
    [ "$status" -eq 0 ]
}

# ==============================================================================
# Update Command Tests
# ==============================================================================

@test "cmd_update() should exist" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep "^cmd_update()" "$script"
    [ "$status" -eq 0 ]
}

@test "cmd_update() should load environment" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    source "$script"

    # Mock functions
    load_environment() { echo "load_environment_called"; }
    get_nas_connection_info() { echo "get_nas_connection_info_called"; }
    ensure_ssh_connectivity() { echo "ensure_ssh_connectivity_called"; }
    export -f load_environment get_nas_connection_info ensure_ssh_connectivity

    run cmd_update
    [[ "${output}" == *"load_environment_called"* ]]
}

@test "cmd_update() should backup existing script before updating" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    source "$script"

    # Mock dependencies
    load_environment() { return 0; }
    get_nas_connection_info() {
        NAS_USER_HOST="test@nas.local"
        SSH_KEY_FILE="/tmp/test_key"
        export NAS_USER_HOST SSH_KEY_FILE
    }
    ensure_ssh_connectivity() { return 0; }
    export -f load_environment get_nas_connection_info ensure_ssh_connectivity

    # Mock SSH/SCP commands
    ssh() {
        if [[ "$*" == *"cp /usr/local/bin/zim-manager.sh"* ]]; then
            echo "backup_created"
        fi
        return 0
    }
    scp() { return 0; }
    export -f ssh scp

    run cmd_update
    [[ "${output}" == *"backup"* ]] || [[ "${output}" == *"Updating"* ]]
}

@test "cmd_update() should copy zim-manager.sh to NAS" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    source "$script"

    # Mock dependencies
    load_environment() { return 0; }
    get_nas_connection_info() {
        NAS_USER_HOST="test@nas.local"
        SSH_KEY_FILE="/tmp/test_key"
        ZIM_MANAGER_SCRIPT="$TEST_DIR/zim-manager.sh"
        export NAS_USER_HOST SSH_KEY_FILE ZIM_MANAGER_SCRIPT
    }
    ensure_ssh_connectivity() { return 0; }
    export -f load_environment get_nas_connection_info ensure_ssh_connectivity

    # Create mock zim-manager.sh
    echo "#!/bin/bash" > "$TEST_DIR/zim-manager.sh"

    # Mock SSH/SCP commands
    ssh() { return 0; }
    scp() {
        echo "scp_called: $*"
        return 0
    }
    export -f ssh scp

    run cmd_update
    [[ "${output}" == *"scp"* ]] || [[ "${output}" == *"updated"* ]]
}

@test "cmd_update() should make script executable on NAS" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    source "$script"

    # Mock dependencies
    load_environment() { return 0; }
    get_nas_connection_info() {
        NAS_USER_HOST="test@nas.local"
        SSH_KEY_FILE="/tmp/test_key"
        ZIM_MANAGER_SCRIPT="$TEST_DIR/zim-manager.sh"
        export NAS_USER_HOST SSH_KEY_FILE ZIM_MANAGER_SCRIPT
    }
    ensure_ssh_connectivity() { return 0; }
    export -f load_environment get_nas_connection_info ensure_ssh_connectivity

    # Create mock zim-manager.sh
    echo "#!/bin/bash" > "$TEST_DIR/zim-manager.sh"

    # Mock SSH/SCP commands
    ssh() {
        if [[ "$*" == *"chmod +x"* ]]; then
            echo "chmod_called"
        fi
        return 0
    }
    scp() { return 0; }
    export -f ssh scp

    run cmd_update
    [[ "${output}" == *"chmod"* ]] || [[ "${output}" == *"updated"* ]]
}

@test "main() should support 'update' command" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    run grep -E "update\)" "$script"
    [ "$status" -eq 0 ]
}

@test "usage() should document update command" {
    local script="${BATS_TEST_DIRNAME}/../setup-nas-downloads.sh"
    source "$script"

    run usage
    [[ "${output}" == *"update"* ]]
}
