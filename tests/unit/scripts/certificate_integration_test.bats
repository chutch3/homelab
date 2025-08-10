#!/usr/bin/env bats

# Test file for certificate integration into generated files
# Tests automatic certificate generation during deployment

setup() {
    # Create a temporary directory for this test
    TEST_TEMP_DIR="$(mktemp -d)"

    # Create a test .env file
    TEST_ENV_FILE="$TEST_TEMP_DIR/.env"
    cat > "$TEST_ENV_FILE" <<EOF
BASE_DOMAIN=test.example.com
WILDCARD_DOMAIN=*.test.example.com
CF_Token=test_token_123
DNS_SERVER=1.1.1.1
EOF

    # Create a test services.yaml file
    TEST_SERVICES_YAML="$TEST_TEMP_DIR/config/services.yaml"
    mkdir -p "$(dirname "$TEST_SERVICES_YAML")"
    cat > "$TEST_SERVICES_YAML" <<EOF
services:
  actual:
    enabled: true
    container:
      image: actualbudget/actual-server:latest
    nginx:
      domain: "budget.\${BASE_DOMAIN}"
    category: finance

  homepage:
    enabled: true
    container:
      image: ghcr.io/gethomepage/homepage:latest
    nginx:
      domain: "dashboard.\${BASE_DOMAIN}"
    category: core
EOF

    # Mock PROJECT_ROOT to our test directory
    export PROJECT_ROOT="$TEST_TEMP_DIR"
    export SERVICES_CONFIG="$TEST_SERVICES_YAML"

    # Source the service generator
    # shellcheck disable=SC1091
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"
}

teardown() {
    # Clean up temporary directory
    [ -n "$TEST_TEMP_DIR" ] && rm -rf "$TEST_TEMP_DIR"
}

@test "certificate configuration should be included in generated files" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Should create certificate configuration files
    [ -f "$TEST_TEMP_DIR/generated/certificates/acme-config.yaml" ]
    [ -f "$TEST_TEMP_DIR/generated/certificates/cert-init.sh" ]
}

@test "generated docker-compose should include certificate initialization" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Generated compose should include ACME service
    grep -q "acme:" "$TEST_TEMP_DIR/generated/deployments/docker-compose.yaml"
    grep -q "acme.sh" "$TEST_TEMP_DIR/generated/deployments/docker-compose.yaml"
}

@test "generated swarm stack should include certificate secrets" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Generated swarm should define certificate secrets
    grep -q "ssl_full.pem:" "$TEST_TEMP_DIR/generated/deployments/swarm-stack.yaml"
    grep -q "ssl_key.pem:" "$TEST_TEMP_DIR/generated/deployments/swarm-stack.yaml"
    grep -q "ssl_ca.pem:" "$TEST_TEMP_DIR/generated/deployments/swarm-stack.yaml"
    grep -q "ssl_dhparam.pem:" "$TEST_TEMP_DIR/generated/deployments/swarm-stack.yaml"
}

@test "certificate checker script should be generated" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Should generate certificate status checker
    [ -f "$TEST_TEMP_DIR/generated/certificates/check-certs.sh" ]
    [ -x "$TEST_TEMP_DIR/generated/certificates/check-certs.sh" ]
}

@test "deployment should auto-initialize certificates if missing" {
    # Test that certificate checking is integrated into selfhosted.sh

    # Check that the enhanced_deploy function in selfhosted.sh includes cert checking
    grep -q "Checking certificate status" "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
    grep -q "ensure_certs_exist" "${BATS_TEST_DIRNAME}/../../../selfhosted.sh"
}

@test "certificate configuration should use BASE_DOMAIN from env" {
    # Create generated directory structure
    run generate_all_to_generated_dir
    [ "$status" -eq 0 ]

    # Certificate files should reference the correct domain
    if [ -f "$TEST_TEMP_DIR/generated/certificates/cert-init.sh" ]; then
        grep -q "test.example.com" "$TEST_TEMP_DIR/generated/certificates/cert-init.sh"
        grep -q "\\*.test.example.com" "$TEST_TEMP_DIR/generated/certificates/cert-init.sh"
    fi
}

@test "certificate renewal script should be generated for automation" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Should generate renewal automation
    [ -f "$TEST_TEMP_DIR/generated/certificates/renew-certs.sh" ]
    [ -x "$TEST_TEMP_DIR/generated/certificates/renew-certs.sh" ]

    # Renewal script should include proper ACME commands
    if [ -f "$TEST_TEMP_DIR/generated/certificates/renew-certs.sh" ]; then
        grep -q "acme.sh --renew" "$TEST_TEMP_DIR/generated/certificates/renew-certs.sh"
    fi
}

@test "certificate status should be checkable without docker" {
    # This test should fail initially (RED phase)
    run generate_all_to_generated_dir

    # Should generate status checker that works without containers
    [ -f "$TEST_TEMP_DIR/generated/certificates/cert-status.sh" ]

    # Status script should check file existence and expiry
    if [ -f "$TEST_TEMP_DIR/generated/certificates/cert-status.sh" ]; then
        grep -q "openssl x509" "$TEST_TEMP_DIR/generated/certificates/cert-status.sh"
        grep -q "expiry" "$TEST_TEMP_DIR/generated/certificates/cert-status.sh" ||
        grep -q "expires" "$TEST_TEMP_DIR/generated/certificates/cert-status.sh"
    fi
}
