#!/usr/bin/env python3
import json
import os
import socket
import ssl
import struct
from http.server import BaseHTTPRequestHandler, HTTPServer

SOCKS_HOST = os.getenv("TOR_VPN_HOST", "tor-vpn")
SOCKS_PORT = int(os.getenv("TOR_VPN_SOCKS_PORT", "1080"))


def socks5_connect(proxy_host, proxy_port, dest_host, dest_port):
    """Return a socket tunneled through a SOCKS5 proxy with remote DNS resolution."""
    sock = socket.create_connection((proxy_host, proxy_port), timeout=10)
    sock.sendall(b"\x05\x01\x00")  # version=5, nmethods=1, no-auth
    if sock.recv(2) != b"\x05\x00":
        raise RuntimeError("SOCKS5 auth rejected")
    host_b = dest_host.encode()
    sock.sendall(
        b"\x05\x01\x00\x03"
        + bytes([len(host_b)])
        + host_b
        + struct.pack(">H", dest_port)
    )
    hdr = sock.recv(4)
    if len(hdr) < 4 or hdr[1] != 0:
        raise RuntimeError(f"SOCKS5 connect failed (reply={hdr[1] if len(hdr) > 1 else '?'})")
    atyp = hdr[3]
    if atyp == 1:
        sock.recv(4)
    elif atyp == 3:
        sock.recv(sock.recv(1)[0])
    elif atyp == 4:
        sock.recv(16)
    sock.recv(2)
    return sock


def fetch_ip_info():
    try:
        sock = socks5_connect(SOCKS_HOST, SOCKS_PORT, "ipinfo.io", 443)
        ctx = ssl.create_default_context()
        tls = ctx.wrap_socket(sock, server_hostname="ipinfo.io")
        tls.sendall(
            b"GET /json HTTP/1.0\r\n"
            b"Host: ipinfo.io\r\n"
            b"Accept: application/json\r\n"
            b"\r\n"
        )
        raw = b""
        while chunk := tls.recv(4096):
            raw += chunk
        tls.close()
        body = raw.split(b"\r\n\r\n", 1)[1].decode()
        data = json.loads(body)
        return {
            "ip": data.get("ip", "Unknown"),
            "org": data.get("org", "Unknown"),
            "city": data.get("city", ""),
            "country": data.get("country", ""),
            "ok": True,
        }
    except Exception as e:
        return {"ip": "ERROR", "org": str(e), "city": "", "country": "", "ok": False}


def render_page(info):
    color = "#00ff88" if info["ok"] else "#ff4444"
    status = "VPN ACTIVE" if info["ok"] else "VPN ERROR — CHECK GLUETUN"
    location = ", ".join(filter(None, [info["city"], info["country"]]))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="30">
  <title>VPN Status</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Courier New', monospace;
      background: #0d0d1a;
      color: #e0e0e0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      gap: 1.2rem;
    }}
    .label {{ font-size: 0.85rem; letter-spacing: 0.35em; color: #555; text-transform: uppercase; }}
    .ip {{ font-size: clamp(2.5rem, 8vw, 5rem); font-weight: bold; color: {color}; letter-spacing: 0.05em; }}
    .detail {{ font-size: 1.1rem; color: #777; }}
    .status {{
      margin-top: 1.5rem;
      padding: 0.4rem 1.2rem;
      border: 1px solid {color}44;
      border-radius: 4px;
      font-size: 0.8rem;
      letter-spacing: 0.15em;
      color: {color};
    }}
    .refresh {{ margin-top: 3rem; font-size: 0.7rem; color: #333; }}
  </style>
</head>
<body>
  <div class="label">VPN Exit IP</div>
  <div class="ip">{info['ip']}</div>
  <div class="detail">{info['org']}</div>
  {"<div class='detail'>" + location + "</div>" if location else ""}
  <div class="status">{status}</div>
  <div class="refresh">auto-refreshes every 30s</div>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        info = fetch_ip_info()
        body = render_page(info).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    print(f"[IP-CHECK] Listening on :8080, proxying via {SOCKS_HOST}:{SOCKS_PORT}")
    server.serve_forever()
