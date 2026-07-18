import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

/** Local offline-friendly dashboard: proxies /api to the Compose gateway. */
export default defineConfig(({ mode }) => {
  // Prefer web/.env* then fall back; gateway port may differ if 8080 is taken.
  const env = loadEnv(mode, process.cwd(), "");
  const parentEnv = loadEnv(mode, `${process.cwd()}/..`, "");
  const gatewayPort = env.API_GATEWAY_PORT || parentEnv.API_GATEWAY_PORT || "18080";
  const gateway = `http://127.0.0.1:${gatewayPort}`;

  const proxy = {
    "/api": { target: gateway, changeOrigin: true, secure: false },
    "/health": { target: gateway, changeOrigin: true, secure: false },
  };

  return {
    plugins: [react()],
    // Fully local assets; no remote font/CDN fetches at runtime
    base: "/",
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      open: false,
      proxy,
    },
    preview: {
      host: "127.0.0.1",
      port: 4173,
      strictPort: true,
      proxy,
    },
    build: {
      outDir: "dist",
      assetsDir: "assets",
      sourcemap: false,
      emptyOutDir: true,
    },
  };
});
