#!/bin/bash

# Define project paths
PROJECT_ROOT="$PWD"
AVAILABLE_DIR="$PROJECT_ROOT/reverseproxy/templates/conf.d"
ENABLED_DIR="$PROJECT_ROOT/reverseproxy/templates/conf.d/enabled"
SSL_DIR="$PROJECT_ROOT/reverseproxy/ssl"
DOMAIN_FILE="$PROJECT_ROOT/.domains"

# Create required directories if they don't exist
mkdir -p "$ENABLED_DIR" "$SSL_DIR"

# Function: load_env
# Description: Loads environment variables from .env file if it exists
# Arguments: None
# Returns: None
# shellcheck disable=SC2317
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
# shellcheck disable=SC2317
list_available_services() {
    AVAILABLE_SERVICES=$(basename -a "$AVAILABLE_DIR"/*.template | sed 's/\.template$//' | tr '\n' ' ' | xargs)
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
    ENABLED_SERVICES=$(tr '\n' ',' <.enabled-services | xargs)
    COMPOSE_PROFILES="$ENABLED_SERVICES,core" docker compose up --build -d

    # deploy initialized certs
    docker exec \
        -e "DEPLOY_DOCKER_CONTAINER_LABEL=sh.acme.autoload.domain=${BASE_DOMAIN}" \
        -e "DEPLOY_DOCKER_CONTAINER_KEY_FILE=/etc/nginx/ssl/${BASE_DOMAIN}/key.pem" \
        -e "DEPLOY_DOCKER_CONTAINER_CERT_FILE=/etc/nginx/ssl/${BASE_DOMAIN}/cert.pem" \
        -e "DEPLOY_DOCKER_CONTAINER_CA_FILE=/etc/nginx/ssl/${BASE_DOMAIN}/ca.pem" \
        -e "DEPLOY_DOCKER_CONTAINER_FULLCHAIN_FILE=/etc/nginx/ssl/${BASE_DOMAIN}/full.pem" \
        -e "DEPLOY_DOCKER_CONTAINER_RELOAD_CMD=service nginx force-reload" \
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

# Function: sync_certs
# Description: Copies the acme certs from a remote server to this location using scp
# Arguments: None
# Returns: None
# Example: sync_certs
sync-certs() {
    read -r -p "Enter remote username: " remote_user
    read -r -p "Enter remote host: " remote_host
    read -r -p "Enter remote path to directory that contains the certs: " remote_path
    read -r -p "Enter local path to copy the certs directory to [.]: " local_path
    local_path=${local_path:-"."}

    # Create local directory if it doesn't exist
    mkdir -p "${local_path}"

    # Use scp instead of sftp for recursive copy
    if scp -r "${remote_user}@${remote_host}:\"${remote_path}\"" "${local_path}"; then
        echo "✅ Certificates synchronized successfully!"
        echo "🔒 Your SSL certificates are now up to date"
    else
        echo "❌ Failed to sync certificates"
    fi
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

    # Generate domains from services.yaml instead of legacy build_domain.sh
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/scripts/service_generator.sh"
    generate_domains_from_services

    set -a
    # .domains file is created dynamically by generate_domains_from_services
    # shellcheck source=/dev/null
    source "${DOMAIN_FILE}"
    set +a
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
    docker compose --profile '*' down --remove-orphans --volumes
}

enable_services() {
    # Get currently enabled services
    CURRENT_ENABLED=()
    if [ -f .enabled-services ]; then
        mapfile -t CURRENT_ENABLED <.enabled-services
    fi

    # Get available services into array using mapfile
    mapfile -t AVAILABLE_SERVICES < <(basename -a "$AVAILABLE_DIR"/*.template | sed 's/\.template$//')

    echo "Available services:"
    for i in "${!AVAILABLE_SERVICES[@]}"; do
        service="${AVAILABLE_SERVICES[$i]}"
        if [[ " ${CURRENT_ENABLED[*]} " =~ \ ${service}\  ]]; then
            echo -e "  $((i + 1)). ${service} \033[32m✓\033[0m"
        else
            echo "  $((i + 1)). ${service}"
        fi
    done

    echo "Enter the numbers of services you want to enable (separated by spaces):"
    read -r -a selections

    NEW_ENABLED=()
    for num in "${selections[@]}"; do
        # Convert to 0-based index
        idx=$((num - 1))

        # Validate input
        if [ "$idx" -lt 0 ] || [ "$idx" -ge "${#AVAILABLE_SERVICES[@]}" ]; then
            echo "Invalid selection: $num"
            continue
        fi

        service="${AVAILABLE_SERVICES[$idx]}"

        # Check if already enabled - fixed regex comparison
        if [[ " ${CURRENT_ENABLED[*]} " =~ \ ${service}\  ]]; then
            echo "Service ${service} is already enabled"
            continue
        fi

        NEW_ENABLED+=("$service")
    done

    # Combine current and new enabled services
    FINAL_ENABLED=("${CURRENT_ENABLED[@]}" "${NEW_ENABLED[@]}")

    # Write to file
    printf "%s\n" "${FINAL_ENABLED[@]}" >.enabled-services
}

# Function: setup_templates
# Description: Copies the available templates to the enabled templates
# Arguments: None
# Returns: None
# Example: setup_templates
setup_templates() {
    ENABLED_SERVICES=$(tr '\n' ' ' <.enabled-services | xargs)
    echo "Enabled services: $ENABLED_SERVICES"

    # remove files in enabled dir that are not in the enabled services
    FILES_IN_ENABLED_DIR=$(ls "$ENABLED_DIR"/*.template)
    for file in $FILES_IN_ENABLED_DIR; do
        if [[ ! " ${ENABLED_SERVICES[*]} " =~ \ ${file}\  ]]; then
            rm "$file"
        fi
    done

    # add files in available dir that are not in the enabled services
    for service in $ENABLED_SERVICES; do
        echo "Setting up template for $service"
        cp "$AVAILABLE_DIR/$service.template" "$ENABLED_DIR/$service.template"
    done
}

# # Function: show_usage
# # Description: Displays the script usage information
# # Arguments: None
# # Returns: None
# # Example: show_usage
# show_usage() {
#     echo "Usage:"
#     echo "  $0 up                        # Start all enabled services"
#     echo "  $0 down                      # Stop all services"
#     echo "  $0 rebuild                   # Rebuild all services"
#     echo "  $0 list                      # List available services"
#     echo "  $0 dropin <service>          # Drop into a service"
#     echo "  $0 tail <service>            # Tail logs for a service"
#     echo "  $0 init-certs                # Initialize certs"
#     echo "  $0 sync-certs                # Sync certs"
#     echo "  $0 enable-services           # Enable services"
# }

# # Main command processing
# main() {
#     case "$1" in
#     up)
#         up
#         ;;
#     down)
#         down
#         ;;
#     rebuild)
#         rebuild_all_services
#         ;;
#     list)
#         list_available_services
#         ;;
#     enable-services)
#         enable_services
#         ;;
#     sync-certs)
#         sync-certs
#         ;;
#     dropin)
#         dropin "$2"
#         ;;
#     tail)
#         tail "$2"
#         ;;
#     init-certs)
#         initialize_certs
#         ;;
#     make-dhparam)
#         make_dhparam
#         ;;
#     *)
#         show_usage
#         exit 1
#         ;;
#     esac
# }

# main "$@"


#!/bin/bash

# Load common functions and variables
source "scripts/common.sh"
source "scripts/machines.sh"

# Load deployment target implementations
# shellcheck disable=SC1090
for target in scripts/deployments/*.sh; do
    source "$target"
done

# Load service generator
if [ -f "scripts/service_generator.sh" ]; then
    source scripts/service_generator.sh
fi

# Enhanced CLI Functions

# Function: show_help
# Description: Shows comprehensive help information
show_help() {
    cat <<EOF
🏠 Selfhosted - Self-hosted Services Management

USAGE:
    $0 <command> [subcommand] [options...]

COMMANDS:
    service         Manage service configurations
    deploy          Deploy services to infrastructure
    config          Manage environment and configuration
    help            Show this help message

SERVICE COMMANDS:
    service list              List all available services with descriptions
    service generate          Generate deployment files from services.yaml
    service validate          Validate services configuration
    service info <name>       Show detailed information about a service

DEPLOY COMMANDS:
    deploy compose <cmd>      Deploy using Docker Compose
    deploy swarm <cmd>        Deploy using Docker Swarm
    deploy k8s <cmd>          Deploy using Kubernetes (future)

CONFIG COMMANDS:
    config init               Initialize environment and certificates
    config validate           Validate all configuration files

LEGACY COMMANDS (deprecated):
    init-certs               Use 'config init' instead
    list                     Use 'service list' instead
    sync-files               Use 'config sync' instead

EXAMPLES:
    $0 service list                    # List all available services
    $0 service generate                # Generate deployment files
    $0 deploy compose up               # Start services with Docker Compose
    $0 config init                     # Initialize certificates and environment

For more information, see: https://github.com/selfhosted/selfhosted
EOF
}

# Function: service_list
# Description: Lists all available services from configuration
service_list() {
    if [ -f "$PROJECT_ROOT/config/services.yaml" ]; then
        list_available_services_from_config
    else
        echo "❌ Error: Services configuration not found at $PROJECT_ROOT/config/services.yaml"
        echo "💡 Run '$0 config init' to set up the environment"
        exit 1
    fi
}

# Function: service_generate
# Description: Generates all deployment files from services configuration
service_generate() {
    echo "🚀 Generating deployment files from services configuration..."
    if ! generate_all_from_services; then
        echo "❌ Failed to generate deployment files"
        exit 1
    fi
    echo "✅ All deployment files generated successfully!"
    echo "📁 Generated files:"
    echo "   - generated-docker-compose.yaml (Docker Compose configuration)"
    echo "   - generated-nginx/ (Nginx templates)"
    echo "   - .domains (Domain variables)"
}

# Function: service_generate_consolidated
# Description: Generates all files to consolidated generated/ directory structure
service_generate_consolidated() {
    echo "🏗️ Generating files to consolidated directory structure..."
    if ! generate_all_to_generated_dir; then
        echo "❌ Failed to generate consolidated directory structure"
        exit 1
    fi
    echo "🎉 Consolidated structure generated successfully!"
    echo "📁 View the structure: ls -la generated/"
    echo "📖 Read the guide: cat generated/README.md"
}

# Function: service_validate
# Description: Validates the services configuration
service_validate() {
    if ! validate_HOMELAB_CONFIG; then
        exit 1
    fi
}

# Function: service_info
# Description: Shows detailed information about a specific service
service_info() {
    local service_name="$1"
    if [ -z "$service_name" ]; then
        echo "❌ Error: Service name required"
        echo "💡 Usage: $0 service info <service-name>"
        echo "💡 Run '$0 service list' to see available services"
        exit 1
    fi

    if [ ! -f "$PROJECT_ROOT/config/services.yaml" ]; then
        echo "❌ Error: Services configuration not found"
        exit 1
    fi

    # Check if service exists
    if ! yq ".services.${service_name}" "$PROJECT_ROOT/config/services.yaml" > /dev/null 2>&1; then
        echo "❌ Error: Service '$service_name' not found"
        echo "💡 Run '$0 service list' to see available services"
        exit 1
    fi

    # Display service information
    echo "📋 Service Information: $service_name"
    echo ""
    echo "Name:        $(yq -r ".services.${service_name}.name" "$PROJECT_ROOT/config/services.yaml")"
    echo "Description: $(yq -r ".services.${service_name}.description" "$PROJECT_ROOT/config/services.yaml")"
    echo "Category:    $(yq -r ".services.${service_name}.category" "$PROJECT_ROOT/config/services.yaml")"
    echo "Domain:      $(yq -r ".services.${service_name}.domain" "$PROJECT_ROOT/config/services.yaml").${BASE_DOMAIN:-\${BASE_DOMAIN\}}"
    echo "Port:        $(yq -r ".services.${service_name}.port" "$PROJECT_ROOT/config/services.yaml")"
    echo ""
    echo "🐳 Docker Configuration:"
    echo "Image:       $(yq -r ".services.${service_name}.compose.image" "$PROJECT_ROOT/config/services.yaml")"
    echo ""
    echo "🌐 Access URL: https://$(yq -r ".services.${service_name}.domain" "$PROJECT_ROOT/config/services.yaml").${BASE_DOMAIN:-\${BASE_DOMAIN\}}"
}

# Function: service_enable
# Description: Enables services in services.yaml
service_enable() {
    if [ $# -eq 0 ]; then
        echo "❌ Error: Service name(s) required"
        echo "💡 Usage: $0 service enable <service1> [service2] ..."
        echo "💡 Example: $0 service enable actual homepage"
        exit 1
    fi

    enable_services_via_yaml "$@"

    echo ""
    echo "📋 Currently enabled services:"
    list_enabled_services_from_yaml
}

# Function: service_disable
# Description: Disables services in services.yaml
service_disable() {
    if [ $# -eq 0 ]; then
        echo "❌ Error: Service name(s) required"
        echo "💡 Usage: $0 service disable <service1> [service2] ..."
        echo "💡 Example: $0 service disable actual homepage"
        exit 1
    fi

    disable_services_via_yaml "$@"

    echo ""
    echo "📋 Currently enabled services:"
    list_enabled_services_from_yaml
}

# Function: service_status
# Description: Shows enabled/disabled status of all services
service_status() {
    echo "📊 Service Status Overview"
    echo "=========================="
    echo ""
    list_enabled_services_from_yaml
}

# Function: service_interactive
# Description: Interactive service enablement interface
service_interactive() {
    interactive_service_enablement
}

# Function: service_help
# Description: Shows service-specific help
service_help() {
    cat <<EOF
🔧 Service Management Commands

USAGE:
    $0 service <subcommand> [options...]

SUBCOMMANDS:
    list                     List all available services with metadata
    enable <service...>      Enable one or more services
    disable <service...>     Disable one or more services
    status                   Show enabled/disabled status of all services
    interactive              Interactive service selection interface
    generate                 Generate deployment files from services.yaml
    generate-consolidated    Generate files to consolidated generated/ directory
    validate                 Validate services configuration syntax
    info <name>              Show detailed information about a service
    help                     Show this help message

EXAMPLES:
    $0 service list                    # Show all available services
    $0 service enable actual           # Enable the 'actual' service
    $0 service disable homepage        # Disable the 'homepage' service
    $0 service status                  # Show which services are enabled/disabled
    $0 service interactive             # Interactive service selection
    $0 service info actual             # Show details about 'actual' service
    $0 service generate                # Generate docker-compose.yaml and nginx templates
    $0 service generate-consolidated   # Generate to clean generated/ directory structure
    $0 service validate                # Check services.yaml syntax and structure
EOF
}

# Function: config_init
# Description: Initializes the environment and certificates
config_init() {
    echo "🚀 Initializing selfhosted environment..."

    # Check for .env file
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            echo "📋 .env file not found. Copying from .env.example..."
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            echo "⚠️  Please edit .env file with your configuration before proceeding"
            echo "💡 Required: BASE_DOMAIN, CF_Token (or CF_Email/CF_Key)"
            exit 1
        else
            echo "❌ Error: Neither .env nor .env.example found"
            echo "💡 Please create .env file with required configuration"
            exit 1
        fi
    fi

    # Load environment
    load_env

    # Validate required variables
    if [ -z "$BASE_DOMAIN" ]; then
        echo "❌ Error: BASE_DOMAIN not set in .env file"
        exit 1
    fi

    if [ -z "$CF_Token" ] && { [ -z "$CF_Email" ] || [ -z "$CF_Key" ]; }; then
        echo "❌ Error: Cloudflare credentials not set in .env file"
        echo "💡 Set either CF_Token or both CF_Email and CF_Key"
        exit 1
    fi

    # Initialize certificates
    ensure_certs_exist

    # Generate deployment files if services.yaml exists
    if [ -f "$PROJECT_ROOT/config/services.yaml" ]; then
        echo "🔧 Generating deployment files..."
        generate_all_from_services
    fi

    echo "✅ Environment setup complete!"
    echo "💡 You can now deploy services with: $0 deploy compose up"
}

# Enhanced deploy command with file generation and modern service enablement
enhanced_deploy() {
    local target="$1"
    local cmd="$2"
    shift 2



    # Generate deployment files before deploying (if not dry-run)
    if [ -f "$PROJECT_ROOT/config/services.yaml" ] && [[ "$*" != *"--dry-run"* ]]; then
        echo "🔧 Generating latest deployment files..."
        if ! generate_all_from_services; then
            echo "❌ Failed to generate deployment files"
            exit 1
        fi

        # Generate .enabled-services file for backward compatibility
        generate_enabled_services_from_yaml

        # Check certificate status and initialize if needed
        echo "🔐 Checking certificate status..."
        if ! ensure_certs_exist; then
            echo "⚠️ Certificate initialization recommended"
            echo "💡 Certificates will be initialized automatically on first service start"
        fi
    fi

    # Check if target-specific function exists
    if command_exists "${target}_${cmd}"; then
        # Add special handling for compose commands to use generated files
        if [ "$target" = "compose" ] && [ -f "$PROJECT_ROOT/generated-docker-compose.yaml" ]; then
            echo "📁 Using generated docker-compose.yaml"
            # For dry-run, just show the command that would be executed
            if [[ "$*" == *"--dry-run"* ]]; then
                echo "Would execute: docker compose -f generated-docker-compose.yaml ${*//--dry-run/}"
                return 0
            fi
            # Set compose file environment variable
            export COMPOSE_FILE="$PROJECT_ROOT/generated-docker-compose.yaml"
        fi

        "${target}_${cmd}" "$@"
    else
        echo "❌ Unknown command '$cmd' for target '$target'"
        echo "💡 Available commands for $target:"
        list_commands "$target"
        exit 1
    fi
}

