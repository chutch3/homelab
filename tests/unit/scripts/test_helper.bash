#!/usr/bin/env bash

# Helper function to create temporary directory
temp_make() {
    mktemp -d
}

# Helper function to delete temporary directory
temp_del() {
    rm -rf "$1"
}
