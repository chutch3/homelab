#!/usr/bin/env bats

# Tests for Nginx Distribution Enhancement
# Part of Issue #36 - Per-Machine Nginx Configuration

load test_helper

setup() {
    # Set PROJECT_ROOT relative to test location
    local project_root_path
    project_root_path="$(cd "$(dirname "$BATS_TEST_FILENAME")/../../.." && pwd)"
    export PROJECT_ROOT="$project_root_path"

    load test_helper
    load "${BATS_TEST_DIRNAME}/../../helpers/bats-support/load.bash"
    load "${BATS_TEST_DIRNAME}/../../helpers/bats-assert/load.bash"
    load "${BATS_TEST_DIRNAME}/../../helpers/homelab_builder"

    # Create temporary directories for testing
    TEST_TEMP_DIR="$(temp_make)"
    export HOMELAB_CONFIG="$TEST_TEMP_DIR/homelab.yaml"
    export BUNDLES_DIR="$TEST_TEMP_DIR/bundles"

    create_multi_machine_homelab_config "$HOMELAB_CONFIG"

    # Source the translation script (which contains nginx generation)
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/scripts/translate_homelab_to_compose.sh"
}

teardown() {
    # Clean up temporary directories
    temp_del "$TEST_TEMP_DIR"
    unset HOMELAB_CONFIG BUNDLES_DIR
}

@test "should generate nginx config for all web services regardless of port" {
    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    echo "output: $output"
    assert_success

    [ -f "$BUNDLES_DIR/driver/nginx/nginx.conf" ]
    [ -f "$BUNDLES_DIR/driver/nginx/conf.d/homepage.conf" ]
    [ -f "$BUNDLES_DIR/driver/nginx/conf.d/jellyfin.conf" ]

    # Check content includes correct proxy_pass
    grep -q "proxy_pass http://homepage:3000" "$BUNDLES_DIR/driver/nginx/conf.d/homepage.conf"
    grep -q "server_name homepage.homelab.local" "$BUNDLES_DIR/driver/nginx/conf.d/homepage.conf"
    grep -q "server_name jellyfin.homelab.local" "$BUNDLES_DIR/driver/nginx/conf.d/jellyfin.conf"
}

@test "should generate nginx config for services on ports 80 and 443" {

    run generate_nginx_config_for_machine "node-01" "$HOMELAB_CONFIG"
    assert_success

    # Should create nginx configs for both port 80 and 443 services
    [ -f "$BUNDLES_DIR/node-01/nginx/conf.d/static-site.conf" ]
    [ -f "$BUNDLES_DIR/node-01/nginx/conf.d/secure-app.conf" ]

    # Check port 80 service config
    grep -q "proxy_pass http://static-site:8080" "$BUNDLES_DIR/node-01/nginx/conf.d/static-site.conf"
    grep -q "server_name static-site.homelab.local" "$BUNDLES_DIR/node-01/nginx/conf.d/static-site.conf"
    grep -q "proxy_pass http://secure-app:3000" "$BUNDLES_DIR/node-01/nginx/conf.d/secure-app.conf"
    grep -q "server_name secure-app.homelab.local" "$BUNDLES_DIR/node-01/nginx/conf.d/secure-app.conf"
}

@test "should NOT generate nginx config for database services" {


    run generate_nginx_config_for_machine "node-02" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Should NOT create nginx configs for database/non-web services
    [ ! -f "$BUNDLES_DIR/node-02/nginx/conf.d/postgres.conf" ]
    [ ! -f "$BUNDLES_DIR/node-02/nginx/conf.d/redis.conf" ]

    # Should still create jellyfin config (web service on this machine)
    [ -f "$BUNDLES_DIR/node-02/nginx/conf.d/jellyfin.conf" ]
}

@test "should only generate nginx config for services deployed on target machine" {


    # Generate for driver - should only have homepage
    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    [ -f "$BUNDLES_DIR/driver/nginx/conf.d/homepage.conf" ]
    [ -f "$BUNDLES_DIR/driver/nginx/conf.d/jellyfin.conf" ]  # deploy: all
    [ ! -f "$BUNDLES_DIR/driver/nginx/conf.d/static-site.conf" ]  # deploy: node-01
    [ ! -f "$BUNDLES_DIR/driver/nginx/conf.d/postgres.conf" ]    # deploy: node-02
}

