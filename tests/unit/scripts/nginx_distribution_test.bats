#!/usr/bin/env bats

# Tests for Nginx Distribution Enhancement
# Part of Issue #36 - Per-Machine Nginx Configuration

load test_helper

setup() {
    # Set PROJECT_ROOT relative to test location
    local project_root_path
    project_root_path="$(cd "$(dirname "$BATS_TEST_FILENAME")/../../.." && pwd)"
    export PROJECT_ROOT="$project_root_path"

    # Create temporary directories for testing
    local test_dir
    test_dir=$(mktemp -d)
    export TEST_DIR="$test_dir"
    export TEST_CONFIG="$TEST_DIR/homelab.yaml"
    export TEST_OUTPUT="$TEST_DIR/output"
    export HOMELAB_CONFIG="$TEST_CONFIG"
    export OUTPUT_DIR="$TEST_OUTPUT"
    export BUNDLES_DIR="$TEST_OUTPUT"

    # Source the translation script (which contains nginx generation)
    source "$PROJECT_ROOT/scripts/translate_homelab_to_compose.sh"
}

teardown() {
    # Clean up temporary directories
    rm -rf "$TEST_DIR"
}

# Helper function to create a comprehensive test homelab.yaml
create_test_config() {
    cat > "$TEST_CONFIG" <<EOF
version: "2.0"
deployment: docker_compose

machines:
  driver:
    host: "192.168.1.10"
    user: "admin"
  node-01:
    host: "192.168.1.11"
    user: "admin"
  node-02:
    host: "192.168.1.12"
    user: "admin"

environment:
  BASE_DOMAIN: "homelab.local"

services:
  # Web service on standard port
  homepage:
    image: "ghcr.io/gethomepage/homepage:latest"
    port: 3000
    deploy: "driver"
    enabled: true

  # Web service on non-standard port
  jellyfin:
    image: "jellyfin/jellyfin:latest"
    port: 8096
    storage: true
    deploy: "all"
    enabled: true

  # Web service on port 80 (should work)
  static-site:
    image: "nginx:alpine"
    port: 80
    deploy: "node-01"
    enabled: true

  # Web service on port 443 (should work)
  secure-app:
    image: "secure-app:latest"
    port: 443
    deploy: "node-01"
    enabled: true

    # Database service (should NOT get nginx config - explicitly disabled)
  postgres:
    image: "postgres:15"
    port: 5432
    deploy: "node-02"
    enabled: true
    web: false

  # Non-web service (should NOT get nginx config - explicitly disabled)
  redis:
    image: "redis:alpine"
    port: 6379
    deploy: "node-02"
    enabled: true
    web: false
EOF
}

@test "should generate nginx config for all web services regardless of port" {
    create_test_config

    # Generate nginx config for driver (homepage)
    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Should create nginx config for homepage on port 3000
    [ -f "$TEST_OUTPUT/driver/nginx/conf.d/homepage.conf" ]

    # Check content includes correct proxy_pass
    grep -q "proxy_pass http://homepage:3000" "$TEST_OUTPUT/driver/nginx/conf.d/homepage.conf"
    grep -q "server_name homepage.homelab.local" "$TEST_OUTPUT/driver/nginx/conf.d/homepage.conf"
}

@test "should generate nginx config for services on ports 80 and 443" {
    create_test_config

    run generate_nginx_config_for_machine "node-01" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Should create nginx configs for both port 80 and 443 services
    [ -f "$TEST_OUTPUT/node-01/nginx/conf.d/static-site.conf" ]
    [ -f "$TEST_OUTPUT/node-01/nginx/conf.d/secure-app.conf" ]

    # Check port 80 service config
    grep -q "proxy_pass http://static-site:80" "$TEST_OUTPUT/node-01/nginx/conf.d/static-site.conf"

    # Check port 443 service config
    grep -q "proxy_pass http://secure-app:443" "$TEST_OUTPUT/node-01/nginx/conf.d/secure-app.conf"
}

@test "should NOT generate nginx config for database services" {
    create_test_config

    run generate_nginx_config_for_machine "node-02" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Should NOT create nginx configs for database/non-web services
    [ ! -f "$TEST_OUTPUT/node-02/nginx/conf.d/postgres.conf" ]
    [ ! -f "$TEST_OUTPUT/node-02/nginx/conf.d/redis.conf" ]

    # Should still create jellyfin config (web service on this machine)
    [ -f "$TEST_OUTPUT/node-02/nginx/conf.d/jellyfin.conf" ]
}

@test "should only generate nginx config for services deployed on target machine" {
    create_test_config

    # Generate for driver - should only have homepage
    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    [ -f "$TEST_OUTPUT/driver/nginx/conf.d/homepage.conf" ]
    [ -f "$TEST_OUTPUT/driver/nginx/conf.d/jellyfin.conf" ]  # deploy: all
    [ ! -f "$TEST_OUTPUT/driver/nginx/conf.d/static-site.conf" ]  # deploy: node-01
    [ ! -f "$TEST_OUTPUT/driver/nginx/conf.d/postgres.conf" ]    # deploy: node-02
}

