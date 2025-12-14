#!/bin/sh
set -e

echo "[INIT] Installing dante-server..."
apk add --no-cache dante-server

echo "[INIT] Creating dante-server configuration..."
cat > /etc/sockd.conf <<'EOF'
# Dante SOCKS5 server configuration
logoutput: stderr

# DNS resolution
resolveprotocol: udp

# Internal interface (listen on all interfaces)
internal: 0.0.0.0 port = 1080

# External interface (use tun0 for VPN routing)
external: tun0

# Allow connections from Docker networks
clientmethod: none
socksmethod: none

# Client access rules
client pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: error
}

# SOCKS rules
socks pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: error
    protocol: tcp udp
}
EOF

echo "[INIT] Starting dante-server in background..."
# Wait a bit for tun0 to be available, then start dante
(
    sleep 10
    while ! ip link show tun0 >/dev/null 2>&1; do
        echo "[INIT] Waiting for tun0 interface..."
        sleep 2
    done
    echo "[INIT] tun0 is up, starting dante-server..."
    /usr/sbin/sockd -f /etc/sockd.conf
) &

echo "[INIT] Starting Gluetun..."
# Execute the original Gluetun entrypoint
exec /gluetun-entrypoint "$@"
