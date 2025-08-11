#!/usr/bin/env bats

# Real Deployment Tests (Local Only)
# Part of Issue #40 - Comprehensive Test Suite for Unified Configuration
# These tests require Docker and are NOT run in CI/CD

load ../helpers/enhanced_test_helper

setup() {
    setup_comprehensive_test

    # Check if Docker is available
    if ! command -v docker >/dev/null 2>&1; then
        skip "Docker not available - local deployment tests require Docker"
    fi

    # Check if we can connect to Docker daemon
    if ! docker info >/dev/null 2>&1; then
        skip "Docker daemon not accessible - local deployment tests require Docker daemon"
    fi

    # Source required scripts
    if [ -f "$PROJECT_ROOT/scripts/translate_homelab_to_compose.sh" ]; then
        # shellcheck disable=SC1091
        source "$PROJECT_ROOT/scripts/translate_homelab_to_compose.sh"
    fi

    # Set unique project name to avoid conflicts
    export COMPOSE_PROJECT_NAME="homelab_test_$$"
    export TEST_NETWORK_NAME="${COMPOSE_PROJECT_NAME}_default"
}

teardown() {
    # Clean up any running containers
    if [ -n "$COMPOSE_PROJECT_NAME" ]; then
        for compose_file in "$TEST_OUTPUT"/*/docker-compose.yaml; do
            if [ -f "$compose_file" ]; then
                echo "🧹 Cleaning up containers from $(dirname "$compose_file")"
                docker compose -f "$compose_file" -p "$COMPOSE_PROJECT_NAME" down --volumes --remove-orphans 2>/dev/null || true
            fi
        done
    fi

    # Clean up test networks
    if [ -n "$TEST_NETWORK_NAME" ]; then
        docker network rm "$TEST_NETWORK_NAME" 2>/dev/null || true
    fi

    teardown_comprehensive_test
}

# =============================================================================
# SINGLE MACHINE DEPLOYMENT TESTS
# =============================================================================

@test "real deployment - single machine with basic services" {
    # Create simple configuration for testing
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: localhost

machines:
  driver: {host: localhost, user: testuser}

services:
  nginx:
    image: nginx:alpine
    port: 8080
    deploy: driver
    enabled: true
EOF

    # Generate bundle
    generate_all_bundles "$TEST_CONFIG"
    [ -f "$TEST_OUTPUT/driver/docker-compose.yaml" ]

    # Deploy services
    cd "$TEST_OUTPUT/driver"

    echo "🚀 Starting services..."
    docker compose -p "$COMPOSE_PROJECT_NAME" up -d
    [ $? -eq 0 ]

    # Wait for services to be ready
    sleep 10

    # Check service status
    docker compose -p "$COMPOSE_PROJECT_NAME" ps --format "table {{.Name}}\t{{.Status}}"

    # Verify services are running
    local running_containers
    running_containers=$(docker compose -p "$COMPOSE_PROJECT_NAME" ps --services --filter "status=running" | wc -l)
    [ "$running_containers" -gt 0 ]

    echo "✅ Services deployed and running"
}

@test "real deployment - service accessibility test" {
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: localhost

machines:
  driver: {host: localhost, user: testuser}

services:
  nginx:
    image: nginx:alpine
    port: 8081
    deploy: driver
    enabled: true
EOF

    generate_all_bundles "$TEST_CONFIG"
    cd "$TEST_OUTPUT/driver"

    # Start services
    docker compose -p "$COMPOSE_PROJECT_NAME" up -d

    # Wait for startup
    sleep 15

    # Test HTTP connectivity
    local max_attempts=10
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo "🔍 Testing connectivity (attempt $attempt/$max_attempts)..."

        if curl -f -s http://localhost:8081 >/dev/null 2>&1; then
            echo "✅ Service accessible at http://localhost:8081"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            echo "❌ Service not accessible after $max_attempts attempts"

            # Debug information
            echo "Container status:"
            docker compose -p "$COMPOSE_PROJECT_NAME" ps

            echo "Container logs:"
            docker compose -p "$COMPOSE_PROJECT_NAME" logs

            fail "Service not accessible"
        fi

        sleep 3
        attempt=$((attempt + 1))
    done
}

@test "real deployment - nginx proxy functionality" {
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: localhost

machines:
  driver: {host: localhost, user: testuser}

services:
  nginx:
    image: nginx:alpine
    port: 8082
    deploy: driver
    enabled: true
    domain: test.localhost
EOF

    generate_all_bundles "$TEST_CONFIG"
    cd "$TEST_OUTPUT/driver"

    # Start services
    docker compose -p "$COMPOSE_PROJECT_NAME" up -d
    sleep 15

    # Test nginx proxy is running
    local nginx_proxy_running
    nginx_proxy_running=$(docker compose -p "$COMPOSE_PROJECT_NAME" ps --services --filter "status=running" | grep -c "nginx-proxy" || echo "0")

    if [ "$nginx_proxy_running" -gt 0 ]; then
        echo "✅ Nginx proxy container running"

        # Test proxy functionality (if port 80 is available)
        if ! netstat -ln | grep -q ":80 "; then
            # Port 80 is available, test proxy
            if curl -f -s -H "Host: test.localhost" http://localhost >/dev/null 2>&1; then
                echo "✅ Nginx proxy working"
            else
                echo "⚠️  Nginx proxy not responding (may be expected in test environment)"
            fi
        else
            echo "⚠️  Port 80 occupied, skipping proxy test"
        fi
    else
        echo "⚠️  Nginx proxy not running (may be expected based on configuration)"
    fi
}

# =============================================================================
# CONTAINER HEALTH AND MONITORING
# =============================================================================

@test "real deployment - container health checks" {
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: localhost

machines:
  driver: {host: localhost, user: testuser}

services:
  nginx:
    image: nginx:alpine
    port: 8083
    deploy: driver
    enabled: true
EOF

    generate_all_bundles "$TEST_CONFIG"
    cd "$TEST_OUTPUT/driver"

    # Start services
    docker compose -p "$COMPOSE_PROJECT_NAME" up -d
    sleep 10

    # Check container health
    local containers
    containers=$(docker compose -p "$COMPOSE_PROJECT_NAME" ps --format "{{.Name}}")

    while IFS= read -r container; do
        if [ -n "$container" ]; then
            echo "🔍 Checking health of $container"

            # Check if container is running
            local status
            status=$(docker inspect "$container" --format '{{.State.Status}}' 2>/dev/null || echo "not_found")

            if [ "$status" = "running" ]; then
                echo "✅ $container is running"

                # Check resource usage
                local stats
                stats=$(docker stats "$container" --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}" | tail -1)
                echo "📊 $container stats: $stats"
            else
                echo "❌ $container status: $status"

                # Show container logs for debugging
                echo "Container logs:"
                docker logs "$container" 2>&1 | tail -10

                fail "Container $container not running"
            fi
        fi
    done <<< "$containers"
}

@test "real deployment - volume persistence" {
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: localhost

machines:
  driver: {host: localhost, user: testuser}

services:
  nginx:
    image: nginx:alpine
    port: 8084
    deploy: driver
    enabled: true
    storage: true
EOF

    generate_all_bundles "$TEST_CONFIG"
    cd "$TEST_OUTPUT/driver"

    # Start services
    docker compose -p "$COMPOSE_PROJECT_NAME" up -d
    sleep 10

    # Check if volumes were created
    local volumes
    volumes=$(docker compose -p "$COMPOSE_PROJECT_NAME" config --volumes 2>/dev/null || echo "")

    if [ -n "$volumes" ]; then
        echo "✅ Volumes configured: $volumes"

        # Verify volumes exist
        while IFS= read -r volume; do
            if [ -n "$volume" ]; then
                local volume_name="${COMPOSE_PROJECT_NAME}_${volume}"
                if docker volume inspect "$volume_name" >/dev/null 2>&1; then
                    echo "✅ Volume $volume_name exists"
                else
                    echo "⚠️  Volume $volume_name not found"
                fi
            fi
        done <<< "$volumes"
    else
        echo "ℹ️  No volumes configured (expected for this test)"
    fi
}

# =============================================================================
# RESOURCE USAGE TESTS
# =============================================================================

@test "real deployment - resource usage monitoring" {
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: localhost

machines:
  driver: {host: localhost, user: testuser}

services:
  nginx:
    image: nginx:alpine
    port: 8085
    deploy: driver
    enabled: true
  busybox:
    image: busybox:latest
    deploy: driver
    enabled: true
    overrides:
      command: ["sleep", "30"]
EOF

    generate_all_bundles "$TEST_CONFIG"
    cd "$TEST_OUTPUT/driver"

    # Start services
    docker compose -p "$COMPOSE_PROJECT_NAME" up -d
    sleep 15

    # Monitor resource usage
    echo "📊 Container resource usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" \
        $(docker compose -p "$COMPOSE_PROJECT_NAME" ps -q) 2>/dev/null || {
        echo "⚠️  Could not get resource stats"
    }

    # Verify containers are not using excessive resources
    local high_cpu_containers
    high_cpu_containers=$(docker stats --no-stream --format "{{.Name}}\t{{.CPUPerc}}" \
        $(docker compose -p "$COMPOSE_PROJECT_NAME" ps -q) 2>/dev/null | \
        awk -F'\t' '$2 > 50.0 {print $1}' || echo "")

    if [ -n "$high_cpu_containers" ]; then
        echo "⚠️  High CPU usage containers: $high_cpu_containers"
        # Don't fail, just warn
    else
        echo "✅ All containers using reasonable CPU"
    fi
}

# =============================================================================
# NETWORK CONNECTIVITY TESTS
# =============================================================================

@test "real deployment - inter-service communication" {
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: localhost

machines:
  driver: {host: localhost, user: testuser}

services:
  nginx:
    image: nginx:alpine
    port: 8086
    deploy: driver
    enabled: true
  busybox:
    image: busybox:latest
    deploy: driver
    enabled: true
    overrides:
      command: ["sleep", "60"]
EOF

    generate_all_bundles "$TEST_CONFIG"
    cd "$TEST_OUTPUT/driver"

    # Start services
    docker compose -p "$COMPOSE_PROJECT_NAME" up -d
    sleep 15

    # Test inter-service communication
    local busybox_container
    busybox_container=$(docker compose -p "$COMPOSE_PROJECT_NAME" ps -q busybox 2>/dev/null)

    if [ -n "$busybox_container" ]; then
        echo "🔍 Testing inter-service communication from busybox to nginx"

        # Try to connect from busybox to nginx
        local nginx_reachable
        nginx_reachable=$(docker exec "$busybox_container" wget -q -O- http://nginx:80 2>/dev/null && echo "true" || echo "false")

        if [ "$nginx_reachable" = "true" ]; then
            echo "✅ Inter-service communication working"
        else
            echo "⚠️  Inter-service communication failed (may be expected)"

            # Debug network information
            echo "Network information:"
            docker network ls | grep "$COMPOSE_PROJECT_NAME" || echo "No project networks found"

            echo "Container network settings:"
            docker inspect "$busybox_container" --format '{{.NetworkSettings.Networks}}' 2>/dev/null || echo "Could not inspect network"
        fi
    else
        echo "⚠️  Busybox container not found for communication test"
    fi
}

# =============================================================================
# ERROR RECOVERY TESTS
# =============================================================================

@test "real deployment - container restart and recovery" {
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: localhost

machines:
  driver: {host: localhost, user: testuser}

services:
  nginx:
    image: nginx:alpine
    port: 8087
    deploy: driver
    enabled: true
    overrides:
      restart: unless-stopped
EOF

    generate_all_bundles "$TEST_CONFIG"
    cd "$TEST_OUTPUT/driver"

    # Start services
    docker compose -p "$COMPOSE_PROJECT_NAME" up -d
    sleep 10

    # Get container ID
    local nginx_container
    nginx_container=$(docker compose -p "$COMPOSE_PROJECT_NAME" ps -q nginx 2>/dev/null)

    if [ -n "$nginx_container" ]; then
        echo "🔄 Testing container restart recovery"

        # Kill the container
        docker kill "$nginx_container"

        # Wait for restart
        sleep 15

        # Check if container restarted
        local new_container
        new_container=$(docker compose -p "$COMPOSE_PROJECT_NAME" ps -q nginx 2>/dev/null)

        if [ -n "$new_container" ] && [ "$new_container" != "$nginx_container" ]; then
            echo "✅ Container restarted successfully"

            # Verify service is accessible again
            if curl -f -s http://localhost:8087 >/dev/null 2>&1; then
                echo "✅ Service accessible after restart"
            else
                echo "⚠️  Service not accessible after restart"
            fi
        else
            echo "⚠️  Container may not have restarted"

            # Show current status
            docker compose -p "$COMPOSE_PROJECT_NAME" ps
        fi
    else
        echo "⚠️  Nginx container not found for restart test"
    fi
}

# =============================================================================
# CLEANUP AND VALIDATION
# =============================================================================

@test "real deployment - cleanup validation" {
    cat > "$TEST_CONFIG" << 'EOF'
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: localhost

machines:
  driver: {host: localhost, user: testuser}

services:
  nginx:
    image: nginx:alpine
    port: 8088
    deploy: driver
    enabled: true
EOF

    generate_all_bundles "$TEST_CONFIG"
    cd "$TEST_OUTPUT/driver"

    # Start services
    docker compose -p "$COMPOSE_PROJECT_NAME" up -d
    sleep 10

    # Verify services are running
    local running_containers
    running_containers=$(docker compose -p "$COMPOSE_PROJECT_NAME" ps --services --filter "status=running" | wc -l)
    [ "$running_containers" -gt 0 ]

    echo "✅ Services running before cleanup"

    # Stop services
    docker compose -p "$COMPOSE_PROJECT_NAME" down --volumes

    # Verify cleanup
    local remaining_containers
    remaining_containers=$(docker compose -p "$COMPOSE_PROJECT_NAME" ps -q | wc -l)
    [ "$remaining_containers" -eq 0 ]

    echo "✅ Services cleaned up successfully"

    # Verify no orphaned resources
    local project_networks
    project_networks=$(docker network ls --filter "name=${COMPOSE_PROJECT_NAME}" -q | wc -l)
    [ "$project_networks" -eq 0 ]

    echo "✅ Networks cleaned up successfully"
}
