#!/usr/bin/env bats

load test_helper

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
    source "${BATS_TEST_DIRNAME}/../../../scripts/configure_dns_records.sh"
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
    # Mock curl and set DNS token
    curl() { mock_curl "$@"; }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run add_a_record "manager" "192.168.1.100"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Added A record: manager.diyhub.dev -> 192.168.1.100"* ]]
}

@test "add_a_record should skip creation if record already exists" {
    # Mock curl to simulate existing record
    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            echo '{"status":"ok","response":{"records":[{"name":"manager","type":"A"}]}}'
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
    # Mock curl and set DNS token
    curl() { mock_curl "$@"; }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run add_cname_record "actual" "manager.diyhub.dev"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Added CNAME record: actual.diyhub.dev -> manager.diyhub.dev"* ]]
}

@test "add_cname_record should skip creation if record already exists" {
    # Mock curl to simulate existing record
    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            echo '{"status":"ok","response":{"records":[{"name":"actual","type":"CNAME"}]}}'
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

@test "register_service_cnames should add CNAME records for all services" {
    # Mock curl and DNS functions
    curl() { mock_curl "$@"; }
    export -f curl mock_curl
    export DNS_TOKEN="mock-token-12345"

    run register_service_cnames
    [ "$status" -eq 0 ]
    [[ "$output" == *"dns"* ]]
    [[ "$output" == *"actual"* ]]
    [[ "$output" == *"homeassistant"* ]]
}

@test "check_record_exists should return 0 when record exists" {
    # Mock curl to simulate existing record
    curl() {
        if [[ "$*" == *"zones/records/get"* ]]; then
            echo '{"status":"ok","response":{"records":[{"name":"manager","type":"A"}]}}'
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