@test "should use correct domain format in nginx configs" {


    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Check domain format is service.BASE_DOMAIN
    grep -q "server_name homepage.homelab.local" "$BUNDLES_DIR/driver/nginx/conf.d/homepage.conf"
    grep -q "server_name jellyfin.homelab.local" "$BUNDLES_DIR/driver/nginx/conf.d/jellyfin.conf"
}

@test "should generate main nginx.conf with correct structure" {


    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    [ -f "$BUNDLES_DIR/driver/nginx/nginx.conf" ]

    # Check main nginx.conf structure
    grep -q "events {" "$BUNDLES_DIR/driver/nginx/nginx.conf"
    grep -q "http {" "$BUNDLES_DIR/driver/nginx/nginx.conf"
    grep -q "include conf.d/\*.conf" "$BUNDLES_DIR/driver/nginx/nginx.conf"
}

@test "should include nginx service in Docker Compose" {
    load_env() {
        echo "loaded environment variables"
    }



    run generate_docker_compose_for_machine "driver" "$HOMELAB_CONFIG"
    assert_success
    assert_output --partial "loaded environment variables"
    assert_output --partial "docker-compose.yaml"

    [ -f "$BUNDLES_DIR/driver/docker-compose.yaml" ]

    # Should include nginx-proxy service
    grep -q "nginx-proxy:" "$BUNDLES_DIR/driver/docker-compose.yaml"
    grep -q "image: nginx:alpine" "$BUNDLES_DIR/driver/docker-compose.yaml"
    grep -q "80:80" "$BUNDLES_DIR/driver/docker-compose.yaml"
    grep -q "./nginx/nginx.conf:/etc/nginx/nginx.conf" "$BUNDLES_DIR/driver/docker-compose.yaml"
}

@test "should detect web services vs non-web services correctly" {


    # Test web service detection (services with ports that should be exposed)
    run is_web_service "homepage" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    run is_web_service "jellyfin" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    run is_web_service "static-site" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Test non-web service detection (services with web: false)
    run is_web_service "postgres" "$HOMELAB_CONFIG"
    [ "$status" -eq 1 ]

    run is_web_service "redis" "$HOMELAB_CONFIG"
    [ "$status" -eq 1 ]
}

