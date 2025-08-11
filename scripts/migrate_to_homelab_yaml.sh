#!/bin/bash
# Migration Tool: Convert Legacy Configuration to homelab.yaml
# Converts services.yaml + machines.yml + volumes.yaml + .env to unified homelab.yaml

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Input files (legacy format)
SERVICES_YAML="${PROJECT_ROOT}/config/services.yaml"
MACHINES_YML="${PROJECT_ROOT}/machines.yml"
# VOLUMES_YAML="${PROJECT_ROOT}/config/volumes.yaml"  # Currently unused
ENV_FILE="${PROJECT_ROOT}/.env"

# Output file (new format)
OUTPUT_FILE="${PROJECT_ROOT}/homelab.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Convert legacy configuration files to unified homelab.yaml format.

OPTIONS:
    -h, --help          Show this help message
    -o, --output FILE   Output file path (default: homelab.yaml)
    -s, --services FILE Services YAML file (default: config/services.yaml)
    -m, --machines FILE Machines YAML file (default: machines.yml)
    -v, --volumes FILE  Volumes YAML file (default: config/volumes.yaml)
    -e, --env FILE      Environment file (default: .env)
    -d, --deployment TYPE   Target deployment type (docker_compose|docker_swarm)
    --dry-run           Show what would be migrated without creating files
    --force             Overwrite existing output file
    --validate          Validate output using schema validation

EXAMPLES:
    $0                              # Basic migration with defaults
    $0 -d docker_swarm             # Migration for Docker Swarm deployment
    $0 --dry-run                   # Preview migration without creating files
    $0 -o my-homelab.yaml --force  # Custom output with overwrite

EOF
}

# Parse command line arguments
DEPLOYMENT_TYPE="docker_compose"
DRY_RUN=0
FORCE=0
VALIDATE=0

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -s|--services)
            SERVICES_YAML="$2"
            shift 2
            ;;
        -m|--machines)
            MACHINES_YML="$2"
            shift 2
            ;;
        -v|--volumes)
            # VOLUMES_YAML="$2"  # Currently unused - volumes info extracted from services
            shift 2
            ;;
        -e|--env)
            ENV_FILE="$2"
            shift 2
            ;;
        -d|--deployment)
            DEPLOYMENT_TYPE="$2"
            if [[ ! "$DEPLOYMENT_TYPE" =~ ^(docker_compose|docker_swarm|kubernetes)$ ]]; then
                log_error "Invalid deployment type: $DEPLOYMENT_TYPE"
                exit 1
            fi
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --force)
            FORCE=1
            shift
            ;;
        --validate)
            VALIDATE=1
            shift
            ;;
        -*)
            log_error "Unknown option: $1"
            usage >&2
            exit 1
            ;;
        *)
            log_error "Unexpected argument: $1"
            usage >&2
            exit 1
            ;;
    esac
done

# Check if output file exists
check_output_file() {
    if [[ -f "$OUTPUT_FILE" && $FORCE -eq 0 ]]; then
        log_error "Output file already exists: $OUTPUT_FILE"
        log_error "Use --force to overwrite or specify a different output file"
        exit 1
    fi
}

