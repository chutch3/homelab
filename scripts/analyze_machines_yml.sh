#!/bin/bash

# Analysis script for machines.yml usage patterns
# This script investigates whether machines.yml is actually needed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Analyzing machines.yml Usage Patterns${NC}"
echo "=============================================="

# Find the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "\n${YELLOW}1. File References Analysis${NC}"
echo "----------------------------"

# Count all references to machines.yml
echo "📁 Finding all references to 'machines.yml'..."
REFERENCES=$(find . -type f \( -name "*.sh" -o -name "*.bats" -o -name "*.md" -o -name "*.yml" \) -exec grep -l "machines\.yml" {} \; 2>/dev/null || true)

if [ -n "$REFERENCES" ]; then
    echo -e "${GREEN}Found references in:${NC}"
    echo "$REFERENCES" | while read -r file; do
        count=$(grep -c "machines\.yml" "$file" 2>/dev/null || echo "0")
        echo "  • $file ($count occurrences)"
    done
else
    echo -e "${RED}❌ No references to machines.yml found${NC}"
fi

echo -e "\n${YELLOW}2. Functional Usage Analysis${NC}"
echo "------------------------------"

# Analyze scripts/machines.sh specifically
if [ -f "scripts/machines.sh" ]; then
    echo "📋 Analyzing scripts/machines.sh functionality..."

    # Check what functions exist
    FUNCTIONS=$(grep -n "^[a-zA-Z_][a-zA-Z0-9_]*\s*()" scripts/machines.sh | cut -d: -f2 | cut -d'(' -f1)
    echo -e "${GREEN}Functions found:${NC}"
    echo "$FUNCTIONS" | while read -r func; do
        echo "  • $func"
    done

    # Check if these functions are used elsewhere
    echo -e "\n📞 Checking if these functions are called elsewhere..."
    echo "$FUNCTIONS" | while read -r func; do
        if [ -n "$func" ]; then
            usage=$(find . -name "*.sh" -not -path "./scripts/machines.sh" -exec grep -l "$func" {} \; 2>/dev/null || true)
            if [ -n "$usage" ]; then
                echo -e "  • ${GREEN}$func${NC} is used in: $usage"
            else
                echo -e "  • ${YELLOW}$func${NC} appears unused outside machines.sh"
            fi
        fi
    done
else
    echo -e "${RED}❌ scripts/machines.sh not found${NC}"
fi

echo -e "\n${YELLOW}3. Configuration File Analysis${NC}"
echo "--------------------------------"

# Check if machines.yml.example exists and what it contains
if [ -f "machines.yml.example" ]; then
    echo "📄 Found machines.yml.example"
    echo "   Size: $(wc -l < machines.yml.example) lines"
    echo "   Content preview:"
    head -10 machines.yml.example | sed 's/^/     /'
else
    echo -e "${RED}❌ machines.yml.example not found${NC}"
fi

# Check if actual machines.yml exists
if [ -f "machines.yml" ]; then
    echo -e "${GREEN}✅ Active machines.yml found${NC}"
else
    echo -e "${YELLOW}⚠️  No active machines.yml file${NC}"
fi

echo -e "\n${YELLOW}4. Docker Swarm Alternative Analysis${NC}"
echo "-------------------------------------"

# Check if Docker Swarm commands are used that could replace machines.yml
echo "🐳 Checking for Docker Swarm node management commands..."

SWARM_COMMANDS=("docker node ls" "docker node inspect" "docker node update")
for cmd in "${SWARM_COMMANDS[@]}"; do
    usage=$(find . -name "*.sh" -exec grep -l "$cmd" {} \; 2>/dev/null || true)
    if [ -n "$usage" ]; then
        echo -e "  • ${GREEN}'$cmd'${NC} found in: $usage"
    else
        echo -e "  • ${YELLOW}'$cmd'${NC} not found in scripts"
    fi
done

echo -e "\n${BLUE}📊 Summary & Recommendations${NC}"
echo "==============================="

reference_count=$(echo "$REFERENCES" | wc -l)
if [ -z "$REFERENCES" ]; then
    reference_count=0
fi

echo "📈 Total references to machines.yml: $reference_count"

if [ "$reference_count" -eq 0 ]; then
    echo -e "${GREEN}✅ RECOMMENDATION: machines.yml appears unnecessary${NC}"
    echo "   • No references found in codebase"
    echo "   • Consider removing machines.yml.example"
elif [ "$reference_count" -le 2 ] && [ -f "machines.yml.example" ]; then
    echo -e "${YELLOW}⚠️  RECOMMENDATION: machines.yml has minimal usage${NC}"
    echo "   • Limited references suggest low value"
    echo "   • Investigate if Docker Swarm native discovery suffices"
else
    echo -e "${RED}🔍 RECOMMENDATION: Further investigation needed${NC}"
    echo "   • Multiple references suggest active usage"
    echo "   • Analyze each reference for actual necessity"
fi

echo -e "\n${BLUE}🎯 Next Steps${NC}"
echo "==============="
echo "1. Review each reference found above"
echo "2. Test if Docker Swarm native node discovery meets needs"
echo "3. Document decision in GitHub issue #21"
echo "4. If removing: create migration plan"
echo "5. If keeping: document clear use cases"
