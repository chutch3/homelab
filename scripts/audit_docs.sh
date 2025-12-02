#!/bin/bash
set -euo pipefail

# Documentation Audit Script
# Finds outdated commands and references in documentation

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-}")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
DOCS_DIR="$PROJECT_ROOT/docs"

RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "================================================================"
echo "Documentation Audit - Finding Outdated References"
echo "================================================================"
echo

# OLD SCRIPT NAMES (no longer exist)
echo -e "${BLUE}Checking for OLD script names (should not exist)...${NC}"
echo "----------------------------------------------------------------"

OLD_SCRIPTS=(
    "scripts/nuke.sh"
    "scripts/swarm_cluster_manager.sh"
    "scripts/configure_dns_records.sh"
    "scripts/machines.sh"
    "scripts/deploy.sh"
    "scripts/deploy.simple.sh"
)

for script in "${OLD_SCRIPTS[@]}"; do
    echo "Searching for: $script"
    if grep -r "$script" "$DOCS_DIR" --include="*.md" 2>/dev/null | grep -v "^Binary"; then
        echo -e "${RED}  ✗ Found references to OLD script${NC}"
    else
        echo -e "  ✓ No references found"
    fi
    echo
done

# CORRECT SCRIPT NAMES (should be used)
echo -e "${BLUE}Checking for CORRECT script paths...${NC}"
echo "----------------------------------------------------------------"

CORRECT_SCRIPTS=(
    "scripts/cli.sh"
    "scripts/common/ssh.sh"
    "scripts/common/machine.sh"
    "scripts/common/dns.sh"
    "scripts/docker_swarm/cli.sh"
    "scripts/docker_swarm/cluster.sh"
    "scripts/docker_swarm/deploy.sh"
    "scripts/docker_swarm/teardown.sh"
)

for script in "${CORRECT_SCRIPTS[@]}"; do
    echo "Checking usage of: $script"
    count=$(grep -c -r "$script" "$DOCS_DIR" --include="*.md" 2>/dev/null || echo "0")
    if [[ $count -eq 0 ]]; then
        echo -e "${YELLOW}  ⚠ Not documented (may need to add examples)${NC}"
    else
        echo -e "  ✓ Found $count references"
    fi
done
echo

# OLD COMMANDS (deprecated)
echo -e "${BLUE}Checking for OLD/deprecated commands...${NC}"
echo "----------------------------------------------------------------"

OLD_COMMANDS=(
    "docker stack deploy -c"
    "docker service update"
    "docker service logs"
    "./selfhosted.sh redeploy-service"
    "./selfhosted.sh nuke"
)

for cmd in "${OLD_COMMANDS[@]}"; do
    echo "Searching for: $cmd"
    if grep -r "$cmd" "$DOCS_DIR" --include="*.md" 2>/dev/null | grep -v "^Binary"; then
        echo -e "${YELLOW}  ⚠ Found old command (verify if still valid)${NC}"
    else
        echo -e "  ✓ Not found"
    fi
    echo
done

# CORRECT COMMANDS (should be used)
echo -e "${BLUE}Verifying CORRECT command usage...${NC}"
echo "----------------------------------------------------------------"

CORRECT_COMMANDS=(
    "./selfhosted.sh deploy"
    "./selfhosted.sh cluster init"
    "./selfhosted.sh cluster status"
    "./selfhosted.sh cluster join"
    "./selfhosted.sh teardown"
    "./scripts/cli.sh"
)

for cmd in "${CORRECT_COMMANDS[@]}"; do
    echo "Checking: $cmd"
    count=$(grep -c -r "$cmd" "$DOCS_DIR" --include="*.md" 2>/dev/null || echo "0")
    if [[ $count -eq 0 ]]; then
        echo -e "${YELLOW}  ⚠ Not documented${NC}"
    else
        echo -e "  ✓ Found $count references"
    fi
done
echo

# Check for homelab.yaml references (doesn't exist anymore)
echo -e "${BLUE}Checking for homelab.yaml references (file doesn't exist)...${NC}"
echo "----------------------------------------------------------------"
if grep -r "homelab\.yaml" "$DOCS_DIR" --include="*.md" 2>/dev/null | grep -v "^Binary"; then
    echo -e "${RED}  ✗ Found references to non-existent homelab.yaml${NC}"
else
    echo -e "  ✓ No references found"
fi
echo

# Check for correct configuration files
echo -e "${BLUE}Checking configuration file references...${NC}"
echo "----------------------------------------------------------------"

echo "Checking: machines.yaml"
count=$(grep -c -r "machines\.yaml" "$DOCS_DIR" --include="*.md" 2>/dev/null || echo "0")
echo -e "  ✓ Found $count references"

echo "Checking: .env"
count=$(grep -c -r "\.env" "$DOCS_DIR" --include="*.md" 2>/dev/null || echo "0")
echo -e "  ✓ Found $count references"
echo

# List all documentation files for manual review
echo -e "${BLUE}All documentation files to review:${NC}"
echo "----------------------------------------------------------------"
find "$DOCS_DIR" -name "*.md" -type f | sort

echo
echo "================================================================"
echo "Audit complete. Review output above for issues."
echo "================================================================"
