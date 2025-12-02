#!/usr/bin/env bats

load ../test_helper

setup() {
    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"
    export TEST=true
    export PROJECT_ROOT="${TEST_TEMP_DIR}"
    export BASE_DOMAIN="diyhub.dev"
    export DNS_ADMIN_PASSWORD="test123"
    export DNS_SERVER_IP="192.168.1.100"
    export DNS_SERVER_URL="http://localhost:5380" # Add this for consistency

    # Create test machines.yaml with simplified structure
    cat > "${TEST_TEMP_DIR}/machines.yaml" <<EOF
machines:
  manager:
    ip: 192.168.1.100
    user: admin
  node-01:
    ip: 192.168.1.101
    user: deploy
  nas:
    ip: 192.168.1.50
    user: admin
EOF

    export MACHINES_FILE="${TEST_TEMP_DIR}/machines.yaml"

    # Source the DNS configuration script
    source "${BATS_TEST_DIRNAME}/../../../../scripts/common/dns.sh"
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

# Mock curl for testing API calls
mock_curl() {
    # Parse the API endpoint from the URL
    local url=""
    local data=""
    for arg in "$@"; do
        if [[ "$arg" == *"/api/"* ]]; then
            url="$arg"
        elif [[ "$arg" == -d ]]; then
            data_next=true
        elif [ "${data_next:-}" = true ]; then
            data="$arg"
            data_next=false
        fi
    done

    # Simulate successful API responses
    if [[ "$url" == *"/api/user/login"* ]]; then
        echo '{"token":"mock-token-12345"}'
    elif [[ "$url" == *"/api/zones/create"* ]]; then
        echo '{"status":"ok"}'
    elif [[ "$url" == *"/api/zones/records/add"* ]]; then
        echo '{"status":"ok"}'
    else
        echo '{"status":"error","message":"Unknown API endpoint"}'
        return 1
    fi

    return 0
}

@test "get_dns_token should authenticate with Technitium DNS API" {
    # Mock curl to simulate API response
    curl() { mock_curl "$@"; }
    export -f curl mock_curl

    run get_dns_token
    [ "$status" -eq 0 ]
    [ "$output" = "mock-token-12345" ]
}

@test "add_a_record should add A record via API" {
    # Mock curl to capture API parameters and verify correct format
    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            echo '{"status":"ok","response":{"records":[]}}'
        elif [[ "$*" == *"zones/records/add"* ]]; then
            # Write captured params to a file so we can access it outside the function
            echo "$*" > "${TEST_TEMP_DIR}/captured_params"
            mock_curl "$@"
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run add_a_record "manager" "192.168.1.100"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Added A record: manager.diyhub.dev -> 192.168.1.100"* ]]

    # Verify correct API parameters: should use domain=manager.diyhub.dev and zone=diyhub.dev
    local captured_params="$(cat "${TEST_TEMP_DIR}/captured_params")"
    [[ "$captured_params" == *"domain=manager.diyhub.dev"* ]]
    [[ "$captured_params" == *"zone=diyhub.dev"* ]]
}

@test "add_a_record should skip creation if record already exists" {
    # Mock curl to simulate existing record
    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            echo '{"status":"ok","response":{"records":[{"name":"manager.diyhub.dev","type":"A"}]}}'
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run add_a_record "manager" "192.168.1.100"
    [ "$status" -eq 0 ]
    [[ "$output" == *"A record already exists: manager.diyhub.dev"* ]]
}

@test "add_cname_record should add CNAME record via API" {
    # Mock curl to capture API parameters and verify correct format
    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            echo '{"status":"ok","response":{"records":[]}}'
        elif [[ "$*" == *"zones/records/add"* ]]; then
            # Write captured params to a file so we can access it outside the function
            echo "$*" > "${TEST_TEMP_DIR}/captured_params"
            mock_curl "$@"
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run add_cname_record "actual" "manager.diyhub.dev"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Added CNAME record: actual.diyhub.dev -> manager.diyhub.dev"* ]]

    # Verify correct API parameters: should use domain=actual.diyhub.dev and zone=diyhub.dev
    local captured_params="$(cat "${TEST_TEMP_DIR}/captured_params")"
    [[ "$captured_params" == *"domain=actual.diyhub.dev"* ]]
    [[ "$captured_params" == *"zone=diyhub.dev"* ]]
}

@test "add_cname_record should skip creation if record already exists" {
    # Mock curl to simulate check_record_exists failing to detect existing record,
    # but API correctly reports record already exists
    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            # Simulate check_record_exists failing to detect existing record
            echo '{"status":"ok","response":{"records":[]}}'
        elif [[ "$*" == *"zones/records/add"* ]]; then
            # API correctly reports record already exists
            echo '{"status":"error","errorMessage":"Cannot add record: record already exists."}'
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run add_cname_record "actual" "manager.diyhub.dev"
    [ "$status" -eq 0 ]
    [[ "$output" == *"CNAME record already exists: actual.diyhub.dev"* ]]
}

@test "register_machine_dns_records should add A records for all machines" {
    # Mock curl and DNS functions
    curl() { mock_curl "$@"; }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run register_machine_dns_records
    [ "$status" -eq 0 ]
    [[ "$output" == *"manager"* ]]
    [[ "$output" == *"node-01"* ]]
    [[ "$output" == *"nas"* ]]
}

@test "register_service_cnames should use discovered Traefik domains instead of hardcoded list" {
    # Override with realistic machines.yaml - MULTIPLE managers to test bug
    export BASE_DOMAIN="testlab.local"
    cat > "${TEST_TEMP_DIR}/machines.yaml" <<EOF
machines:
  desktop-main:
    ip: 192.168.1.100
    role: manager
  server-01:
    ip: 192.168.1.101
    role: manager
  server-02:
    ip: 192.168.1.102
    role: manager
  worker-node:
    ip: 192.168.1.103
    role: worker
EOF

    # Create mock stacks directory with docker-compose files containing Traefik labels
    local test_stacks_dir="${TEST_TEMP_DIR}/stacks"

    # Create apps with different domain names than directory names
    mkdir -p "${test_stacks_dir}/apps/actual_server"
    cat > "${test_stacks_dir}/apps/actual_server/docker-compose.yml" <<EOF
services:
  actual_server:
    deploy:
      labels:
        - "traefik.http.routers.actual.rule=Host(\`budget.\${BASE_DOMAIN}\`)"
        - "traefik.http.routers.actual.entrypoints=websecure"
EOF

    mkdir -p "${test_stacks_dir}/apps/homeassistant"
    cat > "${test_stacks_dir}/apps/homeassistant/docker-compose.yml" <<EOF
services:
  homeassistant:
    deploy:
      labels:
        - "traefik.http.routers.homeassistant.rule=Host(\`ha.\${BASE_DOMAIN}\`)"
        - "traefik.http.routers.homeassistant.entrypoints=websecure"
EOF

    # Create monitoring stack
    mkdir -p "${test_stacks_dir}/monitoring"
    cat > "${test_stacks_dir}/monitoring/docker-compose.yml" <<EOF
services:
  grafana:
    deploy:
      labels:
        - "traefik.http.routers.grafana.rule=Host(\`monitoring.\${BASE_DOMAIN}\`)"
        - "traefik.http.routers.grafana.entrypoints=websecure"
EOF

    # Create dns stack (should be excluded from CNAME creation)
    mkdir -p "${test_stacks_dir}/dns"
    cat > "${test_stacks_dir}/dns/docker-compose.yml" <<EOF
services:
  technitium:
    deploy:
      labels:
        - "traefik.http.routers.dns.rule=Host(\`dns.\${BASE_DOMAIN}\`)"
        - "traefik.http.routers.dns.entrypoints=websecure"
EOF

    export STACKS_DIR="${test_stacks_dir}"

    local cname_records=()
    # Mock curl to capture CNAME records being created
    curl() {
        if [[ "$*" == *"zones/records/add"* ]] && [[ "$*" == *"type=CNAME"* ]]; then
            # Extract domain name from API call
            local domain=$(echo "$*" | sed -n 's/.*domain=\([^&]*\).*/\1/p')
            cname_records+=("$domain")
            echo '{"status":"ok"}'
        elif [[ "$*" == *"zones/records/get"* ]]; then
            echo '{"status":"ok","records":[]}'
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    # Debug: Test if machines_parse works
    local test_parse=$(machines_parse "manager" 2>&1 || echo "PARSE_FAILED")
    echo "DEBUG: machines_parse output = $test_parse"

    run register_service_cnames
    echo "DEBUG: Output = $output"
    echo "DEBUG: Status = $status"
    [ "$status" -eq 0 ]

    # Should show CNAME records pointing to FIRST manager machine hostname only
    [[ "$output" == *"desktop-main.testlab.local"* ]]
    # Should NOT include other managers in the CNAME target
    [[ "$output" != *"server-01.testlab.local"* ]]
    [[ "$output" != *"server-02.testlab.local"* ]]
    [[ "$output" != *"manager.testlab.local"* ]]

    # Should create CNAME records for discovered Traefik domains, not directory names
    [[ "$output" == *"budget.testlab.local"* ]]      # From actual_server but domain is "budget"
    [[ "$output" == *"ha.testlab.local"* ]]          # From homeassistant but domain is "ha"
    [[ "$output" == *"monitoring.testlab.local"* ]]  # From monitoring stack

    # Should NOT attempt to create CNAME for dns service (conflicts with DNS server A record)
    [[ "$output" != *"dns.testlab.local"* ]]

    # Should NOT create records for old hardcoded service names that don't match Traefik domains
    [[ "$output" != *"actual.testlab.local"* ]]
    [[ "$output" != *"homeassistant.testlab.local"* ]]
}

@test "discover_traefik_domains should extract domains from all stack directories" {
    # Create test stack directories with various docker-compose files containing Traefik labels
    local test_stacks_dir="${TEST_TEMP_DIR}/stacks"

    # Create apps directory
    mkdir -p "${test_stacks_dir}/apps/budget_app"
    cat > "${test_stacks_dir}/apps/budget_app/docker-compose.yml" <<EOF
services:
  actual_server:
    deploy:
      labels:
        - "traefik.http.routers.actual.rule=Host(\`budget.\${BASE_DOMAIN}\`)"
        - "traefik.http.routers.actual.entrypoints=websecure"
EOF

    # Create monitoring directory
    mkdir -p "${test_stacks_dir}/monitoring"
    cat > "${test_stacks_dir}/monitoring/docker-compose.yml" <<EOF
services:
  grafana:
    deploy:
      labels:
        - "traefik.http.routers.grafana.rule=Host(\`monitoring.\${BASE_DOMAIN}\`)"
        - "traefik.http.routers.grafana.entrypoints=websecure"
EOF

    # Create reverse-proxy directory
    mkdir -p "${test_stacks_dir}/reverse-proxy"
    cat > "${test_stacks_dir}/reverse-proxy/docker-compose.yml" <<EOF
services:
  traefik:
    deploy:
      labels:
        - "traefik.http.routers.traefik.rule=Host(\`traefik.\${BASE_DOMAIN}\`)"
        - "traefik.http.routers.traefik.entrypoints=websecure"
EOF

    # Create dns directory
    mkdir -p "${test_stacks_dir}/dns"
    cat > "${test_stacks_dir}/dns/docker-compose.yml" <<EOF
services:
  technitium:
    deploy:
      labels:
        - "traefik.http.routers.dns.rule=Host(\`dns.\${BASE_DOMAIN}\`)"
        - "traefik.http.routers.dns.entrypoints=websecure"
EOF

    # Create file without Traefik labels (should be ignored)
    mkdir -p "${test_stacks_dir}/apps/no_traefik"
    cat > "${test_stacks_dir}/apps/no_traefik/docker-compose.yml" <<EOF
services:
  simple_app:
    image: nginx:alpine
    ports:
      - "80:80"
EOF

    export STACKS_DIR="${test_stacks_dir}"

    run discover_traefik_domains
    [ "$status" -eq 0 ]

    # Should discover domains from all stack directories
    [[ "$output" == *"budget"* ]]
    [[ "$output" == *"monitoring"* ]]
    [[ "$output" == *"traefik"* ]]
    [[ "$output" == *"dns"* ]]

    # Should not include services without Traefik labels
    [[ "$output" != *"simple_app"* ]]

    # Check exact output count (should be 4 domains)
    local domain_count=$(echo "$output" | wc -l)
    [ "$domain_count" -eq 4 ]
}

@test "discover_traefik_domains should handle complex Host rules with logical operators" {
    # Create test stack directories with complex Traefik rules
    local test_stacks_dir="${TEST_TEMP_DIR}/stacks"

    # Create cryptpad-like complex rule
    mkdir -p "${test_stacks_dir}/apps/cryptpad"
    cat > "${test_stacks_dir}/apps/cryptpad/docker-compose.yml" <<EOF
services:
  cryptpad:
    deploy:
      labels:
        - "traefik.http.routers.cryptpad-http.rule=(Host(\`cryptpad.\${BASE_DOMAIN}\`) || Host(\`cryptpad-sandbox.\${BASE_DOMAIN}\`)) && !PathPrefix(\`/cryptpad_websocket\`)"
        - "traefik.http.routers.cryptpad-websocket.rule=(Host(\`cryptpad.\${BASE_DOMAIN}\`) || Host(\`cryptpad-sandbox.\${BASE_DOMAIN}\`)) && PathPrefix(\`/cryptpad_websocket\`)"
EOF

    # Create rule with Host in the middle of complex expression
    mkdir -p "${test_stacks_dir}/apps/complex_app"
    cat > "${test_stacks_dir}/apps/complex_app/docker-compose.yml" <<EOF
services:
  app:
    deploy:
      labels:
        - "traefik.http.routers.app.rule=PathPrefix(\`/api\`) && Host(\`api.\${BASE_DOMAIN}\`) && Method(\`GET,POST\`)"
EOF

    export STACKS_DIR="${test_stacks_dir}"

    run discover_traefik_domains
    echo "Status: $status"
    echo "Output: $output"
    [ "$status" -eq 0 ]

    # Should discover domains from complex rules
    [[ "$output" == *"cryptpad"* ]]
    [[ "$output" == *"cryptpad-sandbox"* ]]
    [[ "$output" == *"api"* ]]

    # Check that we found all expected domains
    local domain_count=$(echo "$output" | wc -l)
    [ "$domain_count" -eq 3 ]
}

@test "check_record_exists should return 0 when record exists" {
    # Mock curl to simulate existing record
    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            echo '{"status":"ok","response":{"records":[{"name":"manager.diyhub.dev","type":"A"}]}}'
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run check_record_exists "manager"
    [ "$status" -eq 0 ]
}

@test "check_record_exists should return 1 when record does not exist" {
    # Mock curl to simulate no existing record
    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            echo '{"status":"ok","response":{"records":[]}}'
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run check_record_exists "nonexistent"
    [ "$status" -eq 1 ]
}

@test "add_a_record should handle when check_record_exists fails to detect existing record" {
    # Mock curl to simulate check_record_exists incorrectly returning false,
    # then API returns "record already exists" error
    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            # Simulate check_record_exists failing to detect existing record
            echo '{"status":"ok","response":{"records":[]}}'
        elif [[ "$*" == *"zones/records/add"* ]]; then
            # API correctly reports record already exists
            echo '{"status":"error","errorMessage":"Cannot add record: record already exists."}'
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run add_a_record "cody-X570-GAMING-X" "192.168.86.41"
    [ "$status" -eq 0 ]  # Should succeed gracefully, not fail
    [[ "$output" == *"A record already exists"* ]]  # Should detect and report existing record
}

@test "get_dns_token urlencodes passwords correctly" {
    export DNS_ADMIN_PASSWORD="foo#bar&baz=qux"
    local curl_log="${TEST_TEMP_DIR}/curl.log"

    # Mock curl to capture the data payload to a file
    curl() {
        printf "%s\n" "$@" > "$curl_log"
        echo '{"token":"mock-token-12345"}'
    }
    export -f curl

    run get_dns_token

    [ "$status" -eq 0 ]

    echo "---BEGIN curl.log---"
    cat "$curl_log"
    echo "---END curl.log---"

    # Read the arguments from the file
    local args=()
    while IFS= read -r line; do
        args+=("$line")
    done < "$curl_log"

    # Find the -d argument
    local data_payload=""
    for i in "${!args[@]}"; do
        if [[ "${args[$i]}" == "-d" ]]; then
            data_payload="${args[$i+1]}"
            break
        fi
    done

    echo "data_payload: $data_payload"

    [ "$data_payload" = "user=admin&pass=foo%23bar%26baz%3Dqux" ]
}

@test "register_dns_server_records should register multiple dns A records for all dns-labeled nodes" {
    # Create machines.yaml with multiple nodes labeled for DNS
    cat > "${TEST_TEMP_DIR}/machines.yaml" <<EOF
machines:
  manager-node:
    ip: 192.168.1.100
    role: manager
    labels:
      dns: true
  worker-node:
    ip: 192.168.1.101
    role: worker
    labels:
      dns: true
  other-node:
    ip: 192.168.1.102
    role: worker
EOF

    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            echo '{"status":"ok","response":{"records":[]}}'
        elif [[ "$*" == *"zones/records/add"* ]]; then
            echo "RECORD_ADD: $*"
            echo '{"status":"ok"}'
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run register_dns_server_records
    [ "$status" -eq 0 ]

    # Should register multiple A records for dns.diyhub.dev (one per dns-labeled node)
    [[ "$output" == *"dns.diyhub.dev"* ]]
    [[ "$output" == *"192.168.1.100"* ]]  # Manager node
    [[ "$output" == *"192.168.1.101"* ]]  # Worker node with dns label
    # Should NOT include node without dns label
    [[ "$output" != *"192.168.1.102"* ]]  # other-node has no dns label

    # Should indicate multiple IPs for redundancy
    [[ "$output" == *"multiple"* ]] || [[ "$output" == *"redundancy"* ]] || [[ "$output" == *"failover"* ]]

    # Should NOT register separate primary/secondary records
    [[ "$output" != *"dns-primary"* ]]
    [[ "$output" != *"dns-secondary"* ]]
}

@test "configure_primary_zone_transfer should enable zone transfer to secondary IP" {
    export DNS_PRIMARY_IP="192.168.1.100"
    export DNS_SECONDARY_IP="192.168.1.101"

    curl() {
        if [[ "$*" == *"zones/options/set"* ]]; then
            echo "$*" > "${TEST_TEMP_DIR}/captured_params"
            echo '{"status":"ok"}'
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run configure_primary_zone_transfer
    [ "$status" -eq 0 ]
    [[ "$output" == *"Zone transfer enabled"* ]]

    # Verify correct API parameters
    local captured_params="$(cat "${TEST_TEMP_DIR}/captured_params")"
    [[ "$captured_params" == *"zoneTransfer=UseSpecifiedNetworkACL"* ]]
    [[ "$captured_params" == *"zoneTransferNetworkACL=192.168.1.101"* ]]
}

@test "configure_secondary_zone should create secondary zone on secondary DNS server" {
    export DNS_PRIMARY_IP="192.168.1.100"
    export DNS_SECONDARY_IP="192.168.1.101"

    local secondary_api_calls=()
    curl() {
        local url=""
        for arg in "$@"; do
            if [[ "$arg" == *"/api/"* ]]; then
                url="$arg"
            fi
        done

        # Handle secondary server login
        if [[ "$url" == *"192.168.1.101"*"/api/user/login"* ]]; then
            echo '{"token":"secondary-token-12345"}'
        # Handle secondary zone creation
        elif [[ "$url" == *"192.168.1.101"*"/api/zones/create"* ]]; then
            secondary_api_calls+=("$*")
            echo '{"status":"ok"}'
        else
            mock_curl "$@"
        fi
    }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run configure_secondary_zone
    [ "$status" -eq 0 ]
    [[ "$output" == *"Secondary zone created"* ]]
}
