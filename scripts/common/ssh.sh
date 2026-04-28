#!/usr/bin/env bash

if [ -z "${SSH_KEY_FILE:-}" ]; then
    SSH_KEY_FILE="$HOME/.ssh/homelab_rsa"
    echo "Warning: SSH_KEY_FILE not set, defaulting to $SSH_KEY_FILE" >&2
    echo "  Add SSH_KEY_FILE=~/.ssh/homelab_rsa to your .env file to suppress this warning." >&2
fi
SSH_TIMEOUT="${SSH_TIMEOUT:-5}"

export SSH_KEY_FILE
export SSH_TIMEOUT

# check if ssh is installed and working (skip in test mode)
if [ -z "${TEST:-}" ]; then
  if ! command -v ssh &> /dev/null; then
    echo "Error: ssh could not be found"
    exit 1
  fi
fi

# SSH wrapper that uses the SSH key file. It's
# a bit more opinionated than the default ssh command.
# Args:
#   $1: SSH user@hostname
#   $2: Command to run
# Returns:
#   None
ssh_key_auth() {
    local key_file="$SSH_KEY_FILE"
    local timeout_duration="${SSH_TIMEOUT:-5}"

    timeout "$timeout_duration" ssh -i "$key_file" \
        -o StrictHostKeyChecking=accept-new \
        -o PasswordAuthentication=no \
        -o PubkeyAuthentication=yes \
        -o IdentitiesOnly=yes \
        -o ConnectTimeout=5 \
        "$1" "$2"
}

# SSH wrapper that uses ssh-copy-id to copy the SSH key to the remote machine
# Args:
#   $1: SSH user@hostname
# Returns:
#   None
ssh_copy_id() {
    ssh-copy-id -i "$SSH_KEY_FILE" -o PasswordAuthentication=yes "$1"
}

# Execute command on remote host using SSH key authentication
# Args:
#   $1: user@hostname
#   $2: command to execute
# Returns:
#   SSH command exit code
ssh_execute() {
    local user_host="$1"
    local command="$2"
    ssh_key_auth "$user_host" "$command"
}

# Test SSH connectivity to a host
# Args:
#   $1: user@hostname
# Returns:
#   0 if connection successful, 1 otherwise
ssh_test_connection() {
    local user_host="$1"
    ssh_key_auth "$user_host" "exit" 2>/dev/null
}

# Copy SSH key to remote host
# Args:
#   $1: user@hostname
# Returns:
#   ssh-copy-id exit code
ssh_copy_key() {
    local user_host="$1"
    ssh_copy_id "$user_host"
}

# Create directory on remote host
# Args:
#   $1: user@hostname
#   $2: directory path
#   $3: permissions (optional, e.g., 700)
# Returns:
#   SSH command exit code
ssh_create_directory() {
    local user_host="$1"
    local dir_path="$2"
    local permissions="${3:-755}"
    ssh_execute "$user_host" "mkdir -p '$dir_path' && chmod '$permissions' '$dir_path'"
}

# Check if command exists on remote host
# Args:
#   $1: user@hostname
#   $2: command name
# Returns:
#   0 if command exists, 1 otherwise
ssh_command_exists() {
    local user_host="$1"
    local command="$2"
    ssh_execute "$user_host" "command -v '$command'" >/dev/null 2>&1
}

# Copy a file to a remote host via SCP using the SSH key file
# Args:
#   $1: source file path
#   $2: destination (user@host:/path)
# Returns:
#   0 on success, non-zero on failure
scp_copy_file() {
    local src="$1"
    local dest="$2"
    local key_file="$SSH_KEY_FILE"
    local timeout_duration="${SSH_TIMEOUT:-5}"

    timeout "$timeout_duration" scp -i "$key_file" \
        -o StrictHostKeyChecking=accept-new \
        -o PasswordAuthentication=no \
        -o PubkeyAuthentication=yes \
        -o IdentitiesOnly=yes \
        -o ConnectTimeout=5 \
        "$src" "$dest"
}

# Execute a local script on a remote host via SSH
# Args:
#   $1: user@hostname
#   $2: path to local script file
# Returns:
#   SSH command exit code
ssh_execute_script() {
    local user_host="$1"
    local script_file="$2"
    local key_file="$SSH_KEY_FILE"
    local timeout_duration="${SSH_TIMEOUT:-5}"

    timeout "$timeout_duration" ssh -i "$key_file" \
        -o StrictHostKeyChecking=accept-new \
        -o PasswordAuthentication=no \
        -o PubkeyAuthentication=yes \
        -o IdentitiesOnly=yes \
        -o ConnectTimeout=5 \
        "$user_host" bash < "$script_file"
}

# Export all SSH functions so they're available to subshells
export -f ssh_key_auth
export -f ssh_copy_id
export -f ssh_execute
export -f ssh_test_connection
export -f ssh_copy_key
export -f ssh_create_directory
export -f ssh_command_exists
export -f scp_copy_file
export -f ssh_execute_script
