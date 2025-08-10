#!/usr/bin/env bats

# Test file for yaml_parser.sh
# Tests the shell-based YAML parser that replaces yq dependency

setup() {
    # Create a temporary directory for this test
    TEST_TEMP_DIR="$(mktemp -d)"

    # Create a test services.yaml file
    TEST_SERVICES_YAML="$TEST_TEMP_DIR/services.yaml"
    cat > "$TEST_SERVICES_YAML" <<EOF
services:
  actual:
    enabled: true
    container:
      image: actualbudget/actual-server:latest
      ports:
        - "5006:5006"
    nginx:
      domain: "actual.\${BASE_DOMAIN}"
    category: finance

  homepage:
    enabled: false
    container:
      image: ghcr.io/gethomepage/homepage:latest
      ports:
        - "3000:3000"
    nginx:
      domain: "home.\${BASE_DOMAIN}"
    category: dashboard

  cryptpad:
    enabled: true
    container:
      image: promasu/cryptpad:latest
      ports:
        - "3001:3001"
    nginx:
      domain: "pad.\${BASE_DOMAIN}"
    category: productivity

  photoprism:
    enabled: false
    container:
      image: photoprism/photoprism:latest
      ports:
        - "2342:2342"
    nginx:
      domain: "photos.\${BASE_DOMAIN}"
    category: media
EOF

    # Source the yaml_parser.sh script
    YAML_PARSER_SCRIPT="${BATS_TEST_DIRNAME}/../../../scripts/yaml_parser.sh"
}

teardown() {
    # Clean up temporary directory
    [ -n "$TEST_TEMP_DIR" ] && rm -rf "$TEST_TEMP_DIR"
}

@test "yaml_parser.sh script should exist and be executable" {
    [ -f "$YAML_PARSER_SCRIPT" ]
    [ -x "$YAML_PARSER_SCRIPT" ]
}

@test "get-enabled should return only services with enabled: true" {
    run "$YAML_PARSER_SCRIPT" get-enabled "$TEST_SERVICES_YAML"

    [ "$status" -eq 0 ]
    [ "${#lines[@]}" -eq 2 ]

    # Check that actual and cryptpad are returned (both enabled: true)
    echo "$output" | grep -q "actual"
    echo "$output" | grep -q "cryptpad"

    # Check that homepage and photoprism are NOT returned (both enabled: false)
    run bash -c "echo '$output' | grep -q 'homepage'"
    [ "$status" -ne 0 ]
    run bash -c "echo '$output' | grep -q 'photoprism'"
    [ "$status" -ne 0 ]
}

@test "get-services should return all service names" {
    run "$YAML_PARSER_SCRIPT" get-services "$TEST_SERVICES_YAML"

    [ "$status" -eq 0 ]
    [ "${#lines[@]}" -eq 4 ]

    # Check that all services are returned
    echo "$output" | grep -q "actual"
    echo "$output" | grep -q "homepage"
    echo "$output" | grep -q "cryptpad"
    echo "$output" | grep -q "photoprism"
}

@test "set-enabled should change service enabled status to true" {
    # First verify homepage is disabled
    run "$YAML_PARSER_SCRIPT" get-enabled "$TEST_SERVICES_YAML"
    run bash -c "echo '$output' | grep -q 'homepage'"
    [ "$status" -ne 0 ]

    # Enable homepage
    run "$YAML_PARSER_SCRIPT" set-enabled "$TEST_SERVICES_YAML" "homepage" "true"
    [ "$status" -eq 0 ]

    # Verify homepage is now enabled
    run "$YAML_PARSER_SCRIPT" get-enabled "$TEST_SERVICES_YAML"
    echo "$output" | grep -q "homepage"
}

@test "set-enabled should change service enabled status to false" {
    # First verify actual is enabled
    run "$YAML_PARSER_SCRIPT" get-enabled "$TEST_SERVICES_YAML"
    echo "$output" | grep -q "actual"

    # Disable actual
    run "$YAML_PARSER_SCRIPT" set-enabled "$TEST_SERVICES_YAML" "actual" "false"
    [ "$status" -eq 0 ]

    # Verify actual is now disabled
    run "$YAML_PARSER_SCRIPT" get-enabled "$TEST_SERVICES_YAML"
    run bash -c "echo '$output' | grep -q 'actual'"
    [ "$status" -ne 0 ]
}