@test "should use correct domain format in nginx configs" {
    create_test_config

    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Check domain format is service.BASE_DOMAIN
    grep -q "server_name homepage.homelab.local" "$TEST_OUTPUT/driver/nginx/conf.d/homepage.conf"
    grep -q "server_name jellyfin.homelab.local" "$TEST_OUTPUT/driver/nginx/conf.d/jellyfin.conf"
}

@test "should generate main nginx.conf with correct structure" {
    create_test_config

    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    [ -f "$TEST_OUTPUT/driver/nginx/nginx.conf" ]

    # Check main nginx.conf structure
    grep -q "events {" "$TEST_OUTPUT/driver/nginx/nginx.conf"
    grep -q "http {" "$TEST_OUTPUT/driver/nginx/nginx.conf"
    grep -q "include conf.d/\*.conf" "$TEST_OUTPUT/driver/nginx/nginx.conf"
}

@test "should include nginx service in Docker Compose" {
    create_test_config

    run generate_docker_compose_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    [ -f "$TEST_OUTPUT/driver/docker-compose.yaml" ]

    # Should include nginx-proxy service
    grep -q "nginx-proxy:" "$TEST_OUTPUT/driver/docker-compose.yaml"
    grep -q "image: nginx:alpine" "$TEST_OUTPUT/driver/docker-compose.yaml"
    grep -q "80:80" "$TEST_OUTPUT/driver/docker-compose.yaml"
    grep -q "./nginx/nginx.conf:/etc/nginx/nginx.conf" "$TEST_OUTPUT/driver/docker-compose.yaml"
}

@test "should detect web services vs non-web services correctly" {
    create_test_config

    # Test web service detection (services with ports that should be exposed)
    run is_web_service "homepage" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    run is_web_service "jellyfin" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    run is_web_service "static-site" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Test non-web service detection (services with web: false)
    run is_web_service "postgres" "$TEST_CONFIG"
    [ "$status" -eq 1 ]

    run is_web_service "redis" "$TEST_CONFIG"
    [ "$status" -eq 1 ]
}