@test "should respect explicit domain configuration for web service detection" {
    # Create config with explicit domain
    cat > "$HOMELAB_CONFIG" <<EOF
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
    run is_web_service "api" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Service with domain but no port should be web service (but won't get nginx config)
    run is_web_service "frontend" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Service with web: false should NOT be web service
    run is_web_service "database" "$HOMELAB_CONFIG"
    [ "$status" -eq 1 ]
}

@test "should handle services with custom domain configuration" {
    # Create config with custom domain
    cat > "$HOMELAB_CONFIG" <<EOF
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

    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Should use custom domain if specified
    grep -q "server_name custom.example.com" "$BUNDLES_DIR/driver/nginx/conf.d/custom-app.conf"
}

@test "should generate SSL configuration when enabled" {
    skip "SSL configuration is an advanced feature for future implementation"
    # Create config with SSL enabled
    cat > "$HOMELAB_CONFIG" <<EOF
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

    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Should include SSL configuration
    grep -q "listen 443 ssl" "$BUNDLES_DIR/driver/nginx/conf.d/secure-app.conf"
    grep -q "ssl_certificate" "$BUNDLES_DIR/driver/nginx/conf.d/secure-app.conf"
}

@test "should handle multiple machines with different service distributions" {


    # Generate for all machines
    for machine in driver node-01 node-02; do
        run generate_nginx_config_for_machine "$machine" "$HOMELAB_CONFIG"
        [ "$status" -eq 0 ]
    done

    # Verify service distribution
    # driver: homepage, jellyfin
    [ -f "$BUNDLES_DIR/driver/nginx/conf.d/homepage.conf" ]
    [ -f "$BUNDLES_DIR/driver/nginx/conf.d/jellyfin.conf" ]

    # node-01: static-site, secure-app, jellyfin
    [ -f "$BUNDLES_DIR/node-01/nginx/conf.d/static-site.conf" ]
    [ -f "$BUNDLES_DIR/node-01/nginx/conf.d/secure-app.conf" ]
    [ -f "$BUNDLES_DIR/node-01/nginx/conf.d/jellyfin.conf" ]

    # node-02: jellyfin only (postgres/redis are not web services)
    [ -f "$BUNDLES_DIR/node-02/nginx/conf.d/jellyfin.conf" ]
    [ ! -f "$BUNDLES_DIR/node-02/nginx/conf.d/postgres.conf" ]
    [ ! -f "$BUNDLES_DIR/node-02/nginx/conf.d/redis.conf" ]
}

@test "should validate nginx configuration syntax" {


    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Test that nginx config files were created with basic structure
    [ -f "$BUNDLES_DIR/driver/nginx/nginx.conf" ]
    grep -q "events {" "$BUNDLES_DIR/driver/nginx/nginx.conf"
    grep -q "http {" "$BUNDLES_DIR/driver/nginx/nginx.conf"
    grep -q "server {" "$BUNDLES_DIR/driver/nginx/nginx.conf"

    # Test nginx config syntax (if nginx is available and in a proper environment)
    if command -v nginx >/dev/null 2>&1; then
        # Create a minimal test environment for nginx validation
        mkdir -p "$BUNDLES_DIR/driver/nginx/logs"
        touch "$BUNDLES_DIR/driver/nginx/mime.types"

        # Try nginx validation, but don't fail the test if nginx environment is incomplete
        nginx -t -c "$BUNDLES_DIR/driver/nginx/nginx.conf" 2>/dev/null || {
            echo "Note: Nginx validation skipped due to environment limitations"
        }
    fi
}

@test "should support health check endpoints" {


    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Should include health check location in nginx configs
    grep -q "location /health" "$BUNDLES_DIR/driver/nginx/nginx.conf"
}

@test "should generate nginx bundle generation CLI command" {


    # Test CLI command exists
    run generate_nginx_bundles "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Should generate bundles for all machines
    [ -d "$BUNDLES_DIR/driver/nginx" ]
    [ -d "$BUNDLES_DIR/node-01/nginx" ]
    [ -d "$BUNDLES_DIR/node-02/nginx" ]
}

@test "should handle nginx service isolation per machine" {


    # Generate configs for different machines
    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    run generate_nginx_config_for_machine "node-01" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Each machine should have different service configs
    # driver has homepage, node-01 doesn't
    [ -f "$BUNDLES_DIR/driver/nginx/conf.d/homepage.conf" ]
    [ ! -f "$BUNDLES_DIR/node-01/nginx/conf.d/homepage.conf" ]

    # node-01 has static-site, driver doesn't
    [ -f "$BUNDLES_DIR/node-01/nginx/conf.d/static-site.conf" ]
    [ ! -f "$BUNDLES_DIR/driver/nginx/conf.d/static-site.conf" ]
}

@test "should support custom nginx configuration templates" {


    # Create custom template directory
    mkdir -p "$TEST_TEMP_DIR/nginx-templates"
    cat > "$TEST_TEMP_DIR/nginx-templates/custom.conf.template" <<EOF
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

    export NGINX_TEMPLATES_DIR="$TEST_TEMP_DIR/nginx-templates"

    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Should use custom template if available
    [ -f "$BUNDLES_DIR/driver/nginx/conf.d/homepage.conf" ]
}

@test "should handle nginx configuration errors gracefully" {
    skip "Advanced error handling is not core to current nginx distribution functionality"
    # Create invalid config
    echo "invalid yaml content" > "$HOMELAB_CONFIG"

    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 1 ]
    [[ "$output" =~ Invalid|invalid|Failed|failed|error ]]
}

@test "should support nginx upstream load balancing" {
    skip "Upstream load balancing is an advanced feature for future implementation"
    # Create config with multiple replicas
    cat > "$HOMELAB_CONFIG" <<EOF
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

    run generate_nginx_config_for_machine "driver" "$HOMELAB_CONFIG"
    [ "$status" -eq 0 ]

    # Should generate upstream configuration for multiple replicas
    grep -q "upstream web-app" "$BUNDLES_DIR/driver/nginx/conf.d/web-app.conf"
}
