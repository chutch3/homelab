#!/bin/bash

# Define project paths
PROJECT_ROOT="$PWD"
AVAILABLE_DIR="$PROJECT_ROOT/reverseproxy/conf.d/available"
ENABLED_DIR="$PROJECT_ROOT/reverseproxy/conf.d/enabled"
TEMP_DIR="$PROJECT_ROOT/reverseproxy/conf.d/temp"
SSL_DIR="$PROJECT_ROOT/reverseproxy/ssl"
DOMAIN_FILE="$PROJECT_ROOT/.domains"

# Create required directories if they don't exist
mkdir -p "$ENABLED_DIR" "$SSL_DIR"

# Function: build_domains
# Description: Reads domain configurations from .domains file and exports them as environment variables
# Arguments: None
# Returns: None
# Example: build_domains
build_domains() {
    while IFS='=' read -r key value; do
        [[ -z "$key" || "$key" =~ ^# ]] && continue
        value=$(echo "${value}" | envsubst '${BASE_DOMAIN}')
        export "$key=$value"
    done < "$DOMAIN_FILE"
}

# Function: build_subitution_tokens
# Description: Builds a string of domain variable names for envsubst
# Arguments: None
# Returns: Space-separated string of domain variable names in ${VAR} format
# Example: tokens=$(build_subitution_tokens)
build_subitution_tokens() {
    sub_tokens=""
    while IFS='=' read -r key value; do
        [[ -z "$key" || "$key" =~ ^# || "$key" =~ ^BASE_DOMAIN ]] && continue
        sub_tokens="${sub_tokens} \${${key}}"
    done < "$DOMAIN_FILE"
    echo "$sub_tokens"
}

# Function: process_nginx_config
# Description: Processes an nginx configuration file by substituting domain variables
# Arguments:
#   $1 - Configuration file name
# Returns:
#   0 - Success
#   1 - Configuration file not found
# Example: process_nginx_config "myservice.conf"
process_nginx_config() {
    local config=$1
    if [ -f "$AVAILABLE_DIR/$config" ]; then
        build_domains
        sub_tokens=$(build_subitution_tokens)
        envsubst "$sub_tokens" \
            < "$AVAILABLE_DIR/$config" > "$ENABLED_DIR/$config"
        return 0
    else
        echo "Configuration $config not found"
        return 1
    fi
}

# Function: list_available_services
# Description: Lists all available services by scanning the available directory
# Arguments: None
# Returns: None
# Example: list_available_services
list_available_services() {
    AVAILABLE_SERVICES=$(basename -a "$AVAILABLE_DIR"/*.conf | sed 's/\.conf$//' | tr '\n' ' ' | xargs)
    echo "Available services:"
    for service in $AVAILABLE_SERVICES; do
        echo "  - $service"
    done
}

# Function: enable_service
# Description: Enables a service by processing its nginx configuration
# Arguments:
#   $1 - Configuration file name
# Returns: None
# Example: enable_service "myservice.conf"
enable_service() {
    local config=$1
    process_nginx_config $config
    echo "Enabled $config"
}

# Function: disable_service
# Description: Disables a service by removing its nginx configuration
# Arguments:
#   $1 - Configuration file name
# Returns: None
# Example: disable_service "myservice.conf"
disable_service() {
    local config=$1
    if [ -f "$ENABLED_DIR/$config" ]; then
        rm "$ENABLED_DIR/$config"
        echo "Disabled $config"
    else
        echo "Configuration $config not enabled"
    fi
}

# Function: start_enabled_services
# Description: Starts all enabled services and core services using docker compose
# Arguments:
#   $1 - Command (unused)
#   $2 - List of enabled configurations
# Returns: None
# Example: start_enabled_services
start_enabled_services() {
    local enabled_configs=$2
    CORE_SERVICES="reverseproxy"
    SERVICES_TO_START=$(basename -a "$ENABLED_DIR"/*.conf | sed 's/\.conf$//' | tr '\n' ' ' | xargs)
    echo "Starting services: $SERVICES_TO_START"
    docker compose up -d $SERVICES_TO_START
    docker compose up --build -d $CORE_SERVICES
}

# Function: stop_all_services
# Description: Stops all running services and removes containers, orphans, and volumes
# Arguments: None
# Returns: None
# Example: stop_all_services
stop_all_services() {
    docker compose down --remove-orphans --volumes
}

# Function: rebuild_all_services
# Description: Rebuilds all services by stopping and then starting them
# Arguments: None
# Returns: None
# Example: rebuild_all_services
rebuild_all_services() {
    stop_all_services
    start_enabled_services
}

# Function: dropin
# Description: Opens an interactive shell in a running service container
# Arguments:
#   $1 - Service name
# Returns:
#   0 - Success
#   1 - Container not found
# Example: dropin "nginx"
dropin () {
    local service=$1
    local container_id=$(docker ps -q --filter "name=.*${service}.*")
    if [ -z "$container_id" ]; then
        echo "No container found for $service"
        return 1
    fi

    docker exec -it $container_id /bin/bash
}

# Function: tail
# Description: Follows the logs of a specified service container
# Arguments:
#   $1 - Service name
# Returns:
#   0 - Success
#   1 - Container not found
# Example: tail "nginx"
tail () {
    local service=$1
    local container_id=$(docker ps -q --filter "name=.*${service}.*")
    if [ -z "$container_id" ]; then
        echo "No container found for $service"
        return 1
    fi
    docker logs -f $container_id
}

# Function: show_usage
# Description: Displays the script usage information
# Arguments: None
# Returns: None
# Example: show_usage
show_usage() {
    echo "Usage:"
    echo "  $0 start                     # Start all enabled services"
    echo "  $0 stop                      # Stop all services"
    echo "  $0 rebuild                   # Rebuild all services"
    echo "  $0 list                      # List available services"
    echo "  $0 enable <service.conf>     # Enable and start a service"
    echo "  $0 disable <service.conf>    # Disable and stop a service"
    echo "  $0 dropin <service>          # Drop into a service"
    echo "  $0 tail <service>            # Tail logs for a service"
}

# Function: main
# Description: Main command processing
# Arguments:
#   $1 - Command
# Returns: None
# Example: main "$@"
main() {
    case "$1" in
        "start")
            start_enabled_services
            ;;
        "stop")
            stop_all_services
            ;;
        "rebuild")
            rebuild_all_services
            ;;
        "list")
            list_available_services
            ;;
        "enable")
            if [ -z "$2" ]; then
                echo "Error: Please specify a configuration file"
                show_usage
                exit 1
            fi
            enable_service "$2"
            ;;
        "disable")
            if [ -z "$2" ]; then
                echo "Error: Please specify a configuration file"
                show_usage
                exit 1
            fi
            disable_service "$2"
            ;;
        "dropin")
            dropin "$2"
            ;;
        "tail")
            tail "$2"
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
