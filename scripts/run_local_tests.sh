#!/bin/bash

# Local Test Runner
# Part of Issue #40 - Comprehensive Test Suite for Unified Configuration
# Runs tests that require Docker and real infrastructure (NOT run in CI/CD)

set -euo pipefail

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for local tests..."

    local missing_tools=()

    # Check for Docker
    if ! command -v docker >/dev/null 2>&1; then
        missing_tools+=("docker")
    elif ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon not accessible"
        return 1
    fi

    # Check for BATS
    if ! command -v bats >/dev/null 2>&1; then
        missing_tools+=("bats")
    fi

    # Check for other required tools
    for tool in yq jq bc curl; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Install with: sudo apt-get install ${missing_tools[*]}"
        return 1
    fi

    log_success "All prerequisites available"
    return 0
}

# Clean up any existing test containers
cleanup_test_containers() {
    log_info "Cleaning up any existing test containers..."

    # Find and stop test containers
    local test_containers
    test_containers=$(docker ps -a --filter "name=homelab_test" --format "{{.Names}}" 2>/dev/null || echo "")

    if [ -n "$test_containers" ]; then
        echo "$test_containers" | while IFS= read -r container; do
            if [ -n "$container" ]; then
                log_info "Stopping container: $container"
                docker stop "$container" >/dev/null 2>&1 || true
                docker rm "$container" >/dev/null 2>&1 || true
            fi
        done
    fi

    # Clean up test networks
    local test_networks
    test_networks=$(docker network ls --filter "name=homelab_test" --format "{{.Name}}" 2>/dev/null || echo "")

    if [ -n "$test_networks" ]; then
        echo "$test_networks" | while IFS= read -r network; do
            if [ -n "$network" ]; then
                log_info "Removing network: $network"
                docker network rm "$network" >/dev/null 2>&1 || true
            fi
        done
    fi

    # Clean up test volumes
    local test_volumes
    test_volumes=$(docker volume ls --filter "name=homelab_test" --format "{{.Name}}" 2>/dev/null || echo "")

    if [ -n "$test_volumes" ]; then
        echo "$test_volumes" | while IFS= read -r volume; do
            if [ -n "$volume" ]; then
                log_info "Removing volume: $volume"
                docker volume rm "$volume" >/dev/null 2>&1 || true
            fi
        done
    fi

    log_success "Cleanup completed"
}

# Run real deployment tests
run_deployment_tests() {
    log_info "Running real deployment tests..."

    local test_file="$PROJECT_ROOT/tests/local/real_deployment_test.bats"

    if [ ! -f "$test_file" ]; then
        log_error "Deployment test file not found: $test_file"
        return 1
    fi

    # Run tests with verbose output
    if bats --tap "$test_file"; then
        log_success "Real deployment tests passed"
        return 0
    else
        log_error "Real deployment tests failed"
        return 1
    fi
}

# Run multi-machine tests (if configured)
run_multi_machine_tests() {
    local test_machines_file="$PROJECT_ROOT/test_machines.env"

    if [ ! -f "$test_machines_file" ]; then
        log_warning "No test_machines.env found - skipping multi-machine tests"
        log_info "To enable multi-machine tests, create test_machines.env with:"
        log_info "  TEST_DRIVER_HOST=192.168.1.10"
        log_info "  TEST_DRIVER_USER=admin"
        log_info "  TEST_NODE_01_HOST=192.168.1.11"
        log_info "  TEST_NODE_01_USER=admin"
        return 0
    fi

    log_info "Loading multi-machine test configuration..."
    # shellcheck source=/dev/null
    source "$test_machines_file"

    # Validate configuration
    if [ -z "${TEST_DRIVER_HOST:-}" ] || [ -z "${TEST_DRIVER_USER:-}" ]; then
        log_error "Invalid test_machines.env - missing TEST_DRIVER_HOST or TEST_DRIVER_USER"
        return 1
    fi

    # Test connectivity to machines
    log_info "Testing SSH connectivity to test machines..."

    if ssh -o ConnectTimeout=5 -o BatchMode=yes "${TEST_DRIVER_USER}@${TEST_DRIVER_HOST}" "echo 'Connection test successful'" >/dev/null 2>&1; then
        log_success "SSH connection to driver machine successful"
    else
        log_warning "Cannot connect to driver machine - skipping multi-machine tests"
        log_info "Ensure SSH key authentication is set up for test machines"
        return 0
    fi

    # Run multi-machine tests
    local multi_machine_test="$PROJECT_ROOT/tests/local/multi_machine_test.bats"

    if [ -f "$multi_machine_test" ]; then
        log_info "Running multi-machine tests..."

        if bats --tap "$multi_machine_test"; then
            log_success "Multi-machine tests passed"
        else
            log_error "Multi-machine tests failed"
            return 1
        fi
    else
        log_warning "Multi-machine test file not found: $multi_machine_test"
    fi
}

