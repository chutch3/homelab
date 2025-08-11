#!/bin/bash

# Analysis script for service.yml vs services.yaml naming conflicts
# This script audits all service configuration references

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
# PURPLE='\033[0;35m' # Unused
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Service Configuration References Audit${NC}"
echo "=========================================="

# Find the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "\n${YELLOW}1. File Existence Check${NC}"
echo "------------------------"

# Check what service configuration files actually exist
echo "🔍 Checking for service configuration files..."

files_found=()
if [ -f "config/services.yaml" ]; then
    echo -e "  ✅ ${GREEN}config/services.yaml${NC} exists ($(wc -l < config/services.yaml) lines)"
    files_found+=("config/services.yaml")
else
    echo -e "  ❌ ${RED}config/services.yaml${NC} not found"
fi

if [ -f "service.yml" ]; then
    echo -e "  ⚠️  ${YELLOW}service.yml${NC} exists in root ($(wc -l < service.yml) lines)"
    files_found+=("service.yml")
else
    echo -e "  ✅ ${GREEN}service.yml${NC} does not exist in root (good)"
fi

if [ -f "config/service.yml" ]; then
    echo -e "  ⚠️  ${YELLOW}config/service.yml${NC} exists ($(wc -l < config/service.yml) lines)"
    files_found+=("config/service.yml")
else
    echo -e "  ✅ ${GREEN}config/service.yml${NC} does not exist (good)"
fi

echo -e "\n📊 Total service config files found: ${#files_found[@]}"

echo -e "\n${YELLOW}2. Reference Pattern Analysis${NC}"
echo "------------------------------"

echo "🔍 Searching for references to different service file patterns..."

