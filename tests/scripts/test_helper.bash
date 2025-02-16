#!/usr/bin/env bash

# Helper function to create temporary directory
temp_make() {
    mktemp -d
}

# Helper function to delete temporary directory
temp_del() {
    rm -rf "$1"
}

# Load bats libraries if they exist
if [ -d "/usr/lib/bats/bats-support" ]; then
    load '/usr/lib/bats/bats-support/load.bash'
    load '/usr/lib/bats/bats-assert/load.bash'
fi