# Generate test report
generate_test_report() {
    local report_file="$PROJECT_ROOT/local_test_report.txt"

    log_info "Generating local test report..."

    cat > "$report_file" << EOF
Local Test Report
================

Generated: $(date)
Host: $(hostname)
Docker Version: $(docker --version)
User: $(whoami)

Test Environment:
- Project Root: $PROJECT_ROOT
- Docker Status: $(docker info --format '{{.ServerVersion}}' 2>/dev/null || echo "Not available")
- Available Memory: $(free -h | grep Mem | awk '{print $2}' 2>/dev/null || echo "Unknown")
- Available Disk: $(df -h "$PROJECT_ROOT" | tail -1 | awk '{print $4}' 2>/dev/null || echo "Unknown")

Test Results:
- Real deployment tests: $([ -f "$PROJECT_ROOT/tests/local/real_deployment_test.bats" ] && echo "Available" || echo "Not found")
- Multi-machine tests: $([ -f "$PROJECT_ROOT/test_machines.env" ] && echo "Configured" || echo "Not configured")

Notes:
- These tests require Docker and real infrastructure
- They are NOT run in CI/CD pipelines
- Results may vary based on local environment

EOF

    log_success "Test report saved to: $report_file"
}

# Display help
show_help() {
    cat << EOF
Local Test Runner for Homelab Comprehensive Test Suite

This script runs tests that require Docker and real infrastructure.
These tests are NOT run in CI/CD pipelines.

Usage: $0 [OPTIONS]

Options:
  -h, --help              Show this help message
  -c, --cleanup-only      Only perform cleanup, don't run tests
  -s, --skip-cleanup      Skip initial cleanup
  -d, --deployment-only   Only run deployment tests
  -m, --multi-machine     Only run multi-machine tests (requires test_machines.env)
  -r, --report-only       Only generate test report
  -v, --verbose           Enable verbose output

Prerequisites:
  - Docker (running and accessible)
  - BATS (Bash Automated Testing System)
  - yq, jq, bc, curl

Multi-machine testing:
  Create test_machines.env with:
    TEST_DRIVER_HOST=192.168.1.10
    TEST_DRIVER_USER=admin
    TEST_NODE_01_HOST=192.168.1.11
    TEST_NODE_01_USER=admin

Examples:
  $0                      # Run all local tests
  $0 --deployment-only    # Run only deployment tests
  $0 --cleanup-only       # Only cleanup test resources
  $0 --help               # Show this help

EOF
}

# Main function
main() {
    local cleanup_only=false
    local skip_cleanup=false
    local deployment_only=false
    local multi_machine_only=false
    local report_only=false
    local verbose=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--cleanup-only)
                cleanup_only=true
                shift
                ;;
            -s|--skip-cleanup)
                skip_cleanup=true
                shift
                ;;
            -d|--deployment-only)
                deployment_only=true
                shift
                ;;
            -m|--multi-machine)
                multi_machine_only=true
                shift
                ;;
            -r|--report-only)
                report_only=true
                shift
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Change to project root
    cd "$PROJECT_ROOT"

    echo ""
    log_info "🧪 Local Test Runner for Homelab Comprehensive Test Suite"
    log_warning "These tests require Docker and are NOT run in CI/CD"
    echo ""

    # Generate report only
    if [ "$report_only" = true ]; then
        generate_test_report
        exit 0
    fi

    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi

    # Cleanup only
    if [ "$cleanup_only" = true ]; then
        cleanup_test_containers
        exit 0
    fi

    # Initial cleanup (unless skipped)
    if [ "$skip_cleanup" = false ]; then
        cleanup_test_containers
    fi

    local test_results=()

    # Run deployment tests
    if [ "$multi_machine_only" = false ]; then
        if run_deployment_tests; then
            test_results+=("Deployment tests: PASSED")
        else
            test_results+=("Deployment tests: FAILED")
        fi
    fi

    # Run multi-machine tests
    if [ "$deployment_only" = false ]; then
        if run_multi_machine_tests; then
            test_results+=("Multi-machine tests: PASSED")
        else
            test_results+=("Multi-machine tests: FAILED")
        fi
    fi

    # Final cleanup
    cleanup_test_containers

    # Generate report
    generate_test_report

    # Summary
    echo ""
    log_info "📊 Local Test Summary:"
    for result in "${test_results[@]}"; do
        if [[ "$result" == *"PASSED"* ]]; then
            log_success "$result"
        else
            log_error "$result"
        fi
    done

    # Check if any tests failed
    local failed_tests=0
    for result in "${test_results[@]}"; do
        if [[ "$result" == *"FAILED"* ]]; then
            failed_tests=$((failed_tests + 1))
        fi
    done

    echo ""
    if [ $failed_tests -eq 0 ]; then
        log_success "All local tests completed successfully! 🎉"
        exit 0
    else
        log_error "$failed_tests test suite(s) failed"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
