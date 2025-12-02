#!/bin/bash
set -euo pipefail

# selfhosted.sh - User-friendly wrapper for homelab CLI
# This file provides a nice banner and delegates to the new CLI structure

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-}")" && pwd)

# Colors
COLOR_RESET='\033[0m'

COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_BLUE='\033[0;34m'
COLOR_BOLD='\033[1m'

# ASCII Art Banner
show_banner() {
  echo -e "${COLOR_BOLD}${COLOR_BLUE}"
  cat << 'EOF'
 ███████ ███████ ██      ███████ ██   ██  ██████  ███████ ████████ ███████ ██████      ███████ ██   ██
 ██      ██      ██      ██      ██   ██ ██    ██ ██         ██    ██      ██   ██     ██      ██   ██
 ███████ █████   ██      █████   ███████ ██    ██ ███████    ██    █████   ██   ██     ███████ ███████
      ██ ██      ██      ██      ██   ██ ██    ██      ██    ██    ██      ██   ██          ██ ██   ██
 ███████ ███████ ███████ ██      ██   ██  ██████  ███████    ██    ███████ ██████  ██  ███████ ██   ██

EOF
  echo -e "${COLOR_GREEN}"
  cat << 'EOF'
   🏠 HOMELAB DEPLOYMENT AUTOMATION 🚀
   ═══════════════════════════════════════
   Docker Swarm • Container Management
   Network Configuration • SSL Automation
   Multi-Node Orchestration • Self-Healing
   ═══════════════════════════════════════

EOF
  echo -e "${COLOR_RESET}"
}

show_compact_banner() {
  echo -e "${COLOR_BOLD}${COLOR_BLUE}🏠 SELFHOSTED HOMELAB 🚀${COLOR_RESET} ${COLOR_GREEN}Deploy • Manage • Scale${COLOR_RESET}"
  echo -e "${COLOR_YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${COLOR_RESET}"
}

# Check if user wants help or no banner
SHOW_BANNER=true
for arg in "$@"; do
  if [[ "$arg" == "--help" || "$arg" == "-h" || "$arg" == "help" ]]; then
    SHOW_BANNER=false
    break
  fi
done

# Show banner for regular commands
if [ "$SHOW_BANNER" = true ]; then
  show_compact_banner
  echo
fi

# Delegate to new CLI structure
exec "$SCRIPT_DIR/scripts/cli.sh" "$@"