# Load environment variables if available
load_environment() {
    if [[ -f "$ENV_FILE" ]]; then
        log_info "Loading environment variables from $ENV_FILE"
        # Export variables for use in yq expressions, skip readonly variables
        set -a
        while IFS='=' read -r key value; do
            # Skip comments, empty lines, and readonly variables
            if [[ ! "$key" =~ ^#.*$ ]] && [[ -n "$key" ]] && [[ "$key" != "UID" ]] && [[ "$key" != "GID" ]]; then
                # Remove quotes from value
                value=$(echo "$value" | sed 's/^"\(.*\)"$/\1/' | sed "s/^'\(.*\)'$/\1/")
                export "$key"="$value"
            fi
        done < "$ENV_FILE"
        set +a
    else
        log_warning "Environment file not found: $ENV_FILE"
    fi
}

# Extract machines configuration
extract_machines() {
    local output=""

    if [[ -f "$MACHINES_YML" ]]; then
        log_info "Processing machines configuration from $MACHINES_YML"

        # Process managers
        local managers
        managers=$(yq '.managers // []' "$MACHINES_YML" 2>/dev/null || echo "[]")
        if [[ "$managers" != "[]" && "$managers" != "null" ]]; then
            while read -r machine; do
                if [[ -n "$machine" && "$machine" != "null" ]]; then
                    local hostname ip user role labels
                    hostname=$(echo "$machine" | yq '.hostname' | tr -d '"')
                    ip=$(echo "$machine" | yq '.ip' | tr -d '"')
                    user=$(echo "$machine" | yq '.user' | tr -d '"')
                    role=$(echo "$machine" | yq '.role // "manager"' | tr -d '"')
                    labels=$(echo "$machine" | yq '.labels // {}' 2>/dev/null)

                    # Generate machine name from hostname
                    local machine_name
                    machine_name=$(echo "$hostname" | sed 's/\..*$//' | tr '[:upper:]' '[:lower:]')

                    output="${output}  ${machine_name}:\n"
                    output="${output}    host: ${ip}\n"
                    output="${output}    user: ${user}\n"
                    if [[ "$DEPLOYMENT_TYPE" == "docker_swarm" ]]; then
                        output="${output}    role: ${role}\n"
                    fi

                    # Add labels if present
                    if [[ "$labels" != "{}" && "$labels" != "null" ]]; then
                        output="${output}    labels:\n"
                        echo "$labels" | yq 'to_entries | .[]' | while read -r label_entry; do
                            local key value
                            key=$(echo "$label_entry" | yq '.key' | tr -d '"')
                            value=$(echo "$label_entry" | yq '.value' | tr -d '"')
                            output="${output}      - \"${key}=${value}\"\n"
                        done
                    fi
                    output="${output}\n"
                fi
            done <<< "$(echo "$managers" | yq '.[]')"
        fi

        # Process workers
        local workers
        workers=$(yq '.workers // []' "$MACHINES_YML" 2>/dev/null || echo "[]")
        if [[ "$workers" != "[]" && "$workers" != "null" ]]; then
            while read -r machine; do
                if [[ -n "$machine" && "$machine" != "null" ]]; then
                    local hostname ip user role labels
                    hostname=$(echo "$machine" | yq '.hostname' | tr -d '"')
                    ip=$(echo "$machine" | yq '.ip' | tr -d '"')
                    user=$(echo "$machine" | yq '.user' | tr -d '"')
                    role=$(echo "$machine" | yq '.role // "worker"' | tr -d '"')
                    labels=$(echo "$machine" | yq '.labels // {}' 2>/dev/null)

                    # Generate machine name from hostname
                    local machine_name
                    machine_name=$(echo "$hostname" | sed 's/\..*$//' | tr '[:upper:]' '[:lower:]')

                    output="${output}  ${machine_name}:\n"
                    output="${output}    host: ${ip}\n"
                    output="${output}    user: ${user}\n"
                    if [[ "$DEPLOYMENT_TYPE" == "docker_swarm" ]]; then
                        output="${output}    role: ${role}\n"
                    fi

                    # Add labels if present
                    if [[ "$labels" != "{}" && "$labels" != "null" ]]; then
                        output="${output}    labels:\n"
                        echo "$labels" | yq 'to_entries | .[]' | while read -r label_entry; do
                            local key value
                            key=$(echo "$label_entry" | yq '.key' | tr -d '"')
                            value=$(echo "$label_entry" | yq '.value' | tr -d '"')
                            output="${output}      - \"${key}=${value}\"\n"
                        done
                    fi
                    output="${output}\n"
                fi
            done <<< "$(echo "$workers" | yq '.[]')"
        fi
    else
        log_warning "Machines file not found: $MACHINES_YML"
        log_info "Creating default single-machine configuration"
        output="  driver:\n    host: localhost\n    user: $(whoami)\n"
    fi

    echo -e "$output"
}

# Extract environment variables
extract_environment() {
    local output=""

    if [[ -f "$ENV_FILE" ]]; then
        log_info "Processing environment variables from $ENV_FILE"

        # Extract common environment variables
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            if [[ ! "$key" =~ ^#.*$ ]] && [[ -n "$key" ]]; then
                # Remove quotes from value
                value=$(echo "$value" | sed 's/^"\(.*\)"$/\1/' | sed "s/^'\(.*\)'$/\1/")
                output="${output}  ${key}: ${value}\n"
            fi
        done < "$ENV_FILE"
    else
        log_warning "Environment file not found: $ENV_FILE"
        output="  BASE_DOMAIN: homelab.local\n  PROJECT_ROOT: /opt/homelab\n"
    fi

    echo -e "$output"
}

# Extract services configuration
extract_services() {
    local output=""

    if [[ -f "$SERVICES_YAML" ]]; then
        log_info "Processing services configuration from $SERVICES_YAML"

        # Get all service names
        local services
        services=$(yq '.services | keys | .[]' "$SERVICES_YAML" | tr -d '"')

        while read -r service; do
            if [[ -n "$service" ]]; then
                log_info "Processing service: $service"

                # Check if service is enabled
                local enabled
                enabled=$(yq ".services.$service.enabled // true" "$SERVICES_YAML")
                if [[ "$enabled" == "false" ]]; then
                    log_info "Skipping disabled service: $service"
                    continue
                fi

                output="${output}  ${service}:\n"

                # Extract image from compose section
                local image
                if yq ".services.$service.compose.image" "$SERVICES_YAML" &>/dev/null; then
                    image=$(yq ".services.$service.compose.image" "$SERVICES_YAML" | tr -d '"')
                elif yq ".services.$service.container.image" "$SERVICES_YAML" &>/dev/null; then
                    image=$(yq ".services.$service.container.image" "$SERVICES_YAML" | tr -d '"')
                else
                    log_warning "No image found for service $service, using placeholder"
                    image="nginx:alpine"
                fi
                output="${output}    image: ${image}\n"

                # Extract port information
                local port
                port=$(yq ".services.$service.port // empty" "$SERVICES_YAML" | tr -d '"')
                if [[ -n "$port" ]]; then
                    output="${output}    port: ${port}\n"
                else
                    # Try to extract from compose ports
                    local compose_ports
                    compose_ports=$(yq ".services.$service.compose.ports // []" "$SERVICES_YAML" 2>/dev/null)
                    if [[ "$compose_ports" != "[]" && "$compose_ports" != "null" ]]; then
                        # Extract first port mapping
                        local first_port
                        first_port=$(echo "$compose_ports" | yq '.[0]' | tr -d '"' | cut -d':' -f1)
                        if [[ -n "$first_port" && "$first_port" != "null" ]]; then
                            output="${output}    port: ${first_port}\n"
                        fi
                    fi
                fi

                # Determine storage needs
                local has_volumes
                has_volumes=$(yq ".services.$service.volumes // empty" "$SERVICES_YAML" 2>/dev/null)
                if [[ -n "$has_volumes" ]]; then
                    output="${output}    storage: true\n"
                fi

                # Extract environment variables
                local env_vars
                if yq ".services.$service.compose.environment" "$SERVICES_YAML" &>/dev/null; then
                    env_vars=$(yq ".services.$service.compose.environment" "$SERVICES_YAML" 2>/dev/null)
                elif yq ".services.$service.container.environment" "$SERVICES_YAML" &>/dev/null; then
                    env_vars=$(yq ".services.$service.container.environment" "$SERVICES_YAML" 2>/dev/null)
                fi

                if [[ -n "$env_vars" && "$env_vars" != "null" && "$env_vars" != "[]" ]]; then
                    output="${output}    environment:\n"

                    if echo "$env_vars" | yq 'type' | grep -q "array"; then
                        # Handle array format (KEY=value)
                        echo "$env_vars" | yq '.[]' | while read -r env_line; do
                            env_line=$(echo "$env_line" | tr -d '"')
                            if [[ "$env_line" =~ ^([^=]+)=(.*)$ ]]; then
                                local env_key="${BASH_REMATCH[1]}"
                                local env_value="${BASH_REMATCH[2]}"
                                output="${output}      ${env_key}: \"${env_value}\"\n"
                            fi
                        done
                    else
                        # Handle object format
                        echo "$env_vars" | yq 'to_entries | .[]' | while read -r env_entry; do
                            local env_key env_value
                            env_key=$(echo "$env_entry" | yq '.key' | tr -d '"')
                            env_value=$(echo "$env_entry" | yq '.value' | tr -d '"')
                            output="${output}      ${env_key}: \"${env_value}\"\n"
                        done
                    fi
                fi

                # Add deployment strategy for Docker Swarm
                if [[ "$DEPLOYMENT_TYPE" == "docker_swarm" ]]; then
                    # Check if there are specific swarm deployment constraints
                    local swarm_deploy
                    swarm_deploy=$(yq ".swarm.services.$service.deploy // empty" "$SERVICES_YAML" 2>/dev/null)
                    if [[ -n "$swarm_deploy" ]]; then
                        # Check for placement constraints
                        local constraints
                        constraints=$(yq ".swarm.services.$service.deploy.placement.constraints // []" "$SERVICES_YAML" 2>/dev/null)
                        if [[ "$constraints" != "[]" && "$constraints" != "null" ]]; then
                            local first_constraint
                            first_constraint=$(echo "$constraints" | yq '.[0]' | tr -d '"')
                            if [[ "$first_constraint" == "node.role == manager" ]]; then
                                output="${output}    deploy: driver\n"
                            else
                                output="${output}    deploy: any\n"
                            fi
                        else
                            output="${output}    deploy: any\n"
                        fi
                    else
                        output="${output}    deploy: driver\n"
                    fi
                fi

                # Add overrides for complex configurations
                local compose_config
                compose_config=$(yq ".services.$service.compose" "$SERVICES_YAML" 2>/dev/null)
                if [[ -n "$compose_config" && "$compose_config" != "null" ]]; then
                    # Check if there are complex configurations that need overrides
                    local has_complex_config=0

                    # Check for volumes (other than simple data volumes)
                    local volumes
                    volumes=$(yq ".services.$service.compose.volumes // []" "$SERVICES_YAML" 2>/dev/null)
                    if [[ "$volumes" != "[]" && "$volumes" != "null" ]]; then
                        has_complex_config=1
                    fi

                    # Check for depends_on
                    local depends_on
                    depends_on=$(yq ".services.$service.compose.depends_on // empty" "$SERVICES_YAML" 2>/dev/null)
                    if [[ -n "$depends_on" ]]; then
                        has_complex_config=1
                    fi

                    # Check for special configurations
                    local privileged security_opt working_dir
                    privileged=$(yq ".services.$service.compose.privileged // empty" "$SERVICES_YAML" 2>/dev/null)
                    security_opt=$(yq ".services.$service.compose.security_opt // empty" "$SERVICES_YAML" 2>/dev/null)
                    working_dir=$(yq ".services.$service.compose.working_dir // empty" "$SERVICES_YAML" 2>/dev/null)

                    if [[ -n "$privileged" || -n "$security_opt" || -n "$working_dir" ]]; then
                        has_complex_config=1
                    fi

                    if [[ $has_complex_config -eq 1 ]]; then
                        output="${output}    overrides:\n"
                        output="${output}      ${DEPLOYMENT_TYPE}:\n"

                        # Add specific overrides based on what we found
                        if [[ -n "$depends_on" ]]; then
                            output="${output}        depends_on: $(echo "$depends_on" | yq -o json -I=0)\n"
                        fi

                        if [[ "$volumes" != "[]" && "$volumes" != "null" ]]; then
                            output="${output}        volumes:\n"
                            echo "$volumes" | yq '.[]' | while read -r volume; do
                                volume=$(echo "$volume" | tr -d '"')
                                output="${output}          - \"${volume}\"\n"
                            done
                        fi

                        if [[ "$privileged" == "true" ]]; then
                            output="${output}        privileged: true\n"
                        fi

                        if [[ -n "$security_opt" && "$security_opt" != "null" ]]; then
                            output="${output}        security_opt: $(echo "$security_opt" | yq -o json -I=0)\n"
                        fi

                        if [[ -n "$working_dir" ]]; then
                            output="${output}        working_dir: \"${working_dir}\"\n"
                        fi
                    fi
                fi

                output="${output}\n"
            fi
        done <<< "$services"
    else
        log_error "Services file not found: $SERVICES_YAML"
        exit 1
    fi

    echo -e "$output"
}

# Generate the complete homelab.yaml
generate_homelab_yaml() {
    local content=""

    log_info "Generating homelab.yaml configuration"

    # Header
    content="# homelab.yaml - Unified Configuration\n"
    content="${content}# Generated by migration tool from legacy configuration\n"
    content="${content}# $(date)\n\n"

    # Version and deployment type
    content="${content}version: \"2.0\"\n"
    content="${content}deployment: ${DEPLOYMENT_TYPE}\n\n"

    # Environment variables
    content="${content}environment:\n"
    content="${content}$(extract_environment)\n"

    # Machines
    content="${content}machines:\n"
    content="${content}$(extract_machines)\n"

    # Services
    content="${content}services:\n"
    content="${content}$(extract_services)"

    echo -e "$content"
}

# Validate the generated configuration
validate_output() {
    if [[ $VALIDATE -eq 1 ]]; then
        log_info "Validating generated configuration"

        local validator_script="${SCRIPT_DIR}/simple_homelab_validator.sh"
        if [[ -x "$validator_script" ]]; then
            if "$validator_script" "$OUTPUT_FILE"; then
                log_success "Generated configuration is valid"
            else
                log_warning "Generated configuration has validation warnings"
            fi
        else
            log_warning "Validator not found, skipping validation"
        fi
    fi
}

# Main migration function
main() {
    log_info "Starting migration from legacy configuration to homelab.yaml"
    log_info "Target deployment type: $DEPLOYMENT_TYPE"
    log_info "Output file: $OUTPUT_FILE"

    if [[ $DRY_RUN -eq 1 ]]; then
        log_info "DRY RUN MODE - No files will be created"
    fi

    # Check prerequisites
    if [[ $DRY_RUN -eq 0 ]]; then
        check_output_file
    fi

    # Load environment variables
    load_environment

    # Generate the configuration
    local generated_config
    generated_config=$(generate_homelab_yaml)

    if [[ $DRY_RUN -eq 1 ]]; then
        log_info "Generated configuration (dry run):"
        echo "----------------------------------------"
        echo -e "$generated_config"
        echo "----------------------------------------"
    else
        # Write to output file
        echo -e "$generated_config" > "$OUTPUT_FILE"
        log_success "Migration completed successfully"
        log_info "Generated: $OUTPUT_FILE"

        # Validate if requested
        validate_output

        # Show next steps
        echo
        log_info "Next steps:"
        echo "  1. Review the generated $OUTPUT_FILE"
        echo "  2. Validate: ./scripts/simple_homelab_validator.sh $OUTPUT_FILE"
        echo "  3. Test deployment with new configuration"
        echo "  4. Backup and remove legacy files when satisfied"
    fi
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
