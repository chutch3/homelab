#!/bin/bash

# Define project paths
PROJECT_ROOT="$PWD"
export AVAILABLE_DIR="$PROJECT_ROOT/reverseproxy/templates/conf.d"
export ENABLED_DIR="$PROJECT_ROOT/reverseproxy/templates/conf.d/enabled"
export SSL_DIR="$PROJECT_ROOT/reverseproxy/ssl"
export DOMAIN_FILE="$PROJECT_ROOT/.domains"

# Helper function to check if command exists
command_exists() {
    declare -F "$1" > /dev/null
}

# List available commands for a target
list_commands() {
    local target="$1"
    declare -F | cut -d' ' -f3 | grep "^${target}_" | sed "s/^${target}_//"
}

# Common functions used across deployment targets
load_env() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo "❌ Error: .env file not found in $PROJECT_ROOT"
        exit 1
    fi

    source "$PROJECT_ROOT/.env"
}

# Function: expand_env_variables
# Description: Expands ${VAR_NAME} references in a string using .env file and current environment
# Arguments: $1 - string with potential ${VAR} references
# Returns: String with variables expanded
expand_env_variables() {
    local input="$1"

    # Load .env file if it exists (suppress readonly variable errors)
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        # Source .env file in a subshell to avoid polluting current environment
        # shellcheck source=/dev/null
        source "$PROJECT_ROOT/.env" 2>/dev/null || true
    fi

    # Use eval to let the shell do the variable expansion
    # This is the most reliable approach across different shells
    eval "echo \"$input\""
}

# Function: load_and_expand_homelab_config
# Description: Loads homelab.yaml and expands all environment variables
# Arguments: $1 - path to homelab.yaml
# Returns: Outputs expanded YAML to stdout
load_and_expand_homelab_config() {
    local config_file="$1"

    if [[ ! -f "$config_file" ]]; then
        echo "Error: Configuration file not found: $config_file" >&2
        return 1
    fi

    # Load .env file if it exists
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        # shellcheck source=/dev/null
        source "$PROJECT_ROOT/.env"
    fi

    # Process the YAML file line by line to expand variables
    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
            echo "$line"
            continue
        fi

        # Expand environment variables in the line
        expanded_line=$(expand_env_variables "$line")
        echo "$expanded_line"
    done < "$config_file"
}

ensure_certs_exist() {
    # check if certs are already initialized
    if [ -d "$PROJECT_ROOT/certs" ]; then
        echo "✅ Certificates are already initialized"
        return
    fi

    load_env

    docker compose up --build -d acme
    docker exec -it acme.sh /bin/sh -c "acme.sh --upgrade"
    docker exec --env-file .env -it acme.sh /bin/sh -c "acme.sh --issue --dns dns_cf -d ${BASE_DOMAIN} -d ${WILDCARD_DOMAIN} --server letsencrypt || true"
}

list_available_services() {
    # Common service listing logic
    echo "Available services:"
}

sync-files() {
    read -r -p "What is your username on the remote server? " remote_user
    read -r -p "What is the hostname or IP address of the remote server? " remote_host
    read -r -p "What is the full path to the files you want to sync on the remote server? " remote_path
    read -r -p "Where would you like to save the files locally? (Press Enter for current directory) " local_path
    local_path=${local_path:-"."}

    # Create local directory if it doesn't exist
    mkdir -p "${local_path}"

    # Use scp instead of sftp for recursive copy
    if scp -r "${remote_user}@${remote_host}:${remote_path}" "${local_path}"; then
        echo "✅ Files synchronized successfully!"
    else
        echo "❌ Failed to sync files"
    fi
}
