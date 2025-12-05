#!/usr/bin/env bash

# Load bats-support and bats-assert
# Get the directory of the test_helper file
TEST_HELPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
load "$TEST_HELPER_DIR/../../helpers/bats-support/load"
load "$TEST_HELPER_DIR/../../helpers/bats-assert/load"

# Helper function to create temporary directory
temp_make() {
    mktemp -d
}

# Helper function to delete temporary directory
# More robust version that handles edge cases
temp_del() {
    if [[ -n "$1" && -d "$1" ]]; then
        rm -rf "$1" 2>/dev/null || true
    fi
}
