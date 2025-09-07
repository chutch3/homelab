#!/bin/bash

# Get the actual script directory, handling both direct execution and sourcing
MACHINES_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/ssh.sh
source "$MACHINES_SCRIPT_DIR/ssh.sh"

# --- Colors and Logging ---
COLOR_RESET='\033[0m'
COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_BLUE='\033[0;34m'

log() {
  echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $1"
}
log_success() {
  echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $1"
}
log_warn() {
  echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1"
}
log_error() {
  echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1" >&2
}


# Parse machine configuration from YAML file
# Args:
#   $1: Key to parse ('manager' or 'workers')
# Returns:
#   Space-separated list of machine keys for the given key
machines_parse() {
    local machines_file="${MACHINES_FILE:-$PROJECT_ROOT/machines.yaml}"
    if [ ! -f "$machines_file" ]; then
        log_error "Machines file not found at $machines_file"
        return 1
    fi

    local key=$1
    local yq_query=""

    if [ "$key" = "manager" ]; then
        yq_query='.machines | to_entries[] | select(.value.role == "manager") | .key'
    elif [ "$key" = "workers" ]; then
        yq_query='.machines | to_entries[] | select(.value.role == "worker") | .key'
    elif [ "$key" = "swarm" ]; then
        # All machines that should be part of swarm (default true for backward compatibility)
        yq_query='.machines | to_entries[] | select(.value.swarm_node == true or (.value.swarm_node == null and true)) | .key'
    elif [ "$key" = "all" ]; then
        yq_query='.machines | keys | .[]'
    else
        log_error "Invalid key '$key'. Use 'manager', 'workers', 'swarm', or 'all'"
        return 1
    fi

    # Run yq and capture both stdout and stderr
    local output
    # Check yq exit status
    if ! output=$(yq "$yq_query" "$machines_file" 2>&1); then
        log_error "Invalid YAML in $machines_file"
        echo "$output" >&2
        return 1
    fi

    echo "$output" | tr '\n' ' ' | tr -d '"' | sed 's/ $//'
}


# Get SSH user for a given machine key
# Args:
#   $1: Machine key to get SSH user for (e.g., "driver", "node-01")
# Returns:
#   SSH user for the given machine key
machines_get_ssh_user() {
    local machine_key=$1
    local machines_file="${MACHINES_FILE:-$PROJECT_ROOT/machines.yaml}"

    if [ ! -f "$machines_file" ]; then
        log_error "Machines file not found at $machines_file"
        return 1
    fi

    local user
    # Use machine key to get ssh_user directly from the new structure
    user=$(yq ".machines[\"$machine_key\"] .ssh_user" "$machines_file" 2>/dev/null | tr -d '"')

    # Fallback to .user for backward compatibility
    if [ -z "$user" ] || [ "$user" = "null" ]; then
        user=$(yq ".machines[\"$machine_key\"] .user" "$machines_file" 2>/dev/null | tr -d '"')
    fi

    # Handle case where machine key isn't found or user is not set
    if [ -z "$user" ] || [ "$user" = "null" ]; then
        echo "null"
        return 0
    fi

    echo "$user"
}

# Build hostname from machine key and BASE_DOMAIN
# Args:
#   $1: Machine key (e.g., "manager", "node-01")
# Returns:
#   Full hostname (e.g., "manager.diyhub.dev")
machines_build_hostname() {
    local machine_key="$1"

    if [ -z "$machine_key" ]; then
        log_error "Machine key parameter is required"
        return 1
    fi

    echo "${machine_key}.${BASE_DOMAIN:-}"
}

# Format machine display string for consistent logging
# Args:
#   $1: Machine key (e.g., "manager", "node-01")
#   $2: Machine IP (e.g., "192.168.1.100")
# Returns:
#   Formatted string: "machine_key (ip_address)"
machines_format_display() {
    local machine_key="$1"
    local machine_ip="$2"
    echo "$machine_key ($machine_ip)"
}

