#!/bin/bash

# Certificate management functions
# Handles validation of SSL certificate files

# Validate that certificate files exist and are not empty
# Args:
#   $1: Directory containing cert.pem and key.pem
# Returns:
#   0 if valid, 1 if invalid
cert_validate_files() {
    local cert_dir="$1"

    if [ ! -f "$cert_dir/cert.pem" ]; then
        echo "Error: Certificate file not found: $cert_dir/cert.pem" >&2
        return 1
    fi

    if [ ! -f "$cert_dir/key.pem" ]; then
        echo "Error: Private key file not found: $cert_dir/key.pem" >&2
        return 1
    fi

    if [ ! -s "$cert_dir/cert.pem" ]; then
        echo "Error: Certificate file is empty: $cert_dir/cert.pem" >&2
        return 1
    fi

    if [ ! -s "$cert_dir/key.pem" ]; then
        echo "Error: Private key file is empty: $cert_dir/key.pem" >&2
        return 1
    fi

    return 0
}

# Export functions
export -f cert_validate_files
