#!/bin/bash
source scripts/ssh.sh


# Parse machine configuration from YAML file
# Args:
#   $1: Key to parse ('manager' or 'workers')
# Returns:
#   Space-separated list of hostnames for the given key
machines_parse() {
    local machines_file="${MACHINES_FILE:-$PROJECT_ROOT/machines.yml}"
    if [ ! -f "$machines_file" ]; then
        echo "Error: Machines file not found at $machines_file" >&2
        return 1
    fi

    local key=$1
    if [ "$key" = "manager" ]; then
        key='.machines[] | select(.role == "manager") | .host'
    elif [ "$key" = "workers" ]; then
        key='.machines[] | select(.role == "worker") | .host'
    elif [ "$key" = "all" ]; then
        key='.machines[] | .host'
    fi

    # Run yq and capture both stdout and stderr
    local output
    output=$(yq "$key" "$machines_file" 2>&1)

    # Check yq exit status
    if [ $? -ne 0 ]; then
        echo "Error: Invalid YAML in $machines_file" >&2
        echo "$output" >&2
        return 1
    fi

    echo "$output" | tr '\n' ' ' | tr -d '"' | sed 's/ $//'
}


# Get SSH user for a given hostname
# Args:
#   $1: Hostname to get SSH user for
# Returns:
#   SSH user for the given hostname
machines_get_ssh_user() {
    local host=$1
    local machines_file="${MACHINES_FILE:-$PROJECT_ROOT/machines.yml}"

    if [ ! -f "$machines_file" ]; then
        echo "Error: Machines file not found at $machines_file" >&2
        return 1
    fi

    local user
    # Strip quotes from output since yq adds them
    user=$(yq ".machines[] | select(.host == \"$host\") | .ssh_user" "$machines_file" | tr -d '"')

    # Handle case where host isn't found - yq will output empty string
    if [ -z "$user" ]; then
        echo "null"
        return 0
    fi

    echo "$user"
}

# The current machine's IP address
machines_my_ip() {
    local ip=$(ip route get 1 | awk '{print $(NF-2);exit}')
    echo "$ip"
}

# Check if SSH is already configured for a host (without timeout)
# Args:
#   $1: Hostname to check
#   $2: SSH user for the host
# Returns:
#   0 if SSH key authentication works, 1 otherwise
machines_is_ssh_configured_no_timeout() {
    local host=$1
    local ssh_user=$2

    # Try to connect with key auth - if it works, SSH is already configured
    if ssh_key_auth "$ssh_user@$host" exit 2>/dev/null; then
        return 0  # SSH is configured
    else
        return 1  # SSH needs setup
    fi
}

# Check if SSH is already configured for a host
# Args:
#   $1: Hostname to check
#   $2: SSH user for the host
#   $3: Optional "debug" to show SSH command output
# Returns:
#   0 if SSH key authentication works, 1 otherwise
machines_is_ssh_configured() {
    local host=$1
    local ssh_user=$2
    local debug_mode=$3
    local timeout_duration="${SSH_TIMEOUT:-5}"

    # Use the SSH command directly with timeout built into ssh_key_auth function
    # ssh_key_auth already has its own timeout, so we don't need external timeout
    if [ "$debug_mode" = "debug" ]; then
        # Show SSH output for debugging - don't suppress stderr
        if ssh_key_auth "$ssh_user@$host" exit; then
            return 0  # SSH is configured
        else
            return 1  # SSH needs setup
        fi
    else
        # Normal operation - suppress output
        if machines_is_ssh_configured_no_timeout "$host" "$ssh_user"; then
            return 0  # SSH is configured
        else
            return 1  # SSH needs setup
        fi
    fi
}

