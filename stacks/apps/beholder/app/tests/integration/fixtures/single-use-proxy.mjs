import http from "node:http";

// Forwards the first request per connection; reusing it finds it closed.
export async function startSingleUseProxy(target) {
  const used = new WeakSet();
  const server = http.createServer((req, res) => {
    if (used.has(req.socket)) {
      req.socket.destroy();
      return;
    }
    used.add(req.socket);
    const upstream = http.request(
      new URL(req.url, target),
      { method: req.method, headers: req.headers },
      (reply) => {
        res.writeHead(reply.statusCode, reply.headers);
        reply.pipe(res);
      },
    );
    req.pipe(upstream);
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return {
    url: `http://127.0.0.1:${server.address().port}`,
    stop: () => new Promise((resolve) => server.close(resolve)),
  };
}
