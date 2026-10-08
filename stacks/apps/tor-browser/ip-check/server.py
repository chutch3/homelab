#!/usr/bin/env python3
import json
import os
import socket
import ssl
import struct
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

_VPN_HOST: str = os.getenv("TOR_VPN_HOST", "tor-vpn")
SOCKS_PORT: int = int(os.getenv("TOR_VPN_SOCKS_PORT", "1080"))
VPN_CONTROL: str = f"http://{_VPN_HOST}:{os.getenv('TOR_VPN_CONTROL_PORT', '8000')}"

_lock = threading.Lock()
_rotating: bool = False
_last_rotated: Optional[float] = None
_auto_interval: int = int(os.getenv("TOR_VPN_AUTO_ROTATE_INTERVAL", "0"))
_next_rotation: Optional[float] = None
_auto_timer: Optional[threading.Timer] = None


# ── VPN probe ─────────────────────────────────────────────────────────────────

def socks5_connect(dest_host: str, dest_port: int) -> socket.socket:
    sock = socket.create_connection((_VPN_HOST, SOCKS_PORT), timeout=10)
    sock.sendall(b"\x05\x01\x00")
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


def fetch_ip_info() -> dict:
    try:
        sock = socks5_connect("ipinfo.io", 443)
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
            "org": data.get("org", ""),
            "city": data.get("city", ""),
            "country": data.get("country", ""),
            "ok": True,
        }
    except Exception as e:
        return {"ip": "ERROR", "org": str(e), "city": "", "country": "", "ok": False}


# ── Rotation ──────────────────────────────────────────────────────────────────

def _vpn_put(action: str) -> None:
    req = urllib.request.Request(
        f"{VPN_CONTROL}/v1/vpn/status",
        data=json.dumps({"status": action}).encode(),
        method="PUT",
    )
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10):
        pass


def _do_rotate() -> None:
    global _rotating, _last_rotated
    try:
        _vpn_put("stopped")
        time.sleep(5)
        _vpn_put("running")
        with _lock:
            _last_rotated = time.time()
    except Exception as e:
        print(f"[IP-CHECK] Rotation error: {e}")
    finally:
        with _lock:
            _rotating = False


def start_rotation() -> bool:
    global _rotating
    with _lock:
        if _rotating:
            return False
        _rotating = True
    threading.Thread(target=_do_rotate, daemon=True).start()
    return True


def _auto_tick() -> None:
    start_rotation()
    _schedule_auto()


def _schedule_auto() -> None:
    global _auto_timer, _next_rotation
    with _lock:
        interval = _auto_interval
    if interval <= 0:
        return
    with _lock:
        _next_rotation = time.time() + interval
    t = threading.Timer(interval, _auto_tick)
    t.daemon = True
    t.start()
    with _lock:
        _auto_timer = t


def set_auto_rotate(interval: int) -> None:
    global _auto_interval, _auto_timer, _next_rotation
    with _lock:
        _auto_interval = interval
        if _auto_timer is not None:
            _auto_timer.cancel()
            _auto_timer = None
        _next_rotation = None
    if interval > 0:
        _schedule_auto()


