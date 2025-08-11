#!/bin/bash

# Analysis script for service enablement and deployment concerns
# Focus: How service enablement is tracked for Docker Compose vs Swarm deployments

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Service Enablement & Deployment Analysis${NC}"
echo "============================================"

# Find the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "\n${YELLOW}1. Service Configuration Structure Analysis${NC}"
echo "--------------------------------------------"

echo "📋 Analyzing config/services.yaml structure..."

if [ -f "config/services.yaml" ]; then
    echo -e "${GREEN}✅ Found config/services.yaml${NC}"

    # Check for enabled flags in services.yaml
    echo -e "\n🔍 Checking for 'enabled' flags in services.yaml:"
    if grep -q "enabled:" config/services.yaml; then
        echo -e "${GREEN}✅ Found 'enabled' flags in services.yaml${NC}"
        enabled_count=$(grep -c "enabled:" config/services.yaml)
        echo "   📊 Total 'enabled' references: $enabled_count"

        # Show examples
        echo "   📄 Examples:"
        grep -n "enabled:" config/services.yaml | head -3 | sed 's/^/      /'
    else
        echo -e "${RED}❌ No 'enabled' flags found in services.yaml${NC}"
        echo "   This might be the problem - how are services enabled/disabled?"
    fi

    # Check for service structure
    echo -e "\n🏗️ Service structure analysis:"
    total_services=$(yq '.services | keys[]' config/services.yaml | wc -l)
    echo "   📊 Total services defined: $total_services"

    # Sample a few services to understand structure
    echo "   📄 Sample service structures:"
    yq '.services | keys[]' config/services.yaml | head -3 | while read -r service; do
        echo "      • $service:"
        yq ".services.$service | keys[]" config/services.yaml | head -5 | sed 's/^/        - /' || echo "        - (error reading service structure)"
    done

else
    echo -e "${RED}❌ config/services.yaml not found${NC}"
    exit 1
fi

echo -e "\n${YELLOW}2. Service Enablement Mechanisms${NC}"
echo "----------------------------------"

echo "🔍 How are services currently enabled/disabled?"

# Check for enabled services tracking files
echo -e "\n📁 Checking for enablement tracking files:"

if [ -f ".enabled-services" ]; then
    echo -e "${GREEN}✅ Found .enabled-services file${NC}"
    service_count=$(wc -l < .enabled-services)
    echo "   📊 Enabled services: $service_count"
    echo "   📄 Contents:"
    head -5 .enabled-services | sed 's/^/      /'
else
    echo -e "${YELLOW}⚠️  No .enabled-services file found${NC}"
fi

if [ -d "reverseproxy/templates/conf.d/enabled" ]; then
    echo -e "${GREEN}✅ Found nginx enabled directory${NC}"
    enabled_nginx=$(find reverseproxy/templates/conf.d/enabled/ -maxdepth 1 -type f 2>/dev/null | wc -l)
    echo "   📊 Enabled nginx configs: $enabled_nginx"
    if [ "$enabled_nginx" -gt 0 ]; then
        echo "   📄 Enabled services:"
        find reverseproxy/templates/conf.d/enabled/ -maxdepth 1 -type f -exec basename {} \; | head -5 | sed 's/^/      /'
    fi
else
    echo -e "${YELLOW}⚠️  No nginx enabled directory found${NC}"
fi

# Check for enabled services in generated files
echo -e "\n📄 Checking generated deployment files:"

if [ -f "generated-docker-compose.yaml" ]; then
    echo -e "${GREEN}✅ Found generated-docker-compose.yaml${NC}"
    compose_services=$(yq '.services | keys[]' generated-docker-compose.yaml 2>/dev/null | wc -l || echo "0")
    echo "   📊 Services in compose file: $compose_services"
    echo "   📄 Services included:"
    yq '.services | keys[]' generated-docker-compose.yaml 2>/dev/null | head -5 | sed 's/^/      /' || echo "      (error reading services)"
else
    echo -e "${YELLOW}⚠️  No generated-docker-compose.yaml found${NC}"
fi

if [ -f "generated-swarm-stack.yaml" ]; then
    echo -e "${GREEN}✅ Found generated-swarm-stack.yaml${NC}"
    swarm_services=$(yq '.services | keys[]' generated-swarm-stack.yaml 2>/dev/null | wc -l || echo "0")
    echo "   📊 Services in swarm file: $swarm_services"
else
    echo -e "${YELLOW}⚠️  No generated-swarm-stack.yaml found${NC}"
fi

echo -e "\n${YELLOW}3. Docker Compose vs Swarm Enablement${NC}"
echo "--------------------------------------"

echo "🐳 Analyzing deployment-specific enablement patterns..."

# Check how services are filtered for different deployment types
echo -e "\n🔍 Service generation logic analysis:"

if [ -f "scripts/service_generator.sh" ]; then
    echo -e "${GREEN}✅ Analyzing scripts/service_generator.sh${NC}"

    # Check for compose-specific generation
    if grep -q "docker.*compose" scripts/service_generator.sh; then
        echo "   📄 Docker Compose generation logic found"
        grep -n "compose" scripts/service_generator.sh | head -3 | sed 's/^/      /'
    fi

    # Check for swarm-specific generation
    if grep -q "swarm" scripts/service_generator.sh; then
        echo "   📄 Swarm generation logic found"
        grep -n "swarm" scripts/service_generator.sh | head -3 | sed 's/^/      /'
    fi

    # Check for enablement filtering
    if grep -q "enabled" scripts/service_generator.sh; then
        echo -e "${GREEN}   ✅ Found enablement filtering logic${NC}"
        grep -n "enabled" scripts/service_generator.sh | head -3 | sed 's/^/      /'
    else
        echo -e "${RED}   ❌ No enablement filtering found${NC}"
        echo "      This might be the core issue!"
    fi

