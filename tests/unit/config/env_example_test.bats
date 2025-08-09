#!/usr/bin/env bats

setup() {
    # Load test helper functions
    load ../scripts/test_helper

    # Create temporary test directory
    TEST_TEMP_DIR="$(temp_make)"

    # Set up test environment variables
    export TEST=true

    # Change to test directory
    cd "$TEST_TEMP_DIR" || return
}

teardown() {
    # Clean up test directory
    temp_del "$TEST_TEMP_DIR"
}

@test "env_example_should_exist" {
    # Test that .env.example file exists
    [ -f "${BATS_TEST_DIRNAME}/../../../.env.example" ]
}

@test "env_example_should_contain_base_domain" {
    # Test that BASE_DOMAIN is documented
    run grep "BASE_DOMAIN" "${BATS_TEST_DIRNAME}/../../../.env.example"
    [ "$status" -eq 0 ]
}

@test "env_example_should_contain_wildcard_domain" {
    # Test that WILDCARD_DOMAIN is documented
    run grep "WILDCARD_DOMAIN" "${BATS_TEST_DIRNAME}/../../../.env.example"
    [ "$status" -eq 0 ]
}

@test "env_example_should_contain_cloudflare_variables" {
    # Test that Cloudflare DNS variables are documented
    run grep -E "(CF_Email|CF_Key|CF_Token)" "${BATS_TEST_DIRNAME}/../../../.env.example"
    [ "$status" -eq 0 ]
}

@test "env_example_should_have_documentation_comments" {
    # Test that variables are documented with comments
    run grep -E "^#.*" "${BATS_TEST_DIRNAME}/../../../.env.example"
    [ "$status" -eq 0 ]
}

@test "env_example_should_not_contain_real_credentials" {
    # Test that no real credentials are in the example
    run grep -E "(password|secret|token|key)=.{8,}" "${BATS_TEST_DIRNAME}/../../../.env.example"
    [ "$status" -ne 0 ]  # Should not find real credentials
}

@test "env_example_should_contain_uid_gid_variables" {
    # Test that UID/GID variables are documented for Docker permissions
    run grep -E "(UID|GID)" "${BATS_TEST_DIRNAME}/../../../.env.example"
    [ "$status" -eq 0 ]
}
