// A real HTTP/WebSocket boundary for the installed frontend. No production access.
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { WebSocketServer } from 'ws';

const [webroot, mode = 'stream'] = process.argv.slice(2);
const tone = readFileSync(new URL('../fixtures/tone.mpegts', import.meta.url));
const relay = new WebSocketServer({ noServer: true });
const allowed = new Map([
  ['/', ['index.html', 'text/html']],
  ['/vnc.html', ['vnc.html', 'text/html']],
  ['/homelab-audio/sidebar.js', ['homelab-audio/sidebar.js', 'text/javascript']],
  ['/homelab-audio/jsmpeg.min.js', ['homelab-audio/jsmpeg.min.js', 'text/javascript']],
]);
let connections = 0;
const server = http.createServer((req, res) => {
  const path = new URL(req.url, 'http://localhost').pathname;
  if (path === '/stats') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ active: relay.clients.size, connections }));
    return;
  }
  const asset = allowed.get(path);
  if (!asset) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': asset[1] });
  res.end(readFileSync(join(webroot, asset[0])));
});
server.on('upgrade', (req, socket, head) => {
  if (req.url !== '/kasm-audio') {
    socket.end('HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n'); return;
  }
  if (mode === 'reject') {
    socket.end('HTTP/1.1 401 Unauthorized\r\nConnection: close\r\n\r\n'); return;
  }
  if (mode === 'hang') {
    socket.on('error', () => {});
    return;
  }
  relay.handleUpgrade(req, socket, head, ws => relay.emit('connection', ws));
});
relay.on('connection', socket => {
  connections++;
  if (mode === 'close') { socket.close(1011, 'Test relay failure'); return; }
  let offset = 0;
  // Deliberately split TS packets across WebSocket messages, like network delivery.
  const timer = setInterval(() => {
    if (socket.readyState !== socket.OPEN) return;
    const end = Math.min(offset + 701, tone.length);
    socket.send(tone.subarray(offset, end));
    offset = end === tone.length ? 0 : end;
  }, 20);
  socket.on('close', () => clearInterval(timer));
});
server.listen(0, '127.0.0.1', () => {
  console.log(JSON.stringify({ url: `http://127.0.0.1:${server.address().port}` }));
});
function close() {
  for (const socket of relay.clients) socket.terminate();
  server.closeAllConnections();
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 200).unref();
}
process.on('SIGTERM', close);
process.on('SIGINT', close);
