#!/bin/bash

# Analysis script comparing Docker Swarm native discovery vs machines.yml
# This script evaluates the trade-offs between approaches

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Docker Swarm vs machines.yml Comparison${NC}"
echo "=============================================="

# Find the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "\n${YELLOW}1. Docker Swarm Native Capabilities${NC}"
echo "------------------------------------"

echo "🔍 What Docker Swarm provides natively:"
echo "  • Node discovery: 'docker node ls'"
echo "  • Node inspection: 'docker node inspect <node>'"
echo "  • Node labeling: 'docker node update --label-add'"
echo "  • Automatic service placement based on constraints"
echo "  • Built-in load balancing and networking"
echo "  • Health monitoring and failover"

echo -e "\n🔧 Checking current Docker Swarm usage in codebase..."

# Check if Swarm is actually used
SWARM_USAGE=$(find scripts -name "*.sh" -exec grep -l "docker.*swarm\|docker.*node" {} \; 2>/dev/null || true)
if [ -n "$SWARM_USAGE" ]; then
    echo -e "${GREEN}✅ Docker Swarm commands found in:${NC}"
    echo "$SWARM_USAGE" | while read -r file; do
        echo "  • $file"
        # Show specific swarm commands used
        grep -n "docker.*\(swarm\|node\)" "$file" | head -3 | sed 's/^/    /'
    done
else
    echo -e "${RED}❌ No Docker Swarm usage found in scripts${NC}"
fi

echo -e "\n${YELLOW}2. machines.yml Specific Features${NC}"
echo "----------------------------------"

echo "🏗️ What machines.yml provides beyond Swarm:"

# Analyze machines.yml.example structure
if [ -f "machines.yml.example" ]; then
    echo -e "${GREEN}✅ Analyzing machines.yml.example structure:${NC}"

    # Check for SSH configuration
    if grep -q "user\|ssh" machines.yml.example; then
        echo "  • SSH user configuration (not in Swarm)"
        grep -n "user:" machines.yml.example | head -2 | sed 's/^/    /'
    fi

    # Check for IP addresses
    if grep -q "ip:" machines.yml.example; then
        echo "  • Explicit IP address management"
        grep -n "ip:" machines.yml.example | head -2 | sed 's/^/    /'
    fi

    # Check for custom labels
    if grep -q "labels:" machines.yml.example; then
        echo "  • Pre-deployment labeling system"
        grep -A 3 "labels:" machines.yml.example | head -5 | sed 's/^/    /'
    fi

    # Check for roles
    if grep -q "role:" machines.yml.example; then
        echo "  • Role-based organization"
        grep -n "role:" machines.yml.example | sed 's/^/    /'
    fi
else
    echo -e "${RED}❌ machines.yml.example not found${NC}"
fi

echo -e "\n${YELLOW}3. Feature Comparison Matrix${NC}"
echo "-----------------------------"

cat << 'EOF'
| Feature                    | Docker Swarm Native | machines.yml | Winner    |
|----------------------------|--------------------|--------------|-----------|
| Node Discovery             | ✅ Automatic       | ❌ Manual    | Swarm     |
| SSH Configuration          | ❌ Not handled     | ✅ Built-in  | machines  |
| IP Address Management      | ❌ Not explicit    | ✅ Explicit  | machines  |
| Service Placement          | ✅ Dynamic         | ❌ Static    | Swarm     |
| Health Monitoring          | ✅ Built-in        | ❌ Manual    | Swarm     |
| Pre-deployment Setup       | ❌ Not supported   | ✅ Yes       | machines  |
| Load Balancing             | ✅ Automatic       | ❌ Manual    | Swarm     |
| Network Management         | ✅ Overlay nets    | ❌ Manual    | Swarm     |
| Rolling Updates            | ✅ Built-in        | ❌ Manual    | Swarm     |
| Configuration Complexity   | 🟡 Medium          | 🟢 Simple    | machines  |
EOF

echo -e "\n${YELLOW}4. Use Case Analysis${NC}"
echo "--------------------"

echo -e "${PURPLE}Scenario A: Fresh Docker Swarm Cluster${NC}"
echo "• Nodes already in swarm: machines.yml may be redundant"
echo "• Swarm handles discovery, placement, networking automatically"
echo "• machines.yml adds SSH layer that may not be needed"

echo -e "\n${PURPLE}Scenario B: Pre-deployment Configuration${NC}"
echo "• Need to set up nodes before joining swarm"
echo "• SSH access configuration required"
echo "• machines.yml provides structured approach"

echo -e "\n${PURPLE}Scenario C: Hybrid Management${NC}"
echo "• Use machines.yml for initial setup/SSH"
echo "• Use Swarm native for runtime management"
echo "• Best of both worlds approach"

echo -e "\n${YELLOW}5. Current Project Context${NC}"
echo "---------------------------"

# Check how machines.yml is actually used in this project
echo "🔍 Analyzing actual usage patterns..."

if [ -f "scripts/machines.sh" ]; then
    echo -e "\n${GREEN}machines.sh usage analysis:${NC}"

    # Check if it's used for SSH setup
    if grep -q "ssh" scripts/machines.sh; then
        echo "  • SSH management: Used for remote connection setup"
    fi

    # Check if it's used for deployment
    if grep -q "deploy\|swarm" scripts/machines.sh; then
        echo "  • Deployment: Used in swarm deployment process"
    fi

    # Check what scripts call machines.sh functions
    echo -e "\n${GREEN}Scripts that depend on machines.sh:${NC}"
    find scripts -name "*.sh" -exec grep -l "machines_" {} \; 2>/dev/null | while read -r file; do
        echo "  • $file"
        grep -n "machines_" "$file" | head -2 | sed 's/^/    /'
    done
fi

echo -e "\n${BLUE}📊 Conclusion & Recommendation${NC}"
echo "==============================="

# Count dependencies
MACHINE_DEPS=$(find scripts -name "*.sh" -exec grep -l "machines_" {} \; 2>/dev/null | wc -l)
SSH_REFS=$(grep -r "ssh" scripts/ 2>/dev/null | wc -l)

echo "📈 Dependency Analysis:"
echo "  • Scripts depending on machines.sh: $MACHINE_DEPS"
echo "  • SSH references in scripts: $SSH_REFS"

if [ "$MACHINE_DEPS" -gt 1 ] && [ "$SSH_REFS" -gt 5 ]; then
    echo -e "\n${GREEN}✅ RECOMMENDATION: Keep machines.yml${NC}"
    echo "   Reasons:"
    echo "   • Active usage in deployment scripts"
    echo "   • SSH management is valuable for setup"
    echo "   • Complements Swarm rather than competing"
    echo "   • Pre-deployment configuration need"
elif [ "$MACHINE_DEPS" -le 1 ]; then
    echo -e "\n${YELLOW}⚠️  RECOMMENDATION: Consider simplification${NC}"
    echo "   Reasons:"
    echo "   • Low usage suggests limited value"
    echo "   • Docker Swarm native might suffice"
    echo "   • Reduced complexity beneficial"
else
    echo -e "\n${BLUE}🔍 RECOMMENDATION: Hybrid approach${NC}"
    echo "   Reasons:"
    echo "   • Use machines.yml for SSH/setup phase"
    echo "   • Use Swarm native for runtime management"
    echo "   • Clear separation of concerns"
fi

echo -e "\n${BLUE}🎯 Next Steps${NC}"
echo "==============="
echo "1. Document the hybrid model: machines.yml for setup, Swarm for runtime"
echo "2. Clarify when to use each approach in documentation"
echo "3. Consider creating setup/runtime phase separation"
echo "4. Update Issue #21 with findings"