# Main command router
case "$1" in
    # New enhanced commands
    service)
        case "$2" in
            list) service_list ;;
            enable) service_enable "${@:3}" ;;
            disable) service_disable "${@:3}" ;;
            status) service_status ;;
            interactive) service_interactive ;;
            generate) service_generate ;;
            generate-consolidated) service_generate_consolidated ;;
            validate) service_validate ;;
            info) service_info "$3" ;;
            help|"") service_help ;;
            *)
                echo "❌ Unknown service command: $2"
                service_help
                exit 1
                ;;
        esac
        ;;
    deploy)
        case "$2" in
            compose|swarm|k8s)
                enhanced_deploy "$2" "$3" "${@:4}"
                ;;
            "")
                echo "❌ Deploy target required"
                echo "💡 Usage: $0 deploy {compose|swarm|k8s} <command>"
                exit 1
                ;;
            *)
                echo "❌ Unknown deploy target: $2"
                echo "💡 Available targets: compose, swarm, k8s"
                exit 1
                ;;
        esac
        ;;
    deploy-compose)
        # SSH-based Docker Compose deployment coordination
        case "$2" in
            all)
                "$PROJECT_ROOT/scripts/deploy_compose_bundles.sh" deploy-all "${3:-homelab.yaml}" "${@:4}"
                ;;
            status)
                "$PROJECT_ROOT/scripts/deploy_compose_bundles.sh" status "${3:-homelab.yaml}"
                ;;
            test-ssh)
                "$PROJECT_ROOT/scripts/deploy_compose_bundles.sh" test-connectivity "${3:-homelab.yaml}"
                ;;
            logs)
                if [[ -z "$3" ]]; then
                    echo "❌ Machine name required for logs"
                    echo "💡 Usage: $0 deploy-compose logs <machine> [config]"
                    exit 1
                fi
                "$PROJECT_ROOT/scripts/deploy_compose_bundles.sh" logs "$3" "${4:-homelab.yaml}"
                ;;
            rollback)
                if [[ -z "$3" ]]; then
                    echo "❌ Machine name required for rollback"
                    echo "💡 Usage: $0 deploy-compose rollback <machine> [config]"
                    exit 1
                fi
                "$PROJECT_ROOT/scripts/deploy_compose_bundles.sh" rollback "$3" "${4:-homelab.yaml}"
                ;;
            help|"")
                echo "💡 Deploy-Compose Commands:"
                echo "   all [config] [--dry-run] [--progress]  - Deploy to all machines"
                echo "   status [config]                        - Check deployment status"
                echo "   test-ssh [config]                      - Test SSH connectivity"
                echo "   logs <machine> [config]                - Collect deployment logs"
                echo "   rollback <machine> [config]            - Rollback deployment"
                echo ""
                echo "💡 Examples:"
                echo "   $0 deploy-compose all homelab.yaml                # Deploy to all machines"
                echo "   $0 deploy-compose all homelab.yaml --dry-run      # Dry run deployment"
                echo "   $0 deploy-compose status                          # Check all machine status"
                echo "   $0 deploy-compose logs driver                     # View driver logs"
                echo "   $0 deploy-compose rollback node-01                # Rollback node-01"
                ;;
            *)
                if [[ -n "$2" ]]; then
                    # Handle deploy to specific machine
                    "$PROJECT_ROOT/scripts/deploy_compose_bundles.sh" deploy "$2" "${3:-homelab.yaml}"
                else
                    echo "❌ Unknown deploy-compose command: $2"
                    echo "💡 Run '$0 deploy-compose help' for available commands"
                    exit 1
                fi
                ;;
        esac
        ;;
    generate-nginx)
        # Generate nginx bundles for Docker Compose deployment
        case "$2" in
            bundles)
                "$PROJECT_ROOT/scripts/translate_homelab_to_compose.sh" generate-nginx-bundles "${3:-homelab.yaml}"
                ;;
            help|"")
                echo "💡 Generate-Nginx Commands:"
                echo "   bundles [config]  - Generate nginx bundles for all machines"
                echo ""
                echo "💡 Examples:"
                echo "   $0 generate-nginx bundles homelab.yaml    # Generate nginx bundles"
                echo "   $0 generate-nginx bundles                 # Use default homelab.yaml"
                ;;
            *)
                echo "❌ Unknown generate-nginx command: $2"
                echo "💡 Run '$0 generate-nginx help' for available commands"
                exit 1
                ;;
        esac
        ;;
    config)
        case "$2" in
            init) config_init ;;
            validate) service_validate ;;
            help|"")
                echo "💡 Config commands: init, validate"
                ;;
            *)
                echo "❌ Unknown config command: $2"
                exit 1
                ;;
        esac
        ;;
    help|"") show_help ;;



    *)
        echo "❌ Unknown command: $1"
        echo ""
        echo "💡 Available commands:"
        echo "   service        - Manage service configurations"
        echo "   deploy         - Deploy services to infrastructure"
        echo "   deploy-compose - Multi-machine Docker Compose deployment coordination"
        echo "   generate-nginx - Generate nginx bundles for Docker Compose"
        echo "   config         - Manage environment and configuration"
        echo "   help           - Show detailed help"
        echo ""
        echo "💡 Run '$0 help' for detailed usage information"
        exit 1
        ;;
esac
