#!/bin/sh
set -e

# gluetun's FIREWALL_INPUT_PORTS adds INPUT ACCEPT only on eth1 (WireGuard
# gateway). Docker overlay traffic arrives on eth0 and hits the default DROP.
# Inject ACCEPT rules for all service ports every 3s so they survive gluetun's
# VPN-restart firewall reloads.
#   1080 — SOCKS5 proxy
#   8000 — gluetun HTTP control server (used by ip-check for rotation)
(
    while true; do
        for port in 1080 8000; do
            iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null || \
                iptables -I INPUT 1 -p tcp --dport "$port" -j ACCEPT 2>/dev/null || true
        done
        sleep 3
    done
) &

echo "[INIT] Starting Gluetun (WireGuard)..."
exec /gluetun-entrypoint "$@"
