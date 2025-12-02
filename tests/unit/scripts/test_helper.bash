#!/usr/bin/env bash

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
