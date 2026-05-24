#!/bin/sh
set -e

# gluetun's FIREWALL_INPUT_PORTS=1080 adds an INPUT ACCEPT rule only on the
# default gateway interface (eth1). Docker overlay traffic arrives on eth0 and
# hits the default INPUT DROP. This loop injects an unrestricted port-1080
# ACCEPT at position 1 every 3s so it survives gluetun's VPN restart firewall
# reloads.
(
    while true; do
        iptables -C INPUT -p tcp --dport 1080 -j ACCEPT 2>/dev/null || \
            iptables -I INPUT 1 -p tcp --dport 1080 -j ACCEPT 2>/dev/null || true
        sleep 3
    done
) &

echo "[INIT] Starting Gluetun (WireGuard)..."
exec /gluetun-entrypoint "$@"