# Search for service.yml references (problematic)
echo -e "\n${CYAN}References to 'service.yml':${NC}"
SERVICE_YML_REFS=$(find . -type f \( -name "*.sh" -o -name "*.bats" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" \) -exec grep -l "service\.yml" {} \; 2>/dev/null || true)

if [ -n "$SERVICE_YML_REFS" ]; then
    echo -e "${RED}⚠️  Found problematic references:${NC}"
    echo "$SERVICE_YML_REFS" | while read -r file; do
        count=$(grep -c "service\.yml" "$file" 2>/dev/null || echo "0")
        echo "  • $file ($count occurrences)"

        # Show context of references
        echo "    Context:"
        grep -n "service\.yml" "$file" | head -3 | sed 's/^/      /'
    done
else
    echo -e "${GREEN}✅ No references to 'service.yml' found${NC}"
fi

# Search for services.yaml references (correct)
echo -e "\n${CYAN}References to 'services.yaml':${NC}"
SERVICES_YAML_REFS=$(find . -type f \( -name "*.sh" -o -name "*.bats" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" \) -exec grep -l "services\.yaml" {} \; 2>/dev/null || true)

if [ -n "$SERVICES_YAML_REFS" ]; then
    echo -e "${GREEN}✅ Found correct references:${NC}"
    echo "$SERVICES_YAML_REFS" | while read -r file; do
        count=$(grep -c "services\.yaml" "$file" 2>/dev/null || echo "0")
        echo "  • $file ($count occurrences)"
    done
else
    echo -e "${RED}❌ No references to 'services.yaml' found${NC}"
fi

echo -e "\n${YELLOW}3. Configuration Environment Variables${NC}"
echo "--------------------------------------"

echo "🔍 Checking environment variable patterns..."

# Check for SERVICES_CONFIG vs SERVICE_CONFIG
SERVICES_CONFIG_REFS=$(find . -name "*.sh" -exec grep -l "SERVICES_CONFIG" {} \; 2>/dev/null || true)
SERVICE_CONFIG_REFS=$(find . -name "*.sh" -exec grep -l "SERVICE_CONFIG" {} \; 2>/dev/null || true)

echo -e "\n${CYAN}SERVICES_CONFIG variable usage:${NC}"
if [ -n "$SERVICES_CONFIG_REFS" ]; then
    echo -e "${GREEN}✅ Found SERVICES_CONFIG usage:${NC}"
    echo "$SERVICES_CONFIG_REFS" | while read -r file; do
        count=$(grep -c "SERVICES_CONFIG" "$file" 2>/dev/null || echo "0")
        echo "  • $file ($count occurrences)"
    done
else
    echo -e "${YELLOW}⚠️  No SERVICES_CONFIG usage found${NC}"
fi

echo -e "\n${CYAN}SERVICE_CONFIG variable usage:${NC}"
if [ -n "$SERVICE_CONFIG_REFS" ]; then
    echo -e "${RED}⚠️  Found potentially confusing SERVICE_CONFIG:${NC}"
    echo "$SERVICE_CONFIG_REFS" | while read -r file; do
        count=$(grep -c "SERVICE_CONFIG" "$file" 2>/dev/null || echo "0")
        echo "  • $file ($count occurrences)"
    done
else
    echo -e "${GREEN}✅ No confusing SERVICE_CONFIG usage${NC}"
fi

echo -e "\n${YELLOW}4. Documentation Analysis${NC}"
echo "--------------------------"

echo "📚 Checking documentation for service configuration references..."

DOC_REFS=$(find docs -name "*.md" -exec grep -l -E "(service\.yml|services\.yaml)" {} \; 2>/dev/null || true)

if [ -n "$DOC_REFS" ]; then
    echo -e "${GREEN}Found documentation references:${NC}"
    echo "$DOC_REFS" | while read -r file; do
        echo "  • $file"

        # Check what type of references
        if grep -q "service\.yml" "$file"; then
            echo -e "    ${RED}⚠️  Contains 'service.yml' references${NC}"
        fi
        if grep -q "services\.yaml" "$file"; then
            echo -e "    ${GREEN}✅ Contains 'services.yaml' references${NC}"
        fi
    done
else
    echo -e "${YELLOW}⚠️  No documentation found with service config references${NC}"
fi

echo -e "\n${YELLOW}5. Code Pattern Consistency Check${NC}"
echo "----------------------------------"

echo "🔍 Analyzing actual usage patterns in scripts..."

# Check how services configuration is actually loaded/used
echo -e "\n${CYAN}Service configuration loading patterns:${NC}"

# Look for yq operations on service files
YQ_USAGE=$(find scripts -name "*.sh" -exec grep -l "yq.*services" {} \; 2>/dev/null || true)
if [ -n "$YQ_USAGE" ]; then
    echo -e "${GREEN}Found yq operations on services:${NC}"
    echo "$YQ_USAGE" | while read -r file; do
        echo "  • $file"
        grep -n "yq.*services" "$file" | head -2 | sed 's/^/    /'
    done
fi

# Look for direct file path references
echo -e "\n${CYAN}Direct file path usage:${NC}"
CONFIG_PATHS=$(find scripts -name "*.sh" -exec grep -l "config.*\.ya*ml" {} \; 2>/dev/null || true)
if [ -n "$CONFIG_PATHS" ]; then
    echo "$CONFIG_PATHS" | while read -r file; do
        echo "  • $file"
        grep -n "config.*\.ya*ml" "$file" | head -2 | sed 's/^/    /'
    done
fi

echo -e "\n${BLUE}📊 Summary Analysis${NC}"
echo "==================="

# Count different types of references
service_yml_count=0
services_yaml_count=0

if [ -n "$SERVICE_YML_REFS" ]; then
    service_yml_count=$(echo "$SERVICE_YML_REFS" | wc -l)
fi

if [ -n "$SERVICES_YAML_REFS" ]; then
    services_yaml_count=$(echo "$SERVICES_YAML_REFS" | wc -l)
fi

echo "📈 Reference Count Analysis:"
echo "  • 'service.yml' references: $service_yml_count files"
echo "  • 'services.yaml' references: $services_yaml_count files"

if [ "$service_yml_count" -gt 0 ]; then
    echo -e "\n${RED}⚠️  PROBLEM DETECTED: Inconsistent naming${NC}"
    echo "   • Found references to 'service.yml' which conflicts with 'services.yaml'"
    echo "   • This creates confusion about which file to use"
    echo "   • Need to standardize on single naming convention"
elif [ "$services_yaml_count" -gt 0 ]; then
    echo -e "\n${GREEN}✅ CONSISTENT NAMING: All references use 'services.yaml'${NC}"
    echo "   • No conflicting 'service.yml' references found"
    echo "   • Naming convention is consistent"
else
    echo -e "\n${YELLOW}⚠️  NO REFERENCES: No service configuration references found${NC}"
    echo "   • This might indicate unused configuration"
    echo "   • Or configuration access through other means"
fi

echo -e "\n${BLUE}🎯 Recommendations${NC}"
echo "=================="

if [ "$service_yml_count" -gt 0 ]; then
    echo -e "${CYAN}Action Required:${NC}"
    echo "1. Standardize all references to use 'services.yaml'"
    echo "2. Update documentation to use consistent naming"
    echo "3. Remove any references to 'service.yml'"
    echo "4. Update environment variables to use SERVICES_CONFIG"
elif [ "$services_yaml_count" -gt 0 ]; then
    echo -e "${CYAN}Maintenance:${NC}"
    echo "1. Continue using 'services.yaml' as standard"
    echo "2. Ensure new code follows this convention"
    echo "3. Document the naming standard clearly"
else
    echo -e "${CYAN}Investigation:${NC}"
    echo "1. Determine if service configuration is actually used"
    echo "2. If used, document how it's accessed"
    echo "3. If unused, consider removing config files"
fi

echo -e "\n${GREEN}✅ Analysis complete - check results above for issues${NC}"
