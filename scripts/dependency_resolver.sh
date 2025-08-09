#!/bin/bash

# Dependency Resolver
# Provides service dependency resolution, startup ordering, and health checking

# Set default paths
PROJECT_ROOT="${PROJECT_ROOT:-$PWD}"
SERVICES_CONFIG="${SERVICES_CONFIG:-$PROJECT_ROOT/config/services.yaml}"
DEPENDENCY_GRAPH_FILE="${DEPENDENCY_GRAPH_FILE:-$PROJECT_ROOT/dependency-graph.md}"
STARTUP_SCRIPT="${STARTUP_SCRIPT:-$PROJECT_ROOT/startup-services.sh}"
SHUTDOWN_SCRIPT="${SHUTDOWN_SCRIPT:-$PROJECT_ROOT/shutdown-services.sh}"

# Load common functions if available
if [ -f "$PROJECT_ROOT/scripts/common.sh" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/scripts/common.sh"
fi

# Function: get_all_services
# Description: Gets list of all services from config
# Arguments: None
# Returns: List of service names
get_all_services() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG" >&2
        return 1
    fi

    # Use yq-agnostic approach: extract service names using awk
    # This finds entries under the 'services:' section only
    awk '
        /^services:/ { in_services = 1; next }
        in_services && /^[a-zA-Z]/ && !/^  / { in_services = 0 }
        in_services && /^  [a-zA-Z0-9_-]+:/ {
            gsub(/^  /, "");
            gsub(/:.*/, "");
            print
        }
    ' "$SERVICES_CONFIG" | sort
}