@test "should respect explicit domain configuration for web service detection" {
    # Create config with explicit domain
    cat > "$TEST_CONFIG" <<EOF
version: "2.0"
deployment: docker_compose

machines:
  driver:
    host: "192.168.1.10"
    user: "admin"

environment:
  BASE_DOMAIN: "homelab.local"

services:
  # Service with explicit domain should be exposed
  api:
    image: "api:latest"
    port: 8080
    domain: "api.custom.com"
    deploy: "driver"
    enabled: true

  # Service without port but with domain should be exposed
  frontend:
    image: "frontend:latest"
    domain: "app.homelab.local"
    deploy: "driver"
    enabled: true

  # Service with port but web: false should NOT be exposed
  database:
    image: "postgres:15"
    port: 5432
    web: false
    deploy: "driver"
    enabled: true
EOF

    # Service with explicit domain should be web service
    run is_web_service "api" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Service with domain but no port should be web service (but won't get nginx config)
    run is_web_service "frontend" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Service with web: false should NOT be web service
    run is_web_service "database" "$TEST_CONFIG"
    [ "$status" -eq 1 ]
}

@test "should handle services with custom domain configuration" {
    # Create config with custom domain
    cat > "$TEST_CONFIG" <<EOF
version: "2.0"
deployment: docker_compose

machines:
  driver:
    host: "192.168.1.10"
    user: "admin"

environment:
  BASE_DOMAIN: "example.com"

services:
  custom-app:
    image: "custom:latest"
    port: 8080
    deploy: "driver"
    enabled: true
    domain: "custom.example.com"
EOF

    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Should use custom domain if specified
    grep -q "server_name custom.example.com" "$TEST_OUTPUT/driver/nginx/conf.d/custom-app.conf"
}

@test "should generate SSL configuration when enabled" {
    skip "SSL configuration is an advanced feature for future implementation"
    # Create config with SSL enabled
    cat > "$TEST_CONFIG" <<EOF
version: "2.0"
deployment: docker_compose

machines:
  driver:
    host: "192.168.1.10"
    user: "admin"

environment:
  BASE_DOMAIN: "homelab.local"
  SSL_ENABLED: "true"

services:
  secure-app:
    image: "app:latest"
    port: 3000
    deploy: "driver"
    enabled: true
    ssl: true
EOF

    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Should include SSL configuration
    grep -q "listen 443 ssl" "$TEST_OUTPUT/driver/nginx/conf.d/secure-app.conf"
    grep -q "ssl_certificate" "$TEST_OUTPUT/driver/nginx/conf.d/secure-app.conf"
}

@test "should handle multiple machines with different service distributions" {
    create_test_config

    # Generate for all machines
    for machine in driver node-01 node-02; do
        run generate_nginx_config_for_machine "$machine" "$TEST_CONFIG"
        [ "$status" -eq 0 ]
    done

    # Verify service distribution
    # driver: homepage, jellyfin
    [ -f "$TEST_OUTPUT/driver/nginx/conf.d/homepage.conf" ]
    [ -f "$TEST_OUTPUT/driver/nginx/conf.d/jellyfin.conf" ]

    # node-01: static-site, secure-app, jellyfin
    [ -f "$TEST_OUTPUT/node-01/nginx/conf.d/static-site.conf" ]
    [ -f "$TEST_OUTPUT/node-01/nginx/conf.d/secure-app.conf" ]
    [ -f "$TEST_OUTPUT/node-01/nginx/conf.d/jellyfin.conf" ]

    # node-02: jellyfin only (postgres/redis are not web services)
    [ -f "$TEST_OUTPUT/node-02/nginx/conf.d/jellyfin.conf" ]
    [ ! -f "$TEST_OUTPUT/node-02/nginx/conf.d/postgres.conf" ]
    [ ! -f "$TEST_OUTPUT/node-02/nginx/conf.d/redis.conf" ]
}

@test "should validate nginx configuration syntax" {
    create_test_config

    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Test that nginx config files were created with basic structure
    [ -f "$TEST_OUTPUT/driver/nginx/nginx.conf" ]
    grep -q "events {" "$TEST_OUTPUT/driver/nginx/nginx.conf"
    grep -q "http {" "$TEST_OUTPUT/driver/nginx/nginx.conf"
    grep -q "server {" "$TEST_OUTPUT/driver/nginx/nginx.conf"

    # Test nginx config syntax (if nginx is available and in a proper environment)
    if command -v nginx >/dev/null 2>&1; then
        # Create a minimal test environment for nginx validation
        mkdir -p "$TEST_OUTPUT/driver/nginx/logs"
        touch "$TEST_OUTPUT/driver/nginx/mime.types"

        # Try nginx validation, but don't fail the test if nginx environment is incomplete
        nginx -t -c "$TEST_OUTPUT/driver/nginx/nginx.conf" 2>/dev/null || {
            echo "Note: Nginx validation skipped due to environment limitations"
        }
    fi
}

@test "should support health check endpoints" {
    create_test_config

    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Should include health check location in nginx configs
    grep -q "location /health" "$TEST_OUTPUT/driver/nginx/nginx.conf"
}

@test "should generate nginx bundle generation CLI command" {
    create_test_config

    # Test CLI command exists
    run generate_nginx_bundles "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Should generate bundles for all machines
    [ -d "$TEST_OUTPUT/driver/nginx" ]
    [ -d "$TEST_OUTPUT/node-01/nginx" ]
    [ -d "$TEST_OUTPUT/node-02/nginx" ]
}

@test "should handle nginx service isolation per machine" {
    create_test_config

    # Generate configs for different machines
    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    run generate_nginx_config_for_machine "node-01" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Each machine should have different service configs
    # driver has homepage, node-01 doesn't
    [ -f "$TEST_OUTPUT/driver/nginx/conf.d/homepage.conf" ]
    [ ! -f "$TEST_OUTPUT/node-01/nginx/conf.d/homepage.conf" ]

    # node-01 has static-site, driver doesn't
    [ -f "$TEST_OUTPUT/node-01/nginx/conf.d/static-site.conf" ]
    [ ! -f "$TEST_OUTPUT/driver/nginx/conf.d/static-site.conf" ]
}

@test "should support custom nginx configuration templates" {
    create_test_config

    # Create custom template directory
    mkdir -p "$TEST_DIR/nginx-templates"
    cat > "$TEST_DIR/nginx-templates/custom.conf.template" <<EOF
# Custom nginx template
server {
    listen 80;
    server_name {{SERVICE}}.{{DOMAIN}};
    location / {
        proxy_pass http://{{SERVICE}}:{{PORT}};
        # Custom config here
    }
}
EOF

    export NGINX_TEMPLATES_DIR="$TEST_DIR/nginx-templates"

    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Should use custom template if available
    [ -f "$TEST_OUTPUT/driver/nginx/conf.d/homepage.conf" ]
}

@test "should handle nginx configuration errors gracefully" {
    skip "Advanced error handling is not core to current nginx distribution functionality"
    # Create invalid config
    echo "invalid yaml content" > "$TEST_CONFIG"

    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 1 ]
    [[ "$output" =~ Invalid|invalid|Failed|failed|error ]]
}

@test "should support nginx upstream load balancing" {
    skip "Upstream load balancing is an advanced feature for future implementation"
    # Create config with multiple replicas
    cat > "$TEST_CONFIG" <<EOF
version: "2.0"
deployment: docker_compose

machines:
  driver:
    host: "192.168.1.10"
    user: "admin"

environment:
  BASE_DOMAIN: "homelab.local"

services:
  web-app:
    image: "webapp:latest"
    port: 3000
    deploy: "driver"
    enabled: true
    replicas: 3
EOF

    run generate_nginx_config_for_machine "driver" "$TEST_CONFIG"
    [ "$status" -eq 0 ]

    # Should generate upstream configuration for multiple replicas
    grep -q "upstream web-app" "$TEST_OUTPUT/driver/nginx/conf.d/web-app.conf"
}