# Get IP address for a given hostname
# Args:
#   $1: Hostname or IP address to resolve
# Returns:
#   IP address of the host
# Exits with error if hostname cannot be resolved
machines_get_host_ip() {
    local host=$1

    # Check if host is already an IP address
    if [[ $host =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        # Validate IP address format
        local IFS='.'
        read -ra octets <<< "$host"
        for octet in "${octets[@]}"; do
            if [ "$octet" -gt 255 ] || [ "$octet" -lt 0 ]; then
                echo "Error: Invalid IP address format: $host" >&2
                return 1
            fi
        done
        echo "$host"
        return
    fi

    # Otherwise resolve hostname to IP
    local ip
    ip=$(getent hosts "$host" | awk '{ print $1 }')

    if [ -z "$ip" ]; then
        echo "Error: Could not resolve IP for host: $host" >&2
        return 1
    fi

    echo "$ip"
}

# Set up SSH access to all machines
# Generates SSH key if needed and copies to all hosts
# No args
# Returns:
#   None
machines_setup_ssh() {
    local key_file="$SSH_KEY_FILE"
    local current_machine_ip=$(machines_my_ip)

    # Generate SSH key if it doesn't exist
    if [ ! -f "$key_file" ]; then
        echo "Generating new SSH key at $key_file..."
        if ! ssh-keygen -t rsa -b 4096 -f "$key_file" -N ""; then
            echo "Failed to generate SSH key" >&2
            return 1
        fi
    fi

    # Fix local key file permissions
    chmod 600 "$key_file"
    chmod 644 "${key_file}.pub"

    # Get all hosts
    local hosts
    hosts="$(machines_parse all)"

    for host in $hosts; do
        local current_host_ip=$(machines_get_host_ip "$host")
        # Skip if this is the local machine
        if [[ "$host" == "$current_machine_ip" || "$current_host_ip" == "$current_machine_ip" || "$host" == "localhost" || "$host" == "127.0.0.1" ]]; then
            echo "Skipping SSH setup for local machine: $host"
            continue
        fi

        local ssh_user
        ssh_user=$(machines_get_ssh_user "$host")
        if [ "$ssh_user" = "null" ]; then
            ssh_user=${USER}
            echo "No SSH user specified for $host, using current user: $ssh_user"
        fi

        # Check if SSH is already configured for this host
        if machines_is_ssh_configured "$host" "$ssh_user"; then
            echo "Skipping SSH setup for already configured host: $host"
            continue
        fi

        echo "Setting up SSH access for $host (user: $ssh_user)..."

        # Create .ssh directory with correct permissions on remote host
        if ! ssh_password_auth "$ssh_user@$host" \
            "mkdir -p ~/.ssh && chmod 700 ~/.ssh"; then
            echo "Failed to create/fix permissions on .ssh directory for $host" >&2
            return 1
        fi

        # Copy SSH key and set permissions
        if ! ssh_copy_id "$ssh_user@$host"; then
            echo "Failed to copy SSH key to $host" >&2
            return 1
        fi

        # Verify and fix permissions on authorized_keys
        if ! ssh_key_auth "$ssh_user@$host" \
            "chmod 600 ~/.ssh/authorized_keys"; then
            echo "Failed to fix permissions on authorized_keys for $host" >&2
            return 1
        fi

        # Test the connection
        if ! ssh_key_auth "$ssh_user@$host" exit; then
            echo "Failed to verify SSH key access to $host" >&2
            return 1
        fi

        echo "✓ Successfully set up SSH access for $host"
    done

    echo "SSH setup completed successfully for all hosts"
}


# TODO: This does not work when trying to connect to another machine
# Test SSH connectivity to all machines
# No args
# Returns:
#   None, but prints connection status for each host
machines_test_connection() {
    local hosts
    hosts="$(machines_parse workers)"
    local timeout=$SSH_TIMEOUT
    for host in $hosts; do
        local ssh_user
        ssh_user="$(machines_get_ssh_user "$host")"
        echo "Testing connection to $host..."
        if timeout "$timeout" bash -c "ssh_key_auth \"$ssh_user@$host\" exit"; then
            echo "✓ Successfully connected to $host"
        else
            local status=$?
            if [ $status -eq 124 ]; then
                echo "Connection timed out for $host" >&2
                return 1
            fi
            echo "✗ Failed to connect to $host"
            return 1
        fi
    done
}