# Function: get_service_dependencies
# Description: Gets dependencies for a specific service
# Arguments: $1 - service name
# Returns: List of dependency service names
get_service_dependencies() {
    local service="$1"
    if [ -z "$service" ]; then
        echo "❌ Error: Service name required" >&2
        return 1
    fi

    # Check if service exists using grep
    if ! grep -q "^  ${service}:" "$SERVICES_CONFIG"; then
        echo "❌ Error: Service '$service' not found" >&2
        return 1
    fi

    # Extract dependencies using awk - this is yq-agnostic
    awk "
        /^  ${service}:/ { in_service = 1; next }
        in_service && /^  [a-zA-Z0-9_-]+:/ { in_service = 0 }
        in_service && /^    depends_on:/ { in_depends = 1; next }
        in_service && in_depends && /^      - / {
            gsub(/^      - /, \"\");
            gsub(/[\"']/, \"\");
            print;
            next
        }
        in_service && in_depends && /^    [a-zA-Z0-9_-]+:/ { in_depends = 0 }
        in_service && in_depends && /^  [a-zA-Z0-9_-]+:/ { in_service = 0; in_depends = 0 }
    " "$SERVICES_CONFIG"
}

# Function: get_service_priority
# Description: Gets startup priority for a service
# Arguments: $1 - service name
# Returns: Priority number (lower = starts first)
get_service_priority() {
    local service="$1"
    if [ -z "$service" ]; then
        return 1
    fi

    local priority
    priority=$(yq ".services[\"${service}\"].startup_priority" "$SERVICES_CONFIG" 2>/dev/null | tr -d '"')

    # Default priority if not specified
    if [ "$priority" = "null" ] || [ -z "$priority" ]; then
        priority=10
    fi

    echo "$priority"
}

# Function: detect_circular_dependencies
# Description: Detects circular dependencies in service configuration
# Arguments: None
# Returns: 0 if no circular deps, 1 if circular deps found
detect_circular_dependencies() {
    echo "🔍 Checking for circular dependencies..."

    local all_services
    all_services=$(get_all_services)

    # Simple approach: check if any service depends on itself through a chain
    for service in $all_services; do
        if _has_circular_dependency "$service" "$service" ""; then
            echo "❌ Circular dependency detected involving: $service"
            return 1
        fi
    done

    echo "✅ No circular dependencies found"
    return 0
}

# Function: _has_circular_dependency (internal)
# Description: Check if starting from a service leads back to target
# Arguments: $1 - current service, $2 - target service, $3 - visited path
# Returns: 0 if no circular dep, 1 if circular dep found
_has_circular_dependency() {
    local current="$1"
    local target="$2"
    local visited="$3"

    # If we've visited this service in current path, avoid infinite recursion
    if echo "$visited" | grep -q "\<$current\>"; then
        return 0  # Already checked this path, no cycle from here
    fi

    # Get dependencies of current service
    local deps
    deps=$(get_service_dependencies "$current" 2>/dev/null)

    # Check each dependency
    for dep in $deps; do
        # If dependency is the target, we found a cycle
        if [ "$dep" = "$target" ]; then
            return 1  # Circular dependency found
        fi

        # Recursively check if dependency leads to target
        if _has_circular_dependency "$dep" "$target" "$visited $current"; then
            return 1  # Circular dependency found in chain
        fi
    done

    return 0  # No circular dependency found
}

# Function: resolve_service_dependencies
# Description: Resolves all service dependencies using topological sort
# Arguments: None
# Returns: Services in dependency-resolved order
resolve_service_dependencies() {
    echo "📋 Resolving service dependencies..." >&2

    # First check for circular dependencies
    if ! detect_circular_dependencies >/dev/null 2>&1; then
        echo "❌ Cannot resolve dependencies due to circular references" >&2
        detect_circular_dependencies >&2
        return 1
    fi

    local all_services resolved remaining
    all_services=$(get_all_services)
    resolved=""
    remaining="$all_services"

    # Topological sort algorithm
    while [ -n "$remaining" ]; do
        local progress=false
        local new_remaining=""

        for service in $remaining; do
            local deps_satisfied=true
            local deps
            deps=$(get_service_dependencies "$service" 2>/dev/null)

            # Check if all dependencies are already resolved
            for dep in $deps; do
                if ! echo "$resolved" | grep -q "\<$dep\>"; then
                    deps_satisfied=false
                    break
                fi
            done

            if $deps_satisfied; then
                resolved="$resolved $service"
                progress=true
                echo "✅ Resolved: $service" >&2
            else
                new_remaining="$new_remaining $service"
            fi
        done

        remaining="$new_remaining"

        # If no progress was made, we have unresolvable dependencies
        if ! $progress && [ -n "$remaining" ]; then
            echo "❌ Unresolvable dependencies for services: $remaining" >&2
            return 1
        fi
    done

    echo "$resolved"
    return 0
}

# Function: generate_startup_order
# Description: Generates startup order considering both dependencies and priorities
# Arguments: None
# Returns: Services in startup order with priorities
generate_startup_order() {
    echo "🚀 Generating startup order..." >&2

    local resolved_order
    if ! resolved_order=$(resolve_service_dependencies); then
        return 1
    fi

    # Create temporary file to sort by priority within dependency groups
    local temp_file
    temp_file=$(mktemp)

    for service in $resolved_order; do
        local priority
        priority=$(get_service_priority "$service")
        echo "$priority $service" >> "$temp_file"
    done

    # Sort by priority while maintaining dependency order
    sort -n "$temp_file" | while read -r priority service; do
        echo "Service: $service (priority: $priority)"
    done

    rm -f "$temp_file"
}

# Function: validate_service_dependencies
# Description: Validates that all service dependencies exist
# Arguments: None
# Returns: 0 if valid, 1 if invalid dependencies found
validate_service_dependencies() {
    echo "🔍 Validating service dependencies..."

    local all_services
    all_services=$(get_all_services)
    local errors=0

    for service in $all_services; do
        local deps
        deps=$(get_service_dependencies "$service" 2>/dev/null)

        for dep in $deps; do
            if ! echo "$all_services" | grep -q "\<$dep\>"; then
                echo "❌ Service '$service' depends on non-existent service '$dep'"
                errors=$((errors + 1))
            fi
        done
    done

    if [ $errors -eq 0 ]; then
        echo "✅ All service dependencies are valid"
        return 0
    else
        echo "❌ Found $errors invalid dependencies"
        return 1
    fi
}

# Function: get_service_dependents
# Description: Gets services that depend on a given service (reverse dependencies)
# Arguments: $1 - service name
# Returns: List of dependent service names
get_service_dependents() {
    local target_service="$1"
    if [ -z "$target_service" ]; then
        echo "❌ Error: Service name required" >&2
        return 1
    fi

    echo "🔗 Finding services that depend on '$target_service'..." >&2

    local all_services
    all_services=$(get_all_services)

    for service in $all_services; do
        local deps
        deps=$(get_service_dependencies "$service" 2>/dev/null)

        if echo "$deps" | grep -q "\<$target_service\>"; then
            echo "$service"
        fi
    done
}

# Function: generate_dependency_graph
# Description: Generates a visual dependency graph in Markdown format
# Arguments: None
# Returns: Creates dependency graph file
generate_dependency_graph() {
    echo "📊 Generating dependency graph..."

    cat > "$DEPENDENCY_GRAPH_FILE" <<EOF
# Service Dependency Graph

Generated: $(date)

## Services Overview

EOF

    local all_services
    all_services=$(get_all_services)

    echo "| Service | Dependencies | Dependents | Priority |" >> "$DEPENDENCY_GRAPH_FILE"
    echo "|---------|--------------|------------|----------|" >> "$DEPENDENCY_GRAPH_FILE"

    for service in $all_services; do
        local deps dependents priority
        deps=$(get_service_dependencies "$service" 2>/dev/null | tr '\n' ',' | sed 's/,$//')
        dependents=$(get_service_dependents "$service" 2>/dev/null | tr '\n' ',' | sed 's/,$//')
        priority=$(get_service_priority "$service")

        [ -z "$deps" ] && deps="none"
        [ -z "$dependents" ] && dependents="none"

        echo "| $service | $deps | $dependents | $priority |" >> "$DEPENDENCY_GRAPH_FILE"
    done

    local startup_order
    startup_order=$(generate_startup_order 2>/dev/null)

    {
        echo ""
        echo "## Startup Order"
        echo ""
        echo '```'
        echo "$startup_order"
        echo '```'
    } >> "$DEPENDENCY_GRAPH_FILE"

    echo "✅ Dependency graph saved to $DEPENDENCY_GRAPH_FILE"
}

# Function: check_service_health
# Description: Checks health of a service
# Arguments: $1 - service name
# Returns: 0 if healthy, 1 if unhealthy
check_service_health() {
    local service="$1"
    if [ -z "$service" ]; then
        echo "❌ Error: Service name required" >&2
        return 1
    fi

    # Check if health check is enabled
    local health_enabled
    health_enabled=$(yq ".services[\"${service}\"].health_check.enabled" "$SERVICES_CONFIG" 2>/dev/null | tr -d '"')

    if [ "$health_enabled" != "true" ]; then
        echo "ℹ️  Health check not configured for $service"
        return 0
    fi

    local endpoint timeout domain port
    endpoint=$(yq ".services[\"${service}\"].health_check.endpoint" "$SERVICES_CONFIG" 2>/dev/null | tr -d '"')
    timeout=$(yq ".services[\"${service}\"].health_check.timeout" "$SERVICES_CONFIG" 2>/dev/null | tr -d '"')
    domain=$(yq ".services[\"${service}\"].domain" "$SERVICES_CONFIG" 2>/dev/null | tr -d '"')
    port=$(yq ".services[\"${service}\"].port" "$SERVICES_CONFIG" 2>/dev/null | tr -d '"')

    [ "$timeout" = "null" ] && timeout=30
    [ "$endpoint" = "null" ] && endpoint="/health"

    if [ "${HEALTH_CHECK_DRY_RUN:-false}" = "true" ]; then
        echo "Would check health for $service at ${domain}:${port}${endpoint} (timeout: ${timeout}s)"
        return 0
    fi

    echo "🏥 Checking health of $service..."

    # Attempt to connect to health endpoint
    if command -v curl >/dev/null 2>&1; then
        if curl -f -s --max-time "$timeout" "http://${domain}:${port}${endpoint}" >/dev/null 2>&1; then
            echo "✅ $service is healthy"
            return 0
        else
            echo "❌ $service health check failed"
            return 1
        fi
    else
        echo "⚠️  curl not available, skipping health check for $service"
        return 0
    fi
}

# Function: wait_for_service_dependencies
# Description: Waits for all dependencies of a service to be healthy
# Arguments: $1 - service name, $2 - max wait time (optional, default 300s)
# Returns: 0 if all deps healthy, 1 if timeout or failure
wait_for_service_dependencies() {
    local service="$1"
    local max_wait="${2:-300}"

    if [ -z "$service" ]; then
        echo "❌ Error: Service name required" >&2
        return 1
    fi

    local deps
    deps=$(get_service_dependencies "$service" 2>/dev/null)

    if [ -z "$deps" ]; then
        echo "ℹ️  No dependencies for $service"
        return 0
    fi

    echo "⏳ Waiting for dependencies of $service: $deps"

    if [ "${HEALTH_CHECK_DRY_RUN:-false}" = "true" ]; then
        echo "Would wait for dependencies: $deps"
        return 0
    fi

    local start_time
    start_time=$(date +%s)

    for dep in $deps; do
        echo "   Checking dependency: $dep"

        local wait_count=0
        while ! check_service_health "$dep" >/dev/null 2>&1; do
            local current_time
            current_time=$(date +%s)
            local elapsed=$((current_time - start_time))

            if [ "$elapsed" -ge "$max_wait" ]; then
                echo "❌ Timeout waiting for dependency $dep of $service"
                return 1
            fi

            sleep 5
            wait_count=$((wait_count + 1))
            if [ $((wait_count % 6)) -eq 0 ]; then  # Every 30 seconds
                echo "   Still waiting for $dep... (${elapsed}s elapsed)"
            fi
        done

        echo "   ✅ Dependency $dep is ready"
    done

    echo "✅ All dependencies ready for $service"
    return 0
}

# Function: generate_docker_compose_with_dependencies
# Description: Generates Docker Compose with proper depends_on blocks
# Arguments: None
# Returns: Creates enhanced docker-compose.yaml
generate_docker_compose_with_dependencies() {
    echo "🐳 Generating Docker Compose with dependency ordering..."

    # Load service generator if available
    if [ -f "$PROJECT_ROOT/scripts/service_generator.sh" ]; then
        # shellcheck source=/dev/null
        source "$PROJECT_ROOT/scripts/service_generator.sh"

        # Generate base compose file
        generate_compose_from_services >/dev/null

        # Enhance with dependency information
        local compose_file="$PROJECT_ROOT/generated-docker-compose.yaml"
        local temp_file
        temp_file=$(mktemp)

        # Add dependency blocks to each service
        local all_services
        all_services=$(get_all_services)

        for service in $all_services; do
            local deps
            deps=$(get_service_dependencies "$service" 2>/dev/null)

            if [ -n "$deps" ]; then
                echo "   Adding dependencies for $service: $deps"

                # Use yq to add depends_on section to the service
                yq eval ".services[\"${service}\"].depends_on = [$(echo "$deps" | sed 's/ /","/g' | sed 's/^/"/' | sed 's/$/"/' )]" "$compose_file" > "$temp_file"
                mv "$temp_file" "$compose_file"
            fi
        done

        echo "✅ Enhanced Docker Compose with dependencies"
        return 0
    else
        echo "❌ Error: Service generator not found"
        return 1
    fi
}

# Function: generate_startup_script
# Description: Generates a script to start services in dependency order
# Arguments: None
# Returns: Creates startup script
generate_startup_script() {
    echo "🚀 Generating startup script..."

    cat > "$STARTUP_SCRIPT" <<EOF
#!/bin/bash
# Generated service startup script
# DO NOT EDIT - This file is auto-generated
# Generated $(date)

set -e

echo "🚀 Starting services in dependency order..."

EOF

    local startup_order
    startup_order=$(generate_startup_order 2>/dev/null | grep "Service:" | cut -d' ' -f2)

    for service in $startup_order; do
        cat >> "$STARTUP_SCRIPT" <<EOF

echo "▶️  Starting $service..."
if command -v docker-compose >/dev/null 2>&1; then
    docker-compose up -d $service
elif command -v docker >/dev/null 2>&1 && command -v compose >/dev/null 2>&1; then
    docker compose up -d $service
else
    echo "❌ Docker Compose not found"
    exit 1
fi

# Wait for service to be healthy if health check is configured
if [ -f "$PROJECT_ROOT/scripts/dependency_resolver.sh" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/scripts/dependency_resolver.sh"
    wait_for_service_dependencies "$service"
fi

echo "✅ $service started successfully"
EOF
    done

    cat >> "$STARTUP_SCRIPT" <<EOF

echo "🎉 All services started successfully!"
EOF

    chmod +x "$STARTUP_SCRIPT"
    echo "✅ Startup script saved to $STARTUP_SCRIPT"
}

# Function: generate_shutdown_script
# Description: Generates a script to shutdown services in reverse order
# Arguments: None
# Returns: Creates shutdown script
generate_shutdown_script() {
    echo "🛑 Generating shutdown script..."

    cat > "$SHUTDOWN_SCRIPT" <<EOF
#!/bin/bash
# Generated service shutdown script
# DO NOT EDIT - This file is auto-generated
# Generated $(date)

set -e

echo "🛑 Stopping services in reverse dependency order..."

EOF

    local startup_order
    startup_order=$(generate_startup_order 2>/dev/null | grep "Service:" | cut -d' ' -f2)

    # Reverse the order for shutdown
    local shutdown_order
    shutdown_order=$(echo "$startup_order" | tac)

    for service in $shutdown_order; do
        cat >> "$SHUTDOWN_SCRIPT" <<EOF

echo "⏹️  Stopping $service..."
if command -v docker-compose >/dev/null 2>&1; then
    docker-compose stop $service || true
elif command -v docker >/dev/null 2>&1 && command -v compose >/dev/null 2>&1; then
    docker compose stop $service || true
else
    echo "❌ Docker Compose not found"
    exit 1
fi

echo "✅ $service stopped"
EOF
    done

    cat >> "$SHUTDOWN_SCRIPT" <<EOF

echo "🎉 All services stopped successfully!"
EOF

    chmod +x "$SHUTDOWN_SCRIPT"
    echo "✅ Shutdown script saved to $SHUTDOWN_SCRIPT"
}

# Functions are available when script is sourced
# Note: Function exports removed for shell compatibility
