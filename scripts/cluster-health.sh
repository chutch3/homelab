#!/usr/bin/env bash
# scripts/cluster-health.sh
# Quick read-only cluster health check. Run from the manager node.
# Usage: bash scripts/cluster-health.sh

set -euo pipefail

BOLD='\033[1m'
DIM='\033[2m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RESET='\033[0m'

BAR="════════════════════════════════════════════════"
SEP="────────────────────────────────────────────────"

section() {
    echo ""
    echo -e "${BOLD}── $1${RESET}"
    echo -e "${DIM}${SEP}${RESET}"
}

echo ""
echo -e "${BOLD}${CYAN}${BAR}${RESET}"
echo -e "${BOLD}${CYAN}  CLUSTER HEALTH REPORT${RESET}"
echo -e "${BOLD}${CYAN}${BAR}${RESET}"

# ── Nodes ────────────────────────────────────────────────
section "Nodes"
docker node ls --format "table {{.Hostname}}\t{{.Status}}\t{{.Availability}}\t{{.ManagerStatus}}" \
    | awk -v bold="$BOLD" -v red="$RED" -v green="$GREEN" -v reset="$RESET" \
        'NR==1 { print; next }
         /Down|Drain/ { print red $0 reset; next }
         { print green "  ✓ " reset $0 }'

# ── Service Replicas ────────────────────────────────────
section "Service Replicas"
degraded=$(docker service ls --format "{{.Name}}\t{{.Replicas}}" \
    | awk -F'\t' '{split($2,a,"/"); if(a[1]!=a[2]) print $1"\t"$2}')
if [ -z "$degraded" ]; then
    echo -e "  ${GREEN}✓ All services at desired replica count${RESET}"
else
    while IFS=$'\t' read -r name replicas; do
        echo -e "  ${RED}⚠  ${name}: ${replicas}${RESET}"
    done <<< "$degraded"
fi

# ── DNS Crash History ───────────────────────────────────
section "DNS Crash History"
failure_count=$(docker service ps dns_dns-server --no-trunc \
    --format "{{.CurrentState}}" | grep -c "Failed" || true)

if [ "${failure_count}" -gt 2 ]; then
    echo -e "  ${RED}⚠  ${failure_count} failures recorded${RESET}"
elif [ "${failure_count}" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠  ${failure_count} failure(s) recorded${RESET}"
else
    echo -e "  ${GREEN}✓ No failures recorded${RESET}"
fi
echo ""
docker service ps dns_dns-server --no-trunc \
    --format "  {{.CurrentState}}\t{{.Error}}" | head -6 \
    | awk -v red="$RED" -v green="$GREEN" -v dim="$DIM" -v reset="$RESET" \
        '/Failed/ { print red $0 reset; next }
         /Running/ { print green $0 reset; next }
         { print dim $0 reset }'

# ── Gossip Stability ────────────────────────────────────
section "Gossip Stability (last 1h)"
gossip_count=$(journalctl -u docker --since "1 hour ago" --no-pager -q \
    | grep -cE "memberlist.*(failed|suspect|Marking)|NetworkDB.*healthscore|connectivity issues" \
    || true)

if [ "${gossip_count}" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠  ${gossip_count} instability event(s) detected${RESET}"
    echo -e "  ${DIM}journalctl -u docker --since '1 hour ago' | grep memberlist${RESET}"
else
    echo -e "  ${GREEN}✓ No gossip instability detected${RESET}"
fi

echo ""
echo -e "${DIM}${BAR}${RESET}"
echo ""