# The current machine's IP address
machines_my_ip() {
    local ip
    ip=$(ip route get 1 | awk '{print $(NF-2);exit}')
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

# Get IP address for a given machine key or hostname, preferring IP field from machines.yaml
# Args:
#   $1: Machine key (e.g. "manager") or hostname (e.g. "manager.diyhub.dev") to resolve
# Returns:
#   IP address of the machine from machines.yaml IP field, or hostname resolution
#   Exits with error if machine cannot be resolved
machines_get_ip() {
    local input="$1"
    local machines_file="${MACHINES_FILE:-$PROJECT_ROOT/machines.yaml}"

    # Validate input
    if [ -z "$input" ]; then
        log_error "Machine key or hostname parameter is required"
        return 1
    fi

    if [ ! -f "$machines_file" ]; then
        log_error "Machines file not found at $machines_file"
        return 1
    fi

    local machine_key=""

    # First, try to find a machine by role if the input is "manager" or "workers"
    if [ "$input" = "manager" ] || [ "$input" = "workers" ]; then
        machine_key=$(machines_parse "$input")
    fi

    # If we didn't find a machine by role, or the input was not a role,
    # treat the input as a key.
    if [ -z "$machine_key" ]; then
        if [[ "$input" =~ \. ]]; then
            machine_key="${input%%\."${BASE_DOMAIN:-}"*}"
        else
            machine_key="$input"
        fi
    fi

    # Try to get IP from machines.yaml IP field using machine key
    local ip_field
    if ! ip_field=$(yq ".machines[\"${machine_key}\"].ip" "$machines_file" 2>/dev/null | tr -d '"'); then
        log_error "Failed to parse machines.yaml"
        return 1
    fi

    # Use IP field if present and valid
    if [ -n "$ip_field" ] && [ "$ip_field" != "null" ] && [ "$ip_field" != "" ]; then
        echo "$ip_field"
        return 0
    fi

    # Fallback to hostname resolution
    # If input was a machine key, construct the hostname
    local hostname
    if [[ "$input" =~ \. ]]; then
        hostname="$input"
    else
        hostname=$(machines_build_hostname "$machine_key")
    fi

    machines_get_host_ip "$hostname"
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
        # Validate IP address format by checking each octet
        local octet1 octet2 octet3 octet4
        IFS='.' read -r octet1 octet2 octet3 octet4 <<< "$host"

        for octet in "$octet1" "$octet2" "$octet3" "$octet4"; do
            # Check if it's a valid number first
            if ! [[ "$octet" =~ ^[0-9]+$ ]]; then
                log_error "Invalid IP address format: $host"
                return 1
            fi
            # Check if octet is in valid range (0-255)
            if [ "$octet" -gt 255 ]; then
                log_error "Invalid IP address format: $host"
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
        log_error "Could not resolve IP for host: $host"
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
    local current_machine_ip
    current_machine_ip=$(machines_my_ip)

    # Generate SSH key if it doesn't exist
    if [ ! -f "$key_file" ]; then
        echo "Generating new SSH key at $key_file..."
        if ! ssh-keygen -t rsa -b 4096 -f "$key_file" -N ""; then
            log_error "Failed to generate SSH key"
            return 1
        fi
    fi

    # Fix local key file permissions
    chmod 600 "$key_file"
    chmod 644 "${key_file}.pub"

    # Get all machine keys
    local machine_keys
    machine_keys="$(machines_parse all)"

    for machine_key in $machine_keys; do
        # IP-first approach: Use direct IP connections to avoid DNS dependency
        local machine_ip
        machine_ip=$(machines_get_ip "$machine_key")
        local display_name
        display_name=$(machines_format_display "$machine_key" "$machine_ip")

        # Skip if this is the local machine
        if [[ "$machine_ip" == "$current_machine_ip" || "$machine_ip" == "localhost" || "$machine_ip" == "127.0.0.1" ]]; then
            log "Skipping SSH setup for local machine: $display_name"
            continue
        fi

        local ssh_user
        ssh_user="$(machines_get_ssh_user "$machine_key")"
        if [ "$ssh_user" = "null" ]; then
            ssh_user=${USER}
            log_warn "No SSH user specified for $machine_key, using current user: $ssh_user"
        fi

        # Check if SSH key authentication is already working for this IP
        if machines_is_ssh_configured "$machine_ip" "$ssh_user" "debug"; then
            log "Skipping SSH setup for already configured machine: $display_name"
            continue
        fi

        log "Setting up SSH access for $display_name (user: $ssh_user)..."

        # Create .ssh directory with correct permissions on remote host
        if ! ssh_password_auth "$ssh_user@$machine_ip" \
            "mkdir -p ~/.ssh && chmod 700 ~/.ssh"; then
            log_error "Failed to create/fix permissions on .ssh directory for $display_name"
            return 1
        fi

        # Copy SSH key and set permissions
        if ! ssh_copy_id "$ssh_user@$machine_ip"; then
            log_error "Failed to copy SSH key to $display_name"
            return 1
        fi

        # Verify and fix permissions on authorized_keys
        if ! ssh_key_auth "$ssh_user@$machine_ip" \
            "chmod 600 ~/.ssh/authorized_keys"; then
            log_error "Failed to fix permissions on authorized_keys for $display_name"
            return 1
        fi

        # Test the connection
        if ! ssh_key_auth "$ssh_user@$machine_ip" exit; then
            log_error "Failed to verify SSH key access to $display_name"
            return 1
        fi

        log_success "✓ Successfully set up SSH access for $display_name"
    done

    echo "SSH setup completed successfully for all hosts"
}


# TODO: This does not work when trying to connect to another machine
# Test SSH connectivity to all machines
# No args
# Returns:
#   None, but prints connection status for each machine
machines_test_connection() {
    local machine_keys
    machine_keys="$(machines_parse workers)"
    local timeout=$SSH_TIMEOUT
    for machine_key in $machine_keys; do
        local machine_ip
        machine_ip=$(machines_get_ip "$machine_key")
        local display_name
        display_name=$(machines_format_display "$machine_key" "$machine_ip")
        local ssh_user
        ssh_user="$(machines_get_ssh_user "$machine_key")"

        echo "Testing connection to $display_name..."
        if timeout "$timeout" bash -c "ssh_key_auth \"$ssh_user@$machine_ip\" exit"; then
            echo "✓ Successfully connected to $display_name"
        else
            local status=$?
            if [ $status -eq 124 ]; then
                log_error "Connection timed out for $display_name"
                return 1
            fi
            echo "✗ Failed to connect to $display_name"
            return 1
        fi
    done
}


machines_check_cifs_utils() {
    # Set longer SSH timeout for package installation
    export SSH_TIMEOUT=120

    local current_machine_ip
    current_machine_ip=$(machines_my_ip)
    local machine_keys

    machine_keys="$(machines_parse all)"
    # Removed verbose header message - let calling script handle headers
    for machine_key in $machine_keys; do
        local machine_ip
        machine_ip=$(machines_get_ip "$machine_key")
        local display_name
        display_name=$(machines_format_display "$machine_key" "$machine_ip")

        # Check cifs-utils silently, only log issues

        # Skip if this is the local machine
        if [ "$machine_ip" == "$current_machine_ip" ]; then
            # Running locally - check silently
            if ! which mount.cifs >/dev/null 2>&1; then
                log "Installing cifs-utils on $machine_key..."
                log "DEBUG: Running local sudo command: sudo -n apt-get update && sudo -n apt-get install -y cifs-utils"

                # Run install command with timeout and enhanced error capture
                local local_install_output local_install_exit
                local_install_output=$(timeout 60 bash -c 'sudo -n apt-get update 2>&1 && sudo -n apt-get install -y cifs-utils 2>&1' 2>&1)
                local_install_exit=$?

                log "DEBUG: Local install exit code: $local_install_exit"
                log "DEBUG: Local install output: $local_install_output"

                # Test individual commands if failed
                if [ $local_install_exit -ne 0 ]; then
                    log "DEBUG: Testing local individual commands..."
                    local local_update_test
                    local_update_test=$(timeout 30 sudo -n apt-get update 2>&1)
                    log "DEBUG: Local apt-get update result: $local_update_test"

                    local local_install_test
                    local_install_test=$(timeout 30 sudo -n apt-get install -y cifs-utils 2>&1)
                    log "DEBUG: Local apt-get install result: $local_install_test"
                fi

                if [ $local_install_exit -eq 0 ]; then
                    log_success "cifs-utils installed on $machine_key"
                else
                    log_error "Failed to install cifs-utils on $machine_key"
                    log_error "Local install error: $local_install_output"
                    return 1
                fi
            fi
            continue
        fi

        # Check remote machine silently
        local ssh_user
        ssh_user="$(machines_get_ssh_user "$machine_key")"
        if ! ssh_key_auth "$ssh_user@$machine_ip" "which mount.cifs >/dev/null 2>&1"; then
            log "Installing cifs-utils on $display_name..."
            if ssh_key_auth "$ssh_user@$machine_ip" "sudo -n apt-get update >/dev/null 2>&1 && sudo -n apt-get install -y cifs-utils >/dev/null 2>&1"; then
                log_success "cifs-utils installed on $display_name"
            else
                log_error "Failed to install cifs-utils on $display_name"
                return 1
            fi
        fi
        # Already installed - no need to log
    done
    log_success "cifs-utils verification complete on all machines"
    return 0
}
