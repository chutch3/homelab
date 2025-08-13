#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load test_helper

    # Create temporary directories for testing
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true
    export BASE_DOMAIN="test.local"
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export HOMELAB_CONFIG="${TEST_TEMP_DIR}/homelab.yaml"
    export GENERATED_NGINX_DIR="${TEST_TEMP_DIR}/generated-nginx"

    # Create config directory
    mkdir -p "${TEST_TEMP_DIR}/config"
    mkdir -p "${TEST_TEMP_DIR}/config/services/reverseproxy/templates/conf.d"

    # Create test services.yaml with different nginx configuration types
    cat > "${HOMELAB_CONFIG}" <<EOF
version: "1.0"

categories:
  core: "Core Infrastructure"
  collaboration: "Collaboration & Productivity"

defaults:
  domain_pattern: "\${service}.\${BASE_DOMAIN}"

services:
  # Simple service - should use default template
  homepage:
    name: "Homepage"
    category: core
    domain: "dashboard"
    port: 3000
    nginx:
      upstream: "homepage:3000"

  # Service with inline nginx config override (with env var replacement)
  actual:
    name: "Actual Budget"
    category: core
    domain: "budget"
    port: 5006
    nginx:
      upstream: "actual:5006"
      additional_config: |
        location / {
            proxy_pass http://actual:5006;
            proxy_set_header Cross-Origin-Embedder-Policy require-corp;
            proxy_set_header Cross-Origin-Opener-Policy same-origin;
            proxy_set_header X-Custom-Domain \${DOMAIN_ACTUAL};
        }

  # Complex service - should reference external template file
  cryptpad:
    name: "CryptPad"
    category: collaboration
    domain: "docs"
    domain_sandbox: "sandbox-docs"
    port: 3000
    nginx:
      template_file: "cryptpad.template"
      domains:
        - "\${DOMAIN_CRYPTPAD}"
        - "\${DOMAIN_CRYPTPAD_SANDBOX}"
EOF

    # Create a complex template file for cryptpad
    cat > "${TEST_TEMP_DIR}/config/services/reverseproxy/templates/conf.d/cryptpad.template" <<EOF
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name \${DOMAIN_CRYPTPAD} \${DOMAIN_CRYPTPAD_SANDBOX};

    set \$main_domain \${DOMAIN_CRYPTPAD};
    set \$sandbox_domain \${DOMAIN_CRYPTPAD_SANDBOX};

    add_header Cross-Origin-Resource-Policy cross-origin;
    add_header Cross-Origin-Embedder-Policy require-corp;

    location / {
        proxy_pass http://cryptpad:3000;
    }
}
EOF
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"

    # Unset test environment variables
    unset TEST BASE_DOMAIN PROJECT_ROOT HOMELAB_CONFIG GENERATED_NGINX_DIR
}

@test "simple service should use default nginx template" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run nginx generation
    run generate_nginx_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create nginx file for homepage
    [ -f "${GENERATED_NGINX_DIR}/homepage.template" ]

    # Should contain default SSL and proxy setup
    run grep "listen 443 ssl" "${GENERATED_NGINX_DIR}/homepage.template"
    [ "$status" -eq 0 ]

    run grep "include /etc/nginx/conf.d/includes/ssl" "${GENERATED_NGINX_DIR}/homepage.template"
    [ "$status" -eq 0 ]

    run grep "proxy_pass http://homepage:3000" "${GENERATED_NGINX_DIR}/homepage.template"
    [ "$status" -eq 0 ]
}

@test "service with additional_config should include custom directives and env vars" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run nginx generation
    run generate_nginx_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should create nginx file for actual
    [ -f "${GENERATED_NGINX_DIR}/actual.template" ]

    # Should contain the custom headers from additional_config
    run grep "Cross-Origin-Embedder-Policy require-corp" "${GENERATED_NGINX_DIR}/actual.template"
    [ "$status" -eq 0 ]

    run grep "Cross-Origin-Opener-Policy same-origin" "${GENERATED_NGINX_DIR}/actual.template"
    [ "$status" -eq 0 ]

    # Should contain env var replacement in additional_config
    run grep "X-Custom-Domain \\\${DOMAIN_ACTUAL}" "${GENERATED_NGINX_DIR}/actual.template"
    [ "$status" -eq 0 ]
}

@test "service with template_file should reference external template" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run nginx generation
    run generate_nginx_from_services

    # Check exit status
    [ "$status" -eq 0 ]

    # Should NOT create a generated template for cryptpad (it uses external template)
    [ ! -f "${GENERATED_NGINX_DIR}/cryptpad.template" ]

    # External template should exist and be used by the system
    [ -f "${TEST_TEMP_DIR}/config/services/reverseproxy/templates/conf.d/cryptpad.template" ]
}

@test "default template should include HTTP to HTTPS redirect" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run nginx generation
    run generate_nginx_from_services

    # Check default template includes HTTP redirect
    [ -f "${GENERATED_NGINX_DIR}/homepage.template" ]

    run grep "listen 80" "${GENERATED_NGINX_DIR}/homepage.template"
    [ "$status" -eq 0 ]

    run grep "return 301 https" "${GENERATED_NGINX_DIR}/homepage.template"
    [ "$status" -eq 0 ]
}

@test "generated templates should use correct domain variables" {
    # Source the service generator script
    # shellcheck source=/dev/null
    source "${BATS_TEST_DIRNAME}/../../../scripts/service_generator.sh"

    # Run nginx generation
    run generate_nginx_from_services

    # Check that homepage uses DOMAIN_HOMEPAGE variable
    [ -f "${GENERATED_NGINX_DIR}/homepage.template" ]
    run grep "\${DOMAIN_HOMEPAGE}" "${GENERATED_NGINX_DIR}/homepage.template"
    [ "$status" -eq 0 ]

    # Check that actual uses DOMAIN_ACTUAL variable
    [ -f "${GENERATED_NGINX_DIR}/actual.template" ]
    run grep "\${DOMAIN_ACTUAL}" "${GENERATED_NGINX_DIR}/actual.template"
    [ "$status" -eq 0 ]
}