else
    echo -e "${RED}❌ scripts/service_generator.sh not found${NC}"
fi

echo -e "\n${YELLOW}4. Service Enablement Workflow Analysis${NC}"
echo "----------------------------------------"

echo "🔄 How does a user enable/disable services?"

# Check CLI interface
if [ -f "selfhosted.sh" ]; then
    echo -e "${GREEN}✅ Analyzing selfhosted.sh CLI${NC}"

    if grep -q "enable\|disable" selfhosted.sh; then
        echo "   📄 Enable/disable commands found:"
        grep -n -A 2 -B 2 "enable\|disable" selfhosted.sh | head -10 | sed 's/^/      /'
    else
        echo -e "${YELLOW}   ⚠️  No enable/disable commands found in CLI${NC}"
    fi

    if grep -q "service" selfhosted.sh; then
        echo "   📄 Service management commands:"
        grep -n "service" selfhosted.sh | head -3 | sed 's/^/      /'
    fi
fi

echo -e "\n${YELLOW}5. Problem Identification${NC}"
echo "-------------------------"

echo "🎯 Identifying the core issue with service enablement..."

# Compare what's in services.yaml vs what gets deployed
compose_services_count=0
swarm_services_count=0
total_services_count=0

if [ -f "config/services.yaml" ]; then
    total_services_count=$(yq '.services | keys[]' config/services.yaml 2>/dev/null | wc -l || echo "0")
fi

if [ -f "generated-docker-compose.yaml" ]; then
    compose_services_count=$(yq '.services | keys[]' generated-docker-compose.yaml 2>/dev/null | wc -l || echo "0")
fi

if [ -f "generated-swarm-stack.yaml" ]; then
    swarm_services_count=$(yq '.services | keys[]' generated-swarm-stack.yaml 2>/dev/null | wc -l || echo "0")
fi

echo "📊 Service count comparison:"
echo "   • Total services in config: $total_services_count"
echo "   • Services in Docker Compose: $compose_services_count"
echo "   • Services in Swarm stack: $swarm_services_count"

if [ "$total_services_count" -eq "$compose_services_count" ] && [ "$total_services_count" -eq "$swarm_services_count" ]; then
    echo -e "${YELLOW}⚠️  All services are deployed in both modes${NC}"
    echo "   This suggests no selective enablement is happening"
elif [ "$compose_services_count" -ne "$swarm_services_count" ]; then
    echo -e "${GREEN}✅ Different services deployed per mode${NC}"
    echo "   This suggests some enablement logic exists"
else
    echo -e "${RED}❌ Unclear enablement pattern${NC}"
    echo "   Need to investigate further"
fi

echo -e "\n${BLUE}🔍 Key Issues Identified${NC}"
echo "========================"

issues_found=0

# Issue 1: No enabled flags in services.yaml
if ! grep -q "enabled:" config/services.yaml 2>/dev/null; then
    echo -e "${RED}❌ Issue 1: No 'enabled' flags in services.yaml${NC}"
    echo "   • Services cannot be selectively enabled/disabled"
    echo "   • All services might be deployed regardless of need"
    ((issues_found++))
fi

# Issue 2: Missing enablement CLI
if ! grep -q "enable\|disable" selfhosted.sh 2>/dev/null; then
    echo -e "${RED}❌ Issue 2: No service enable/disable CLI commands${NC}"
    echo "   • Users have no way to control which services run"
    echo "   • Must manually edit configuration files"
    ((issues_found++))
fi

# Issue 3: Docker Compose vs Swarm differences
if [ "$compose_services_count" -gt 0 ] && [ "$swarm_services_count" -gt 0 ] && [ "$compose_services_count" -eq "$swarm_services_count" ]; then
    echo -e "${YELLOW}⚠️  Issue 3: Same services deployed in both modes${NC}"
    echo "   • No deployment-specific service selection"
    echo "   • Might not be optimized for different use cases"
    ((issues_found++))
fi

if [ "$issues_found" -eq 0 ]; then
    echo -e "${GREEN}✅ No major issues found with service enablement${NC}"
    echo "   • System appears to have proper enablement logic"
else
    echo -e "\n${RED}📊 Total issues found: $issues_found${NC}"
fi

echo -e "\n${BLUE}🎯 Recommendations${NC}"
echo "=================="

if [ "$issues_found" -gt 0 ]; then
    echo -e "${CYAN}Action Items:${NC}"
    echo "1. Add 'enabled: true/false' flags to services in config/services.yaml"
    echo "2. Implement service enable/disable CLI commands"
    echo "3. Add enablement filtering in service generation"
    echo "4. Create different default enablement for Compose vs Swarm"
    echo "5. Document service enablement workflow"
else
    echo -e "${CYAN}Maintenance:${NC}"
    echo "1. Document existing enablement mechanisms"
    echo "2. Ensure consistency across deployment types"
    echo "3. Add tests for enablement logic"
fi

echo -e "\n${GREEN}✅ Service enablement analysis complete${NC}"