# ── HTTP server ───────────────────────────────────────────────────────────────

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VPN Status</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Courier New', monospace;
      background: #0d0d1a; color: #e0e0e0;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      min-height: 100vh; gap: 1.1rem;
    }
    .label { font-size: 0.8rem; letter-spacing: 0.35em; color: #444; text-transform: uppercase; }
    #ip { font-size: clamp(2.5rem, 8vw, 5rem); font-weight: bold; letter-spacing: 0.05em; }
    .detail { font-size: 1rem; color: #666; }
    #badge {
      padding: 0.35rem 1rem; border: 1px solid currentColor;
      border-radius: 4px; font-size: 0.75rem; letter-spacing: 0.15em; opacity: 0.7;
    }
    .controls { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; justify-content: center; margin-top: 0.5rem; }
    button {
      padding: 0.45rem 1.4rem; background: transparent;
      border: 1px solid #00ff8866; color: #00ff88;
      font-family: inherit; font-size: 0.72rem; letter-spacing: 0.12em;
      text-transform: uppercase; cursor: pointer; border-radius: 4px;
    }
    button:hover:not(:disabled) { background: #00ff8811; }
    button:disabled { opacity: 0.3; cursor: not-allowed; }
    button.busy { border-color: #ffaa0066; color: #ffaa00; }
    select {
      background: #0d0d1a; border: 1px solid #2a2a3a; color: #555;
      font-family: inherit; font-size: 0.72rem;
      padding: 0.45rem 0.75rem; border-radius: 4px; cursor: pointer;
    }
    .meta { margin-top: 1rem; font-size: 0.65rem; color: #2e2e3e; text-align: center; line-height: 2; }
  </style>
</head>
<body>
  <div class="label">VPN Exit IP</div>
  <div id="ip">—</div>
  <div class="detail" id="org"></div>
  <div class="detail" id="loc"></div>
  <div id="badge"></div>
  <div class="controls">
    <button id="btn" onclick="rotateNow()">Rotate Server</button>
    <select id="auto-sel" onchange="setAuto(this.value)">
      <option value="0">Auto: Off</option>
      <option value="1800">Auto: 30 min</option>
      <option value="3600">Auto: 1 hr</option>
      <option value="7200">Auto: 2 hr</option>
      <option value="14400">Auto: 4 hr</option>
    </select>
  </div>
  <div class="meta">
    <div id="last-r"></div>
    <div id="next-r"></div>
    <div id="updated"></div>
  </div>
<script>
let nextTs = 0, autoInterval = 0;

function fmt(ts) { return ts ? new Date(ts * 1000).toLocaleTimeString() : ''; }
function countdown(ts) {
  if (!ts) return '';
  const s = Math.max(0, Math.round(ts - Date.now() / 1000));
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}m ${s % 60}s` : `${s}s`;
}

async function poll() {
  try {
    const d = await fetch('/status').then(r => r.json());
    const c = d.ok ? '#00ff88' : '#ff4444';
    document.getElementById('ip').textContent = d.ip;
    document.getElementById('ip').style.color = c;
    document.getElementById('org').textContent = d.org || '';
    document.getElementById('loc').textContent = [d.city, d.country].filter(Boolean).join(', ');
    const badge = document.getElementById('badge');
    badge.textContent = d.ok ? 'VPN ACTIVE' : 'VPN ERROR';
    badge.style.color = c;
    const btn = document.getElementById('btn');
    btn.disabled = d.rotating;
    btn.className = d.rotating ? 'busy' : '';
    btn.textContent = d.rotating ? 'Rotating…' : 'Rotate Server';
    if (d.auto_interval !== undefined) {
      autoInterval = d.auto_interval;
      document.getElementById('auto-sel').value = autoInterval;
    }
    nextTs = d.next_rotation || 0;
    document.getElementById('last-r').textContent = d.last_rotated ? `last rotation  ${fmt(d.last_rotated)}` : '';
    document.getElementById('updated').textContent = `updated  ${new Date().toLocaleTimeString()}`;
  } catch(_) {}
}

function tick() {
  document.getElementById('next-r').textContent =
    (nextTs && autoInterval > 0) ? `next rotation  ${countdown(nextTs)}` : '';
}

async function rotateNow() {
  const btn = document.getElementById('btn');
  btn.disabled = true; btn.className = 'busy'; btn.textContent = 'Rotating…';
  await fetch('/rotate', { method: 'POST' });
  setTimeout(poll, 15000);
}

async function setAuto(v) {
  autoInterval = parseInt(v);
  await fetch('/auto-rotate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ interval: autoInterval })
  });
  poll();
}

poll();
setInterval(poll, 30000);
setInterval(tick, 1000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        pass

    def _json(self, data: dict, code: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if self.path == "/status":
            info = fetch_ip_info()
            with _lock:
                info.update({
                    "rotating": _rotating,
                    "last_rotated": _last_rotated,
                    "auto_interval": _auto_interval,
                    "next_rotation": _next_rotation,
                })
            self._json(info)
            return
        body = PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path == "/rotate":
            self._json({"started": start_rotation()})
            return
        if self.path == "/auto-rotate":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            set_auto_rotate(int(body.get("interval", 0)))
            with _lock:
                self._json({"interval": _auto_interval, "next_rotation": _next_rotation})
            return
        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    if _auto_interval > 0:
        _schedule_auto()
        print(f"[IP-CHECK] Auto-rotate enabled: every {_auto_interval}s")
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    print(f"[IP-CHECK] Listening :8080 | SOCKS5 {_VPN_HOST}:{SOCKS_PORT} | control {VPN_CONTROL}")
    server.serve_forever()
