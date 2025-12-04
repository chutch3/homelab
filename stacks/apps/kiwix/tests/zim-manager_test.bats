#!/usr/bin/env bats
# shellcheck disable=SC2076,SC2317,SC2155,SC1091
# SC2076: Quotes in regex are intentional for literal matching in tests
# SC2317: Mock functions appear unreachable but are invoked by sourced scripts
# SC2155: Declare and assign on same line is acceptable in tests for readability
# SC1091: Sourced file path is relative and verified at runtime

# ==============================================================================
# Test Setup and Helpers
# ==============================================================================

setup() {
    # Create test directory structure
    export TEST_DIR="$(mktemp -d)"
    export ZIM_DATA_DIR="$TEST_DIR/data"
    export ZIM_LOG_DIR="$TEST_DIR/logs"
    export EMAIL_TO="test@example.com"

    mkdir -p "$ZIM_DATA_DIR" "$ZIM_LOG_DIR"

    # Source the script to get functions (but don't run main logic)
    export BATS_TEST_MODE=1
    source "${BATS_TEST_DIRNAME}/../zim-manager.sh" 2>/dev/null || true

    # Mock external commands by creating functions
    # These will be overridden in individual tests
    cmd_wget() { echo "MOCK: wget $*" >> "$TEST_DIR/commands.log"; return 0; }
    cmd_sha256sum() { echo "MOCK: sha256sum $*" >> "$TEST_DIR/commands.log"; return 0; }
    cmd_mail() { echo "MOCK: mail $*" >> "$TEST_DIR/commands.log"; return 0; }
    cmd_sed() { echo "MOCK: sed $*" >> "$TEST_DIR/commands.log"; return 0; }
    cmd_mv() { echo "MOCK: mv $*" >> "$TEST_DIR/commands.log"; return 0; }
    cmd_rm() { echo "MOCK: rm $*" >> "$TEST_DIR/commands.log"; return 0; }
    cmd_date() { echo "2025-12-03 12:00:00"; }

    export -f cmd_wget cmd_sha256sum cmd_mail cmd_sed cmd_mv cmd_rm cmd_date
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ==============================================================================
# Script Structure Tests
# ==============================================================================

@test "zim-manager.sh should exist and be executable" {
    [ -f "${BATS_TEST_DIRNAME}/../zim-manager.sh" ]
    [ -x "${BATS_TEST_DIRNAME}/../zim-manager.sh" ]
}

@test "zim-manager.sh should have bash shebang" {
    run head -n 1 "${BATS_TEST_DIRNAME}/../zim-manager.sh"
    [[ "$output" =~ ^#!/.*bash ]]
}

@test "zim-manager.sh should use strict error handling" {
    run grep "set -euo pipefail" "${BATS_TEST_DIRNAME}/../zim-manager.sh"
    [ "$status" -eq 0 ]
}

# ==============================================================================
# Command Wrapper Tests
# ==============================================================================

@test "script should define cmd_wget wrapper" {
    run grep "^cmd_wget()" "${BATS_TEST_DIRNAME}/../zim-manager.sh"
    [ "$status" -eq 0 ]
}

@test "script should define cmd_sha256sum wrapper" {
    run grep "^cmd_sha256sum()" "${BATS_TEST_DIRNAME}/../zim-manager.sh"
    [ "$status" -eq 0 ]
}

@test "script should define cmd_mail wrapper" {
    run grep "^cmd_mail()" "${BATS_TEST_DIRNAME}/../zim-manager.sh"
    [ "$status" -eq 0 ]
}

@test "script should define cmd_sed wrapper" {
    run grep "^cmd_sed()" "${BATS_TEST_DIRNAME}/../zim-manager.sh"
    [ "$status" -eq 0 ]
}

@test "script should define cmd_mv wrapper" {
    run grep "^cmd_mv()" "${BATS_TEST_DIRNAME}/../zim-manager.sh"
    [ "$status" -eq 0 ]
}

@test "script should define cmd_rm wrapper" {
    run grep "^cmd_rm()" "${BATS_TEST_DIRNAME}/../zim-manager.sh"
    [ "$status" -eq 0 ]
}

# ==============================================================================
# log() Function Tests - Test Actual Behavior
# ==============================================================================

@test "log() should write timestamped message to log file" {
    LOG_FILE="$TEST_DIR/test.log"

    log "Test message"

    [ -f "$LOG_FILE" ]
    run cat "$LOG_FILE"
    [[ "$output" =~ "Test message" ]]
    [[ "$output" =~ "[" ]]  # Contains timestamp bracket
}

@test "log() should append to existing log file" {
    LOG_FILE="$TEST_DIR/test.log"

    log "First message"
    log "Second message"

    run cat "$LOG_FILE"
    [[ "$output" =~ "First message" ]]
    [[ "$output" =~ "Second message" ]]
    [ "$(wc -l < "$LOG_FILE")" -eq 2 ]
}

# ==============================================================================
# send_email() Function Tests - Test with Mocked mail Command
# ==============================================================================

@test "send_email() should call cmd_mail when mail command exists" {
    # Mock cmd_mail to track calls
    cmd_mail() {
        echo "$*" > "$TEST_DIR/mail_args.txt"
        return 0
    }
    export -f cmd_mail

    # Mock command -v to say mail exists
    command() {
        if [ "$1" = "-v" ] && [ "$2" = "mail" ]; then
            return 0
        fi
        builtin command "$@"
    }
    export -f command

    send_email "Test Subject" "Test Body"

    [ -f "$TEST_DIR/mail_args.txt" ]
    run cat "$TEST_DIR/mail_args.txt"
    [[ "$output" =~ "-s" ]]
    [[ "$output" =~ "Test Subject" ]]
}

@test "send_email() should return 0 when mail succeeds" {
    cmd_mail() { return 0; }
    export -f cmd_mail

    command() {
        if [ "$1" = "-v" ] && [ "$2" = "mail" ]; then return 0; fi
        builtin command "$@"
    }
    export -f command

    run send_email "Subject" "Body"
    [ "$status" -eq 0 ]
}

@test "send_email() should handle missing mail command gracefully" {
    command() {
        if [ "$1" = "-v" ] && [ "$2" = "mail" ]; then return 1; fi
        builtin command "$@"
    }
    export -f command

    run send_email "Subject" "Body"
    [ "$status" -eq 0 ]  # Should not fail, just warn
}

# ==============================================================================
# download_with_verify() Function Tests - Test Actual Download Logic
# ==============================================================================

@test "download_with_verify() should call cmd_wget with correct arguments" {
    cmd_wget() {
        # Capture first call (main file download)
        if [ ! -f "$TEST_DIR/wget_call.txt" ]; then
            echo "wget called with: $*" > "$TEST_DIR/wget_call.txt"
        fi
        # Create mock temp file
        touch "${3}" 2>/dev/null || true  # $3 is the output file from -O flag
        return 0
    }
    export -f cmd_wget

    cmd_sha256sum() { return 1; }  # Skip checksum for this test
    cmd_rm() { return 0; }  # Mock cleanup
    export -f cmd_sha256sum cmd_rm

    download_with_verify "https://example.com/file.zim" "$TEST_DIR/output.zim" || true

    [ -f "$TEST_DIR/wget_call.txt" ]
    run cat "$TEST_DIR/wget_call.txt"
    [[ "$output" =~ "-c" ]]  # Resume flag
    [[ "$output" =~ "-O" ]]  # Output flag
    [[ "$output" =~ "https://example.com/file.zim" ]]
}

@test "download_with_verify() should return 1 when wget fails" {
    cmd_wget() { return 1; }  # Simulate wget failure
    export -f cmd_wget

    run download_with_verify "https://example.com/file.zim" "$TEST_DIR/output.zim"
    [ "$status" -eq 1 ]
}

@test "download_with_verify() should download checksum file" {
    cmd_wget() {
        if [[ "$*" =~ ".sha256" ]]; then
            echo "checksum downloaded" > "$TEST_DIR/checksum_downloaded.txt"
        fi
        touch "${3}" 2>/dev/null || true  # Create temp file
        return 0
    }
    export -f cmd_wget

    cmd_sha256sum() { return 0; }
    cmd_sed() { return 0; }
    cmd_mv() { return 0; }
    cmd_rm() { return 0; }
    export -f cmd_sha256sum cmd_sed cmd_mv cmd_rm

    download_with_verify "https://example.com/file.zim" "$TEST_DIR/output.zim"

    [ -f "$TEST_DIR/checksum_downloaded.txt" ]
}

@test "download_with_verify() should call cmd_sed to fix checksum filename" {
    cmd_wget() {
        touch "${3}" 2>/dev/null || true
        return 0
    }
    cmd_sed() {
        echo "sed called: $*" > "$TEST_DIR/sed_call.txt"
        return 0
    }
    cmd_sha256sum() { return 0; }
    cmd_mv() { return 0; }
    cmd_rm() { return 0; }
    export -f cmd_wget cmd_sed cmd_sha256sum cmd_mv cmd_rm

    download_with_verify "https://example.com/file.zim" "$TEST_DIR/output.zim"

    [ -f "$TEST_DIR/sed_call.txt" ]
    run cat "$TEST_DIR/sed_call.txt"
    [[ "$output" =~ "-i" ]]  # In-place editing
    [[ "$output" =~ ".tmp" ]]  # Should reference temp file
}

@test "download_with_verify() should verify checksum" {
    cmd_wget() {
        touch "${3}" 2>/dev/null || true
        return 0
    }
    cmd_sed() { return 0; }
    cmd_sha256sum() {
        echo "sha256sum called" > "$TEST_DIR/sha256sum_called.txt"
        return 0
    }
    cmd_mv() { return 0; }
    cmd_rm() { return 0; }
    export -f cmd_wget cmd_sed cmd_sha256sum cmd_mv cmd_rm

    download_with_verify "https://example.com/file.zim" "$TEST_DIR/output.zim"

    [ -f "$TEST_DIR/sha256sum_called.txt" ]
}

@test "download_with_verify() should return 1 when checksum verification fails" {
    cmd_wget() {
        touch "${3}" 2>/dev/null || true
        return 0
    }
    cmd_sed() { return 0; }
    cmd_sha256sum() { return 1; }  # Checksum fails
    cmd_rm() { return 0; }
    export -f cmd_wget cmd_sed cmd_sha256sum cmd_rm

    run download_with_verify "https://example.com/file.zim" "$TEST_DIR/output.zim"
    [ "$status" -eq 1 ]
}

@test "download_with_verify() should move temp file to final location on success" {
    cmd_wget() {
        touch "${3}" 2>/dev/null || true
        return 0
    }
    cmd_sed() { return 0; }
    cmd_sha256sum() { return 0; }
    cmd_mv() {
        echo "mv $*" > "$TEST_DIR/mv_call.txt"
        return 0
    }
    cmd_rm() { return 0; }
    export -f cmd_wget cmd_sed cmd_sha256sum cmd_mv cmd_rm

    download_with_verify "https://example.com/file.zim" "$TEST_DIR/output.zim"

    [ -f "$TEST_DIR/mv_call.txt" ]
    run cat "$TEST_DIR/mv_call.txt"
    [[ "$output" =~ ".tmp" ]]
    [[ "$output" =~ "output.zim" ]]
}

@test "download_with_verify() should cleanup temp files on checksum failure" {
    cmd_wget() {
        touch "${3}" 2>/dev/null || true
        return 0
    }
    cmd_sed() { return 0; }
    cmd_sha256sum() { return 1; }  # Fail checksum
    cmd_rm() {
        echo "rm $*" > "$TEST_DIR/rm_call.txt"
        return 0
    }
    export -f cmd_wget cmd_sed cmd_sha256sum cmd_rm

    download_with_verify "https://example.com/file.zim" "$TEST_DIR/output.zim" || true

    [ -f "$TEST_DIR/rm_call.txt" ]
    run cat "$TEST_DIR/rm_call.txt"
    [[ "$output" =~ ".tmp" ]]
}

@test "download_with_verify() should return 0 on complete success" {
    cmd_wget() {
        touch "${3}" 2>/dev/null || true
        return 0
    }
    cmd_sed() { return 0; }
    cmd_sha256sum() { return 0; }
    cmd_mv() { return 0; }
    cmd_rm() { return 0; }
    export -f cmd_wget cmd_sed cmd_sha256sum cmd_mv cmd_rm

    run download_with_verify "https://example.com/file.zim" "$TEST_DIR/output.zim"
    [ "$status" -eq 0 ]
}

@test "download_with_verify() should skip verification if checksum download fails" {
    cmd_wget() {
        # Succeed for main file, fail for checksum
        if [[ "$*" =~ ".sha256" ]]; then
            return 1
        fi
        touch "${3}" 2>/dev/null || true
        return 0
    }
    cmd_mv() { return 0; }
    export -f cmd_wget cmd_mv

    run download_with_verify "https://example.com/file.zim" "$TEST_DIR/output.zim"
    [ "$status" -eq 0 ]  # Should succeed even without checksum
}

# ==============================================================================
# Integration Tests - Test Complete Workflows
# ==============================================================================

@test "download_starter_pack() should iterate through STARTER_PACK array without exiting" {
    # This test verifies the fix for the ((success_count++)) bug with set -e
    # Previously, ((0++)) would return 0, causing set -e to exit the script

    # Mock successful downloads
    cmd_wget() {
        touch "${3}" 2>/dev/null || true
        return 0
    }
    cmd_sha256sum() { return 0; }
    cmd_sed() { return 0; }
    cmd_mv() { return 0; }
    cmd_rm() { return 0; }
    export -f cmd_wget cmd_sha256sum cmd_sed cmd_mv cmd_rm

    # Mock send_email
    send_email() { return 0; }
    export -f send_email

    run download_starter_pack

    # Should complete successfully without exiting early due to set -e
    # This is the KEY test - before the fix, this would return non-zero
    [ "$status" -eq 0 ]
}

@test "check_for_updates() should list current ZIM files" {
    skip "Requires refactored implementation"
}

@test "check_for_updates() should send email report" {
    skip "Requires refactored implementation"
}
