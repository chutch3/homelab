#!/usr/bin/env bash
set -euo pipefail

ISCSI_APP_DATA="/mnt/iscsi/app-data/tor-browser"

echo "Creating Tor Browser directories..."
mkdir -p "$ISCSI_APP_DATA"

echo "Setting ownership to 1000:1000 (kasm-user)..."
chown -R 1000:1000 "$ISCSI_APP_DATA"

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Fill in WireGuard credentials (if not done):"
echo "       ./nordvpn-setup.sh --token <nordvpn_access_token>"
echo "       # Other providers: populate TOR_WIREGUARD_* in .env manually"
echo "  2. Generate TOR_BROWSER_VNC_PASSWORD in .env:"
echo "       openssl rand -base64 16"
echo "  3. Deploy:"
echo "       task ansible:deploy:service -- -e \"stack_name=tor-browser\""
