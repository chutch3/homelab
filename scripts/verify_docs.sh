#!/bin/bash
set -euo pipefail

# Documentation Verification Script
# This script verifies that documentation matches the actual implementation

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-}")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track errors
ERRORS=0
WARNINGS=0

log_error() {
    echo -e "${RED}✗ ERROR: $1${NC}"
    ((ERRORS++))
}

log_warning() {
    echo -e "${YELLOW}⚠ WARNING: $1${NC}"
    ((WARNINGS++))
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}



echo "================================================================"
echo "Documentation Verification"
echo "================================================================"
echo

# ================================================================
# 1. Verify CLI Commands Match Documentation
# ================================================================
echo "Checking CLI Commands..."
echo "----------------------------------------"

# Check main CLI help
if ! "$PROJECT_ROOT/scripts/cli.sh" --help &>/dev/null; then
    log_error "scripts/cli.sh --help failed"
else
    log_success "scripts/cli.sh is executable"
fi

# Check Docker Swarm CLI
if ! "$PROJECT_ROOT/scripts/docker_swarm/cli.sh" --help &>/dev/null; then
    log_error "scripts/docker_swarm/cli.sh --help failed"
else
    log_success "scripts/docker_swarm/cli.sh is executable"
fi

# Verify documented commands exist
COMMANDS=("deploy" "cluster" "teardown")
for cmd in "${COMMANDS[@]}"; do
    if "$PROJECT_ROOT/scripts/cli.sh" --help 2>&1 | grep -q "$cmd"; then
        log_success "Command '$cmd' exists in CLI"
    else
        log_error "Command '$cmd' documented but not in CLI --help"
    fi
done

# Verify cluster subcommands
CLUSTER_SUBCMDS=("init" "status" "join")
for subcmd in "${CLUSTER_SUBCMDS[@]}"; do
    if "$PROJECT_ROOT/scripts/docker_swarm/cli.sh" cluster 2>&1 | grep -q "$subcmd"; then
        log_success "Cluster subcommand '$subcmd' exists"
    else
        log_warning "Cluster subcommand '$subcmd' documented but not in help"
    fi
done

echo

# ================================================================
# 2. Verify Script Paths in Documentation
# ================================================================
echo "Checking Script Paths..."
echo "----------------------------------------"

# Check if documented scripts exist
SCRIPTS=(
    "scripts/cli.sh"
    "scripts/common/ssh.sh"
    "scripts/common/machine.sh"
    "scripts/common/dns.sh"
    "scripts/docker_swarm/cli.sh"
    "scripts/docker_swarm/cluster.sh"
    "scripts/docker_swarm/deploy.sh"
    "scripts/docker_swarm/teardown.sh"
    "scripts/docker_swarm/wrappers/docker.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [[ -f "$PROJECT_ROOT/$script" ]]; then
        log_success "$script exists"
    else
        log_error "$script documented but not found"
    fi
done

echo

# ================================================================
# 3. Verify Example Configuration Files
# ================================================================
echo "Checking Configuration Files..."
echo "----------------------------------------"

CONFIG_FILES=(
    ".env.example"
    "machines.yaml.example"
)

for config in "${CONFIG_FILES[@]}"; do
    if [[ -f "$PROJECT_ROOT/$config" ]]; then
        log_success "$config exists"
    else
        log_warning "$config referenced in docs but not found"
    fi
done

# Check required .env variables mentioned in docs
if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
    REQUIRED_VARS=("BASE_DOMAIN" "CF_Token" "ACME_EMAIL")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" "$PROJECT_ROOT/.env.example" || grep -q "^#${var}=" "$PROJECT_ROOT/.env.example"; then
            log_success "Variable $var in .env.example"
        else
            log_warning "Variable $var documented but not in .env.example"
        fi
    done
fi

echo

# ================================================================
# 4. Verify Directory Structure
# ================================================================
echo "Checking Directory Structure..."
echo "----------------------------------------"

DIRECTORIES=(
    "scripts/common"
    "scripts/docker_swarm"
    "scripts/docker_swarm/wrappers"
    "stacks/apps"
    "stacks/reverse-proxy"
    "stacks/monitoring"
    "stacks/dns"
    "tests/unit/scripts/common"
    "tests/unit/scripts/docker_swarm"
)

for dir in "${DIRECTORIES[@]}"; do
    if [[ -d "$PROJECT_ROOT/$dir" ]]; then
        log_success "$dir/ exists"
    else
        log_error "$dir/ documented but not found"
    fi
done

echo

# ================================================================
# 5. Verify Stacks Match Documentation
# ================================================================
echo "Checking Service Stacks..."
echo "----------------------------------------"

# Services mentioned in documentation
DOCUMENTED_SERVICES=(
    "actual_server"
    "cryptpad"
    "deluge"
    "emby"
    "homeassistant"
    "homepage"
    "librechat"
    "photoprism"
    "prowlarr"
    "qbittorrent"
    "radarr"
    "sonarr"
)

for service in "${DOCUMENTED_SERVICES[@]}"; do
    if [[ -d "$PROJECT_ROOT/stacks/apps/$service" ]]; then
        if [[ -f "$PROJECT_ROOT/stacks/apps/$service/docker-compose.yml" ]]; then
            log_success "Service $service has docker-compose.yml"
        else
            log_warning "Service $service directory exists but no docker-compose.yml"
        fi
    else
        log_warning "Service $service documented but directory not found"
    fi
done

echo

# ================================================================
# 6. Verify Prerequisites Documentation Accuracy
# ================================================================
echo "Checking Prerequisites Documentation..."
echo "----------------------------------------"

# Check if prerequisites doc mentions correct ports
PREREQ_DOC="$PROJECT_ROOT/docs/getting-started/prerequisites.md"
if [[ -f "$PREREQ_DOC" ]]; then
    # Check for Docker Swarm ports
    SWARM_PORTS=("2377" "7946" "4789")
    for port in "${SWARM_PORTS[@]}"; do
        if grep -q "$port" "$PREREQ_DOC"; then
            log_success "Port $port documented in prerequisites"
        else
            log_warning "Port $port not mentioned in prerequisites"
        fi
    done

    # Check for key software mentions
    SOFTWARE=("Docker" "Cloudflare" "OpenMediaVault" "cifs-utils")
    for sw in "${SOFTWARE[@]}"; do
        if grep -qi "$sw" "$PREREQ_DOC"; then
            log_success "$sw mentioned in prerequisites"
        else
            log_warning "$sw not mentioned in prerequisites"
        fi
    done
else
    log_error "Prerequisites documentation not found"
fi

echo

# ================================================================
# Summary
# ================================================================
echo "================================================================"
echo "Verification Summary"
echo "================================================================"
echo -e "${GREEN}Passed: $(($(find "$PROJECT_ROOT/scripts" -name "*.sh" | wc -l) - ERRORS))${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Errors: $ERRORS${NC}"
echo

if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}✓ Documentation verification passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Documentation verification failed with $ERRORS errors${NC}"
    exit 1
fi
