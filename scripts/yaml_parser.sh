#!/bin/bash
# Simple YAML parser for services.yaml
# Provides basic functionality to replace yq dependency

# Function: get_enabled_services
# Description: Extract services where enabled=true
# Arguments: path_to_services_yaml
# Returns: List of enabled service names
get_enabled_services() {
    local services_file="$1"

    if [ ! -f "$services_file" ]; then
        echo "Error: Services file not found: $services_file" >&2
        return 1
    fi

    # Parse YAML to find enabled services
    # This is a simple parser that looks for the pattern:
    # service_name:
    #   enabled: true

    local current_service=""
    local in_services_section=false

    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue

        # Check if we're in the services section
        if [[ "$line" =~ ^services:[[:space:]]*$ ]]; then
            in_services_section=true
            continue
        fi

        # If we hit another top-level section, exit services
        if [[ "$line" =~ ^[a-zA-Z] ]] && [ "$in_services_section" = true ] && [[ ! "$line" =~ ^[[:space:]] ]]; then
            in_services_section=false
        fi

        if [ "$in_services_section" = true ]; then
            # Look for service definitions (indented with 2 spaces, followed by colon)
            if [[ "$line" =~ ^[[:space:]]{2}([a-zA-Z0-9_-]+):[[:space:]]*$ ]]; then
                current_service="${BASH_REMATCH[1]}"
            # Look for enabled: true within a service (handles inline comments)
            elif [[ "$line" =~ ^[[:space:]]{4}enabled:[[:space:]]*(true|True|TRUE)([[:space:]]*#.*)?[[:space:]]*$ ]] && [ -n "$current_service" ]; then
                echo "$current_service"
                current_service=""
            # Reset current service if we hit another property at service level
            elif [[ "$line" =~ ^[[:space:]]{2}[a-zA-Z0-9_-]+: ]] && [[ ! "$line" =~ enabled: ]]; then
                current_service=""
            fi
        fi
    done < "$services_file"
}

# Function: get_service_names
# Description: Extract all service names from services.yaml
# Arguments: path_to_services_yaml
# Returns: List of all service names
get_service_names() {
    local services_file="$1"

    if [ ! -f "$services_file" ]; then
        echo "Error: Services file not found: $services_file" >&2
        return 1
    fi

    local in_services_section=false

    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue

        # Check if we're in the services section
        if [[ "$line" =~ ^services:[[:space:]]*$ ]]; then
            in_services_section=true
            continue
        fi

        # If we hit another top-level section, exit services
        if [[ "$line" =~ ^[a-zA-Z] ]] && [ "$in_services_section" = true ] && [[ ! "$line" =~ ^[[:space:]] ]]; then
            in_services_section=false
        fi

        if [ "$in_services_section" = true ]; then
            # Look for service definitions (indented with 2 spaces, followed by colon)
            if [[ "$line" =~ ^[[:space:]]{2}([a-zA-Z0-9_-]+):[[:space:]]*$ ]]; then
                echo "${BASH_REMATCH[1]}"
            fi
        fi
    done < "$services_file"
}

# Function: set_service_enabled
# Description: Set enabled flag for a service in services.yaml
# Arguments: services_file service_name enabled_value
# Returns: 0 on success, 1 on failure
set_service_enabled() {
    local services_file="$1"
    local service_name="$2"
    local enabled_value="$3"

    if [ ! -f "$services_file" ]; then
        echo "Error: Services file not found: $services_file" >&2
        return 1
    fi

    # Create a temporary file
    local temp_file
    temp_file=$(mktemp)

    local current_service=""
    local in_services_section=false
    local in_target_service=false
    local enabled_set=false

    while IFS= read -r line; do
        # Check if we're in the services section
        if [[ "$line" =~ ^services:[[:space:]]*$ ]]; then
            in_services_section=true
            echo "$line" >> "$temp_file"
            continue
        fi

        # If we hit another top-level section, exit services
        if [[ "$line" =~ ^[a-zA-Z] ]] && [ "$in_services_section" = true ] && [[ ! "$line" =~ ^[[:space:]] ]]; then
            in_services_section=false
            in_target_service=false
        fi

        if [ "$in_services_section" = true ]; then
            # Look for our target service
            if [[ "$line" =~ ^[[:space:]]{2}([a-zA-Z0-9_-]+):[[:space:]]*$ ]]; then
                current_service="${BASH_REMATCH[1]}"
                if [ "$current_service" = "$service_name" ]; then
                    in_target_service=true
                    enabled_set=false
                else
                    in_target_service=false
                fi
                echo "$line" >> "$temp_file"
                continue
            fi

            # If we're in our target service
            if [ "$in_target_service" = true ]; then
                # Replace existing enabled line (handles inline comments)
                if [[ "$line" =~ ^[[:space:]]{4}enabled:[[:space:]]*(true|false|True|False|TRUE|FALSE)([[:space:]]*#.*)?[[:space:]]*$ ]]; then
                    echo "    enabled: $enabled_value" >> "$temp_file"
                    enabled_set=true
                    continue
                # If we hit another service-level property and haven't set enabled yet, add it
                elif [[ "$line" =~ ^[[:space:]]{2}[a-zA-Z0-9_-]+: ]] && [ "$enabled_set" = false ]; then
                    echo "    enabled: $enabled_value" >> "$temp_file"
                    enabled_set=true
                    in_target_service=false
                    echo "$line" >> "$temp_file"
                    continue
                # If we hit any 4-space indented property and haven't set enabled yet, we're still in the service
                elif [[ "$line" =~ ^[[:space:]]{4}[a-zA-Z0-9_-]+: ]] && [ "$enabled_set" = false ]; then
                    # Add enabled before this property
                    echo "    enabled: $enabled_value" >> "$temp_file"
                    enabled_set=true
                    echo "$line" >> "$temp_file"
                    continue
                fi
            fi
        fi

        echo "$line" >> "$temp_file"
    done < "$services_file"

    # Replace the original file
    mv "$temp_file" "$services_file"
    return 0
}

# Main function to handle command line arguments
main() {
    case "$1" in
        "get-enabled")
            if [ $# -ne 2 ]; then
                echo "Usage: $0 get-enabled <services_file>" >&2
                exit 1
            fi
            get_enabled_services "$2"
            ;;
        "get-services")
            if [ $# -ne 2 ]; then
                echo "Usage: $0 get-services <services_file>" >&2
                exit 1
            fi
            get_service_names "$2"
            ;;
        "set-enabled")
            if [ $# -ne 4 ]; then
                echo "Usage: $0 set-enabled <services_file> <service_name> <true|false>" >&2
                exit 1
            fi
            set_service_enabled "$2" "$3" "$4"
            ;;
        *)
            echo "Usage: $0 {get-enabled|get-services|set-enabled} <services_file> [service_name] [value]" >&2
            echo "Commands:"
            echo "  get-enabled <file>              - Get enabled services"
            echo "  get-services <file>             - Get all service names"
            echo "  set-enabled <file> <name> <val> - Set service enabled status"
            exit 1
            ;;
    esac
}

# Run main function if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
