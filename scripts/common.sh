#!/bin/bash

# Define project paths
PROJECT_ROOT="$PWD"
AVAILABLE_DIR="$PROJECT_ROOT/reverseproxy/templates/conf.d"
ENABLED_DIR="$PROJECT_ROOT/reverseproxy/templates/conf.d/enabled"
SSL_DIR="$PROJECT_ROOT/reverseproxy/ssl"
DOMAIN_FILE="$PROJECT_ROOT/.domains"

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
