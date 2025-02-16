#!/bin/bash

# Source homelab.sh for helper functions and paths
DOMAIN_FILE="${DOMAIN_FILE:-.domains}"

# shellcheck source=/dev/null
load_env() {
    source "${PROJECT_ROOT}/.env"
}

# build_env_mappings()
# Purpose: Defines the mapping between service names and their corresponding domain variables
# Returns: A list of service-to-variable mappings in the format "service=VARIABLE1,VARIABLE2"
build_env_mappings() {
    cat <<EOF
cryptpad=DOMAIN_CRYPTPAD,DOMAIN_CRYPTPAD_SANDBOX
actual_budget=DOMAIN_BUDGET
homeassistant=DOMAIN_HOMEASSISTANT
librechat=DOMAIN_LIBRECHAT
portainer_agent=DOMAIN_PORTAINER_AGENT
photoprism=DOMAIN_PHOTOPRISM
EOF
}

# build_domain_patterns()
# Purpose: Defines the actual domain values for each service using BASE_DOMAIN
# Returns: A list of domain variable assignments
build_domain_patterns() {
    cat <<EOF
DOMAIN_CRYPTPAD=drive.${BASE_DOMAIN}
DOMAIN_CRYPTPAD_SANDBOX=sandbox-drive.${BASE_DOMAIN}
DOMAIN_BUDGET=budget.${BASE_DOMAIN}
DOMAIN_HOMEASSISTANT=ha.${BASE_DOMAIN}
DOMAIN_LIBRECHAT=chat.${BASE_DOMAIN}
DOMAIN_PORTAINER_AGENT=agent.${BASE_DOMAIN}
DOMAIN_PHOTOPRISM=photo.${BASE_DOMAIN}
EOF
}

build_domains_file() {
    if [ -z "${BASE_DOMAIN}" ]; then
        echo "BASE_DOMAIN is not set. Please set it in your environment." >&2
        exit 1
    fi

    # Create/clear the .domains file
    echo "# Domain variables generated $(date)" >"${DOMAIN_FILE}"
    echo "BASE_DOMAIN=${BASE_DOMAIN}" >>"${DOMAIN_FILE}"

    # Read enabled services from .enabled-services
    services=$(cat "${PROJECT_ROOT}/.enabled-services")
    for service in $services; do
        [ -z "$service" ] && continue
        echo "service: $service"

        # Look up if service has specific variables
        vars=$(build_env_mappings | grep "^${service}=" | cut -d= -f2)

        if [ -n "$vars" ]; then
            # Service has specific variables defined
            IFS=',' read -ra variables <<<"$vars"
            for var in "${variables[@]}"; do
                echo "var: $var"
                value=$(build_domain_patterns | grep "^${var}=" | cut -d= -f2)
                echo "value: $value"
                if [ -n "$value" ]; then
                    echo "${var}=${value}" >>"${DOMAIN_FILE}"
                fi
            done
        else
            # Use default pattern
            echo "DOMAIN_$(echo "$service" | tr '[:lower:]' '[:upper:]')=${service}.${BASE_DOMAIN}" >>"${DOMAIN_FILE}"
        fi
    done <"${PROJECT_ROOT}/.enabled-services"

    echo "Generated ${DOMAIN_FILE} file with the following variables:"
    cat "${DOMAIN_FILE}"
}

# Main execution
build_domains_file

# shellcheck source=/dev/null
source "${DOMAIN_FILE}"