@test "set-enabled should preserve other service configurations" {
    # Get original cryptpad config
    original_config=$(grep -A 10 "cryptpad:" "$TEST_SERVICES_YAML")

    # Change homepage enabled status
    run "$YAML_PARSER_SCRIPT" set-enabled "$TEST_SERVICES_YAML" "homepage" "true"
    [ "$status" -eq 0 ]

    # Verify cryptpad config is unchanged
    current_config=$(grep -A 10 "cryptpad:" "$TEST_SERVICES_YAML")
    [ "$original_config" = "$current_config" ]
}

@test "get-enabled should handle file with no enabled services" {
    # Create a file with all services disabled
    cat > "$TEST_SERVICES_YAML" <<EOF
services:
  service1:
    enabled: false
  service2:
    enabled: false
EOF

    run "$YAML_PARSER_SCRIPT" get-enabled "$TEST_SERVICES_YAML"
    [ "$status" -eq 0 ]
    [ "${#lines[@]}" -eq 0 ]
}

@test "get-services should handle file with no services section" {
    # Create a file without services section
    cat > "$TEST_SERVICES_YAML" <<EOF
version: "3.8"
networks:
  default:
    external: true
EOF

    run "$YAML_PARSER_SCRIPT" get-services "$TEST_SERVICES_YAML"
    [ "$status" -eq 0 ]
    [ "${#lines[@]}" -eq 0 ]
}

@test "yaml_parser should show usage for invalid command" {
    run "$YAML_PARSER_SCRIPT" invalid-command
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Usage:" ]]
}

@test "yaml_parser should show usage for missing arguments" {
    run "$YAML_PARSER_SCRIPT" get-enabled
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Usage:" ]]
}

@test "yaml_parser should handle missing file gracefully" {
    run "$YAML_PARSER_SCRIPT" get-enabled "/nonexistent/file.yaml"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Error:" ]]
}

@test "set-enabled should handle missing file gracefully" {
    run "$YAML_PARSER_SCRIPT" set-enabled "/nonexistent/file.yaml" "service" "true"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Error:" ]]
}

@test "set-enabled should add enabled property if it doesn't exist" {
    # Create a service without enabled property
    cat > "$TEST_SERVICES_YAML" <<EOF
services:
  newservice:
    container:
      image: nginx:latest
    nginx:
      domain: "new.example.com"
EOF

    # Set enabled to true
    run "$YAML_PARSER_SCRIPT" set-enabled "$TEST_SERVICES_YAML" "newservice" "true"
    [ "$status" -eq 0 ]

    # Verify it's now enabled
    run "$YAML_PARSER_SCRIPT" get-enabled "$TEST_SERVICES_YAML"
    echo "$output" | grep -q "newservice"
}

@test "yaml_parser should handle complex YAML with comments and spacing" {
    cat > "$TEST_SERVICES_YAML" <<EOF
# This is a comment
services:
  # Another comment
  service1:
    enabled: true  # Inline comment
    container:
      image: nginx:latest

  service2:
    # Some spacing
    enabled: false
    container:
      image: apache:latest

  # Final service
  service3:
    enabled: true
    container:
      image: caddy:latest
EOF

    run "$YAML_PARSER_SCRIPT" get-enabled "$TEST_SERVICES_YAML"
    [ "$status" -eq 0 ]
    [ "${#lines[@]}" -eq 2 ]
    echo "$output" | grep -q "service1"
    echo "$output" | grep -q "service3"
    run bash -c "echo '$output' | grep -q 'service2'"
    [ "$status" -ne 0 ]
}

@test "yaml_parser should be case-sensitive for enabled values" {
    # Test various true/false representations
    cat > "$TEST_SERVICES_YAML" <<EOF
services:
  service1:
    enabled: true
  service2:
    enabled: True
  service3:
    enabled: TRUE
  service4:
    enabled: false
  service5:
    enabled: False
  service6:
    enabled: FALSE
EOF

    run "$YAML_PARSER_SCRIPT" get-enabled "$TEST_SERVICES_YAML"
    [ "$status" -eq 0 ]

    # All true variants should be detected
    echo "$output" | grep -q "service1"
    echo "$output" | grep -q "service2"
    echo "$output" | grep -q "service3"

    # No false variants should be detected
    run bash -c "echo '$output' | grep -q 'service4'"
    [ "$status" -ne 0 ]
    run bash -c "echo '$output' | grep -q 'service5'"
    [ "$status" -ne 0 ]
    run bash -c "echo '$output' | grep -q 'service6'"
    [ "$status" -ne 0 ]
}
