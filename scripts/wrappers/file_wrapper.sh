#!/bin/bash

# File wrapper interface to enable testing by abstracting file operations
# This allows us to easily substitute file operations in tests

# Check if file exists
# Args:
#   $1: file path
# Returns:
#   0 if file exists, 1 otherwise
file_exists() {
    local file_path="$1"
    [ -f "$file_path" ]
}

# Check if directory exists
# Args:
#   $1: directory path
# Returns:
#   0 if directory exists, 1 otherwise
dir_exists() {
    local dir_path="$1"
    [ -d "$dir_path" ]
}

# Read file contents
# Args:
#   $1: file path
# Returns:
#   file contents to stdout, or error message to stderr
file_read() {
    local file_path="$1"
    if [ ! -f "$file_path" ]; then
        echo "Error: File not found: $file_path" >&2
        return 1
    fi
    cat "$file_path"
}

# Write content to file
# Args:
#   $1: file path
#   $2: content
# Returns:
#   0 on success, 1 on error
file_write() {
    local file_path="$1"
    local content="$2"
    echo "$content" > "$file_path"
}

# Append content to file
# Args:
#   $1: file path
#   $2: content
# Returns:
#   0 on success, 1 on error
file_append() {
    local file_path="$1"
    local content="$2"
    echo "$content" >> "$file_path"
}

# Create directory if it doesn't exist
# Args:
#   $1: directory path
# Returns:
#   0 on success, 1 on error
dir_create() {
    local dir_path="$1"
    mkdir -p "$dir_path"
}

# Remove file
# Args:
#   $1: file path
# Returns:
#   0 on success, 1 on error
file_remove() {
    local file_path="$1"
    rm -f "$file_path"
}

# Remove directory
# Args:
#   $1: directory path
#   $2: additional flags (optional, e.g., -rf)
# Returns:
#   0 on success, 1 on error
dir_remove() {
    local dir_path="$1"
    local flags="${2:--rf}"
    rm "$flags" "$dir_path"
}

# Get file modification time
# Args:
#   $1: file path
# Returns:
#   modification time to stdout
file_mtime() {
    local file_path="$1"
    stat -c %Y "$file_path" 2>/dev/null
}

# Check if file is readable
# Args:
#   $1: file path
# Returns:
#   0 if readable, 1 otherwise
file_readable() {
    local file_path="$1"
    [ -r "$file_path" ]
}

# Check if file is writable
# Args:
#   $1: file path
# Returns:
#   0 if writable, 1 otherwise
file_writable() {
    local file_path="$1"
    [ -w "$file_path" ]
}

# Export all functions for use in other scripts
export -f file_exists
export -f dir_exists
export -f file_read
export -f file_write
export -f file_append
export -f dir_create
export -f file_remove
export -f dir_remove
export -f file_mtime
export -f file_readable
export -f file_writable
