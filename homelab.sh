#!/bin/bash

# Define project paths
PROJECT_ROOT="$PWD"
AVAILABLE_DIR="$PROJECT_ROOT/reverseproxy/templates/conf.d"
ENABLED_DIR="$PROJECT_ROOT/reverseproxy/templates/conf.d/enabled"
SSL_DIR="$PROJECT_ROOT/reverseproxy/ssl"
DOMAIN_FILE="$PROJECT_ROOT/.domains"
CORE_SERVICES="acme reverseproxy"

# Create required directories if they don't exist
mkdir -p "$ENABLED_DIR" "$SSL_DIR"

# Function: load_env
# Description: Loads environment variables from .env file if it exists
# Arguments: None
# Returns: None
load_env() {
    if [ -f "$PROJECT_ROOT/.env" ]; then
        # shellcheck source=/dev/null
        source "$PROJECT_ROOT/.env"
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

# Function: start_enabled_services
# Description: Starts all enabled services and core services using docker compose
# Arguments: None
# Returns: None
# Example: start_enabled_services
start_enabled_services() {
    ENABLED_SERVICES=$(tr '\n' ' ' <.enabled-services | xargs)
    docker compose up -d "$ENABLED_SERVICES"
    docker compose up --build -d "$CORE_SERVICES"

    # deploy initialized certs
    docker exec \
        -e "DEPLOY_DOCKER_CONTAINER_LABEL=sh.acme.autoload.domain=${BASE_DOMAIN}" \
        -e "DEPLOY_DOCKER_CONTAINER_KEY_FILE=/etc/nginx/ssl/${BASE_DOMAIN}/key.pem" \
        -e "DEPLOY_DOCKER_CONTAINER_CERT_FILE=/etc/nginx/ssl/${BASE_DOMAIN}/cert.pem" \
        -e "DEPLOY_DOCKER_CONTAINER_CA_FILE=/etc/nginx/ssl/${BASE_DOMAIN}/ca.pem" \
        -e "DEPLOY_DOCKER_CONTAINER_FULLCHAIN_FILE=/etc/nginx/ssl/${BASE_DOMAIN}/full.pem" \
        -e "DEPLOKER_CONTAINER_RELOAD_CMD=service nginx force-reload" \
        acme.sh --deploy -d "${BASE_DOMAIN}" --deploy-hook docker
}

# Function: rebuild_all_services
# Description: Rebuilds all services by stopping and then starting them
# Arguments: None
# Returns: None
# Example: rebuild_all_services
rebuild_all_services() {
    down
    up
}

# Function: dropin
# Description: Opens an interactive shell in a running service container
# Arguments:
#   $1 - Service name
# Returns:
#   0 - Success
#   1 - Container not found
# Example: dropin "nginx"
dropin() {
    local service=$1
    local container_id
    container_id=$(docker ps -q --filter "name=.*${service}.*")

    if [ -z "$container_id" ]; then
        echo "No container found for $service"
        return 1
    fi

    docker exec -it "$container_id" /bin/bash
}

# Function: tail
# Description: Follows the logs of a specified service container
# Arguments:
#   $1 - Service name
# Returns:
#   0 - Success
#   1 - Container not found
# Example: tail "nginx"
tail() {
    local service=$1
    local container_id
    container_id=$(docker ps -a -q --filter "name=.*${service}.*")

    if [ -z "$container_id" ]; then
        echo "No container found for $service"
        return 1
    fi
    docker logs -f "$container_id"
}

# Function: initialize_certs
# Description: Initializes the certs for the services
# Arguments: None
# Returns: None
# Example: initialize_certs
initialize_certs() {
    load_env

    docker compose up --build -d acme
    docker exec -it acme.sh /bin/sh -c "acme.sh --upgrade"
    docker exec --env-file .env -it acme.sh /bin/sh -c "acme.sh --issue --dns dns_cf -d ${BASE_DOMAIN} -d ${WILDCARD_DOMAIN} --server letsencrypt || true"
}

# Function: make_dhparam
# Description: Creates a dhparam.pem file
# Arguments: None
# Returns: None
# Example: make_dhparam
make_dhparam() {
    docker exec -it acme.sh /bin/sh -c "openssl dhparam -out /acme.sh/dhparam.pem 2048"
}

# Function: up
# Description: Starts all enabled services and core services using docker compose
# Arguments: None
# Returns: None
# Example: up
up() {
    load_env

    # source build_domain.sh and invoke build_domains_file
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/scripts/build_domain.sh"
    # shellcheck source=/dev/null
    source "${DOMAIN_FILE}"

    env | grep -E '^(DOMAIN|BASE_DOMAIN)'

    setup_templates
    start_enabled_services
}

# Function: down
# Description: Stops all running services and removes containers, orphans, and volumes
# Arguments: None
# Returns: None
# Example: down
down() {
    docker compose down --remove-orphans --volumes
}

# Function: setup_templates
# Description: Copies the available templates to the enabled templates
# Arguments: None
# Returns: None
# Example: setup_templates
setup_templates() {
    ENABLED_SERVICES=$(tr '\n' ' ' <.enabled-services | xargs)
    echo "Enabled services: $ENABLED_SERVICES"
    for service in $ENABLED_SERVICES; do
        echo "Setting up template for $service"
        cp "$AVAILABLE_DIR/$service.template" "$ENABLED_DIR/$service.template"
    done
}

# Function: show_usage
# Description: Displays the script usage information
# Arguments: None
# Returns: None
# Example: show_usage
show_usage() {
    echo "Usage:"
    echo "  $0 up                        # Start all enabled services"
    echo "  $0 down                      # Stop all services"
    echo "  $0 rebuild                   # Rebuild all services"
    echo "  $0 list                      # List available services"
    echo "  $0 dropin <service>          # Drop into a service"
    echo "  $0 tail <service>            # Tail logs for a service"
    echo "  $0 init-certs                # Initialize certs"
}

# Main command processing
main() {
    case "$1" in
    up)
        up
        ;;
    down)
        down
        ;;
    rebuild)
        rebuild_all_services
        ;;
    list)
        list_available_services
        ;;
    dropin)
        dropin "$2"
        ;;
    tail)
        tail "$2"
        ;;
    init-certs)
        initialize_certs
        ;;
    make-dhparam)
        make_dhparam
        ;;
    *)
        show_usage
        exit 1
        ;;
    esac
}

main "$@"
