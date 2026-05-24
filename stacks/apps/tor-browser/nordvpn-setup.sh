#!/usr/bin/env bash
# Fetch NordVPN WireGuard (NordLynx) credentials and upsert TOR_WIREGUARD_* in .env.
# NordVPN manages the keypair — this fetches the private key from their API.
# Safe to rerun — fetches the same persistent key each time.
#
# Other VPN providers: populate TOR_WIREGUARD_PRIVATE_KEY and TOR_WIREGUARD_ADDRESSES
# in .env manually per https://github.com/qdm12/gluetun-wiki/tree/main/setup/providers
#
# Usage:
#   ./nordvpn-setup.sh                              # prompts for access token
#   ./nordvpn-setup.sh --token <access_token>
#   ./nordvpn-setup.sh --token <token> --env-file /path/to/.env
#   ./nordvpn-setup.sh --token <token> --addresses <cidr>  # override WG address
#
# --addresses defaults to 10.5.0.2/32, NordVPN's fixed NordLynx interface address.
# Override only if NordVPN changes it or your account is assigned a different one.
#
# Get your NordVPN access token:
#   my.nordaccount.com/dashboard/nordvpn/manual-configuration/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
NORDVPN_TOKEN=""
WG_ADDRESSES="10.5.0.2/32"

while [[ $# -gt 0 ]]; do
    case $1 in
        --token)     NORDVPN_TOKEN="$2"; shift 2 ;;
        --env-file)  ENV_FILE="$2";      shift 2 ;;
        --addresses) WG_ADDRESSES="$2";  shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Preflight ─────────────────────────────────────────────────────────────────

if ! command -v curl &>/dev/null; then
    echo "Error: 'curl' not found."
    exit 1
fi

if ! command -v jq &>/dev/null; then
    echo "Error: 'jq' not found. Install it:"
    echo "  Ubuntu/Debian: sudo apt install jq"
    echo "  Arch:          sudo pacman -S jq"
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

if [[ -z "$NORDVPN_TOKEN" ]]; then
    echo "NordVPN access token required."
    echo "Get one at: my.nordaccount.com/dashboard/nordvpn/manual-configuration/"
    read -rsp "Access token: " NORDVPN_TOKEN
    echo
fi

# ── Fetch credentials from NordVPN ────────────────────────────────────────────

echo "[1/2] Fetching NordLynx private key from NordVPN..."
RESPONSE=$(curl -s \
    -u "token:${NORDVPN_TOKEN}" \
    "https://api.nordvpn.com/v1/users/services/credentials")

PRIVATE_KEY=$(echo "$RESPONSE" | jq -r '.nordlynx_private_key // empty')

if [[ -z "$PRIVATE_KEY" ]]; then
    echo "Error: Could not extract nordlynx_private_key. Response:"
    echo "$RESPONSE"
    exit 1
fi

echo "      Got private key (${#PRIVATE_KEY} chars)"

# ── Upsert .env ───────────────────────────────────────────────────────────────

echo "[2/2] Updating ${ENV_FILE}..."

upsert_env() {
    local key="$1"
    local value="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        echo "      Updated  ${key}"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
        echo "      Added    ${key}"
    fi
}

upsert_env "TOR_WIREGUARD_PRIVATE_KEY" "$PRIVATE_KEY"
upsert_env "TOR_WIREGUARD_ADDRESSES"   "$WG_ADDRESSES"

echo ""
echo "Done. Redeploy to apply:"
echo "  docker stack deploy -c stacks/apps/tor-browser/docker-compose.yml tor-browser"
