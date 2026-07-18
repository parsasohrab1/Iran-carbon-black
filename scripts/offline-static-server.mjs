/**
 * Zero-dependency offline static dashboard server.
 * Serves offline/dashboard and proxies /api + /health to the local gateway.
 * Usage: node scripts/offline-static-server.mjs [gatewayPort] [listenPort]
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..", "offline", "dashboard");
const GATEWAY_PORT = Number(process.argv[2] || process.env.API_GATEWAY_PORT || 18080);
const LISTEN_PORT = Number(process.argv[3] || 5173);
const GATEWAY = `http://127.0.0.1:${GATEWAY_PORT}`;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".woff2": "font/woff2",
  ".woff": "font/woff",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".map": "application/json",
};

function sendFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, {
    "Content-Type": MIME[ext] || "application/octet-stream",
    "Cache-Control": ext === ".html" ? "no-cache" : "public, max-age=86400",
  });
  fs.createReadStream(filePath).pipe(res);
}

function proxy(req, res) {
  const target = new URL(req.url, GATEWAY);
  const headers = { ...req.headers, host: `127.0.0.1:${GATEWAY_PORT}` };
  const upstream = http.request(
    {
      protocol: "http:",
      hostname: "127.0.0.1",
      port: GATEWAY_PORT,
      path: target.pathname + target.search,
      method: req.method,
      headers,
    },
    (up) => {
      res.writeHead(up.statusCode || 502, up.headers);
      up.pipe(res);
    },
  );
  upstream.on("error", (err) => {
    res.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
    res.end(
      JSON.stringify({
        error: "gateway_unreachable",
        message: err.message,
        hint: "Run .\\scripts\\offline-run.ps1 or .\\scripts\\dev-backend.ps1",
        gateway: GATEWAY,
      }),
    );
  });
  req.pipe(upstream);
}

if (!fs.existsSync(path.join(ROOT, "index.html"))) {
  console.error(`[ICB] Missing offline build at ${ROOT}`);
  console.error("Run: .\\scripts\\offline-save.ps1");
  process.exit(1);
}

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
  if (urlPath.startsWith("/api") || urlPath === "/health" || urlPath.startsWith("/health?")) {
    return proxy(req, res);
  }

  let rel = urlPath === "/" ? "/index.html" : urlPath;
  const candidate = path.normalize(path.join(ROOT, rel));
  if (!candidate.startsWith(ROOT)) {
    res.writeHead(403);
    return res.end("Forbidden");
  }

  if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
    return sendFile(res, candidate);
  }

  // SPA fallback
  return sendFile(res, path.join(ROOT, "index.html"));
});

server.listen(LISTEN_PORT, "127.0.0.1", () => {
  console.log(`[ICB] Offline dashboard: http://127.0.0.1:${LISTEN_PORT}`);
  console.log(`[ICB] API proxy        → ${GATEWAY}`);
  console.log(`[ICB] Static root      → ${ROOT}`);
});
