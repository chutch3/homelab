#!/bin/bash
# Homelab Builder - Dynamic test configuration generator
# Provides functions to create homelab.yaml configurations for testing

# Create a minimal homelab.yaml for testing
create_minimal_homelab_config() {
    local config_file="$1"
    cat > "$config_file" <<EOF
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: test.local
  PROJECT_ROOT: /tmp/test

machines:
  driver:
    host: localhost
    user: testuser

services:
  nginx:
    image: nginx:alpine
    ports: [80, 443]
    deploy: all
    enabled: true
EOF
}

# Create a homelab.yaml with specific services
create_homelab_with_services() {
    local config_file="$1"
    shift
    local services=("$@")

    cat > "$config_file" <<EOF
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: test.local
  PROJECT_ROOT: /tmp/test

machines:
  driver:
    host: localhost
    user: testuser

services:
EOF

    for service in "${services[@]}"; do
        case "$service" in
            "actual")
                cat >> "$config_file" <<EOF
  actual:
    name: "Actual Budget"
    image: actualbudget/actual-server:latest
    port: 5006
    domain: budget
    deploy: driver
    enabled: true
    nginx:
      upstream: "actual:5006"
EOF
                ;;
            "homepage")
                cat >> "$config_file" <<EOF
  homepage:
    name: "Homepage"
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000
    domain: home
    deploy: driver
    enabled: true
    nginx:
      upstream: "homepage:3000"
EOF
                ;;
            "homeassistant")
                cat >> "$config_file" <<EOF
  homeassistant:
    name: "Home Assistant"
    image: ghcr.io/home-assistant/home-assistant:stable
    port: 8123
    domain: ha
    deploy: driver
    enabled: true
    nginx:
      upstream: "homeassistant:8123"
EOF
                ;;
            "nginx")
                cat >> "$config_file" <<EOF
  nginx:
    name: "Nginx Reverse Proxy"
    image: nginx:alpine
    ports: [80, 443]
    deploy: all
    enabled: true
EOF
                ;;
        esac
    done
}

# Create a multi-machine homelab.yaml
create_multi_machine_homelab_config() {
    local config_file="$1"
    cat > "$config_file" <<EOF
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: homelab.local
  PROJECT_ROOT: /tmp/test

machines:
  driver:
    host: 192.168.1.100
    user: testuser
    role: manager
  node-01:
    host: 192.168.1.101
    user: testuser
    role: worker
  node-02:
    host: 192.168.1.102
    user: testuser
    role: worker

services:
  nginx:
    image: nginx:alpine
    ports: [80, 443]
    deploy: all
    enabled: true

  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000
    deploy: driver
    enabled: true

  jellyfin:
    image: jellyfin/jellyfin:latest
    port: 8096
    deploy: all
    enabled: true

  static-site:
    image: nginx:alpine
    port: 8080
    deploy: node-01
    enabled: true

  secure-app:
    image: secure-app:latest
    port: 3000
    deploy: node-01
    enabled: true

  postgres:
    image: postgres:15
    port: 5432
    deploy: node-02
    enabled: true
    web: false

  redis:
    image: redis:alpine
    port: 6379
    deploy: node-02
    enabled: true
    web: false
EOF
}

# Create a docker swarm homelab.yaml
create_swarm_homelab_config() {
    local config_file="$1"
    cat > "$config_file" <<EOF
version: "2.0"
deployment: docker_swarm

environment:
  BASE_DOMAIN: homelab.local
  PROJECT_ROOT: /tmp/test
  SWARM_STACK_NAME: homelab
  SSL_ENABLED: true

machines:
  driver:
    host: 192.168.1.100
    user: testuser
    role: manager
    labels:
      - storage=ssd
  node-01:
    host: 192.168.1.101
    user: testuser
    role: worker
    labels:
      - storage=hdd

services:
  reverseproxy:
    name: "Reverse Proxy"
    image: nginx:alpine
    ports: [80, 443]
    deploy: all
    enabled: true
    overrides:
      docker_swarm:
        replicas: 1
        placement:
          constraints:
            - node.role == manager

  nginx:
    name: "Nginx"
    image: nginx:alpine
    ports: [80, 443]
    deploy: all
    enabled: true
    overrides:
      docker_swarm:
        replicas: 1

  web_app:
    name: "Web Application"
    image: nginx:alpine
    port: 8080
    deploy: any
    enabled: true
    overrides:
      docker_swarm:
        replicas: 3
        placement:
          constraints:
            - node.role == worker

  homepage:
    name: "Homepage"
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000
    deploy: driver
    enabled: true
    overrides:
      docker_swarm:
        replicas: 1

  jellyfin:
    name: "Jellyfin Media Server"
    image: jellyfin/jellyfin:latest
    port: 8096
    deploy: all
    enabled: true
    overrides:
      docker_swarm:
        replicas: 1
EOF
}

# Add a service to an existing homelab.yaml
add_service_to_homelab() {
    local config_file="$1"
    local service_name="$2"
    local service_config="$3"

    # Use yq to add the service
    yq eval ".services.${service_name} = ${service_config}" -i "$config_file"
}

# Enable/disable a service in homelab.yaml
set_service_enabled() {
    local config_file="$1"
    local service_name="$2"
    local enabled="$3"

    yq eval ".services.${service_name}.enabled = ${enabled}" -i "$config_file"
}

# Get the test fixture path
get_test_fixture_path() {
    echo "${BATS_TEST_DIRNAME}/../fixtures/homelab-test-fixture.yaml"
}

# Copy test fixture to a specific location
copy_test_fixture() {
    local target_file="$1"
    local fixture_path
    fixture_path="$(get_test_fixture_path)"
    cp "$fixture_path" "$target_file"
}

# Validate that a homelab.yaml file is valid
validate_homelab_config() {
    local config_file="$1"

    # Check that file exists and is valid YAML
    if [[ ! -f "$config_file" ]]; then
        echo "Config file does not exist: $config_file"
        return 1
    fi

    # Validate YAML syntax
    if ! yq eval '.' "$config_file" > /dev/null 2>&1; then
        echo "Invalid YAML syntax in: $config_file"
        return 1
    fi

    # Check required fields
    local version deployment
    version=$(yq eval '.version' "$config_file")
    deployment=$(yq eval '.deployment' "$config_file")

    if [[ "$version" == "null" ]]; then
        echo "Missing required field: version"
        return 1
    fi

    if [[ "$deployment" == "null" ]]; then
        echo "Missing required field: deployment"
        return 1
    fi

    return 0
}
