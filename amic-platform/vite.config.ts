import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { sentryVitePlugin } from "@sentry/vite-plugin";
import path from "path";
import { readFileSync } from "fs";

const pkg = JSON.parse(
  readFileSync(path.resolve(__dirname, "package.json"), "utf-8"),
);

function readEnvVar(
  env: Record<string, string>,
  name: string,
  fallback: string,
): string {
  const value = env[name]?.trim();
  return value && value.length > 0 ? value : fallback;
}

function joinUrlPath(base: string, segment: string): string {
  return `${base.replace(/\/+$/, "")}/${segment.replace(/^\/+/, "")}`;
}

function rewriteProxySetCookieHeader(
  setCookieHeader: string | string[] | undefined,
): string[] | undefined {
  if (!setCookieHeader) {
    return undefined;
  }

  const cookies = Array.isArray(setCookieHeader)
    ? setCookieHeader
    : [setCookieHeader];

  return cookies.map((cookie) =>
    cookie
      .replace(/;\s*secure/gi, "")
      .replace(/;\s*domain=[^;]+/gi, ""),
  );
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, "");
  const DEFAULT_API_PROXY_TARGET = readEnvVar(
    env,
    "VITE_API_PROXY_TARGET",
    "https://52.231.69.38",
  );
  const RAW_FDD_API_PROXY_TARGET = env.VITE_FDD_API_PROXY_TARGET?.trim();
  const RAW_MA_API_PROXY_TARGET = env.VITE_MA_API_PROXY_TARGET?.trim();
  const FDD_API_PROXY_TARGET = readEnvVar(
    env,
    "VITE_FDD_API_PROXY_TARGET",
    DEFAULT_API_PROXY_TARGET,
  );
  const FDD_AUTH_PROXY_TARGET = readEnvVar(
    env,
    "VITE_FDD_AUTH_PROXY_TARGET",
    RAW_FDD_API_PROXY_TARGET
      ? joinUrlPath(FDD_API_PROXY_TARGET, "auth")
      : joinUrlPath(DEFAULT_API_PROXY_TARGET, "api/fdd/auth"),
  );
  const MA_API_PROXY_TARGET = readEnvVar(
    env,
    "VITE_MA_API_PROXY_TARGET",
    joinUrlPath(DEFAULT_API_PROXY_TARGET, "api/ma"),
  );

  return {
    define: {
      __APP_VERSION__: JSON.stringify(pkg.version),
    },
    build: {
      sourcemap: true,
      chunkSizeWarningLimit: 2000,
      rollupOptions: {
        output: {
          manualChunks: {
            "react-vendor": ["react", "react-dom", "react-router-dom"],
            "query-vendor": ["@tanstack/react-query"],
            "chart-vendor": ["recharts"],
            "excalidraw-vendor": ["@excalidraw/excalidraw"],
            "tiptap-vendor": [
              "@tiptap/react",
              "@tiptap/starter-kit",
              "@tiptap/extension-table",
              "@tiptap/extension-table-cell",
              "@tiptap/extension-table-header",
              "@tiptap/extension-table-row",
              "@tiptap/extension-placeholder",
            ],
          },
        },
      },
    },
    plugins: [
      react(),
      env.SENTRY_AUTH_TOKEN
        ? sentryVitePlugin({
            org: env.SENTRY_ORG,
            project: env.SENTRY_PROJECT,
            authToken: env.SENTRY_AUTH_TOKEN,
          })
        : null,
    ].filter(Boolean),
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      host: true,
      watch: {
        usePolling: true,
        interval: 1000,
      },
      proxy: {
        "/api/ma/health": {
          target: MA_API_PROXY_TARGET,
          changeOrigin: true,
          secure: false,
          rewrite: () => "/health",
        },
        "/api/fdd/auth": {
          target: FDD_AUTH_PROXY_TARGET,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api\/fdd\/auth/, "") || "/",
          configure: (proxy) => {
            proxy.on("proxyRes", (proxyRes) => {
              proxyRes.headers["set-cookie"] = rewriteProxySetCookieHeader(
                proxyRes.headers["set-cookie"],
              );
            });
          },
        },
        "/api/fdd": {
          target: FDD_API_PROXY_TARGET,
          changeOrigin: true,
          secure: false,
          configure: (proxy) => {
            proxy.on("proxyRes", (proxyRes) => {
              proxyRes.headers["set-cookie"] = rewriteProxySetCookieHeader(
                proxyRes.headers["set-cookie"],
              );
            });
          },
        },
        "/api/ma": {
          target: MA_API_PROXY_TARGET,
          changeOrigin: true,
          secure: false,
          rewrite: (path) =>
            RAW_MA_API_PROXY_TARGET
              ? path.replace(/^\/api\/ma/, "/api/v1")
              : path.replace(/^\/api\/ma/, "") || "/",
        },
        "/api": {
          target: DEFAULT_API_PROXY_TARGET,
          changeOrigin: true,
          secure: false,
          configure: (proxy) => {
            proxy.on("proxyRes", (proxyRes) => {
              proxyRes.headers["set-cookie"] = rewriteProxySetCookieHeader(
                proxyRes.headers["set-cookie"],
              );
            });
          },
        },
      },
    },
  };
});
