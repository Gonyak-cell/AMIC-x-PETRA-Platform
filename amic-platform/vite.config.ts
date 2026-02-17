import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { sentryVitePlugin } from "@sentry/vite-plugin";
import path from "path";

export default defineConfig({
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          "query-vendor": ["@tanstack/react-query"],
          "chart-vendor": ["recharts"],
        },
      },
    },
  },
  plugins: [
    react(),
    process.env.SENTRY_AUTH_TOKEN
      ? sentryVitePlugin({
          org: process.env.SENTRY_ORG,
          project: process.env.SENTRY_PROJECT,
          authToken: process.env.SENTRY_AUTH_TOKEN,
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
      // Health 전용 프록시 (루트 /health로 리라이트)
      "/api/fdd/health": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: () => "/health",
      },
      "/api/kiis/health": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: () => "/health",
      },
      "/api/im/health": {
        target: "http://localhost:8002",
        changeOrigin: true,
        rewrite: () => "/health",
      },
      // 범용 API 프록시
      "/api/fdd": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/fdd/, "/api/v1"),
      },
      "/api/kiis": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/kiis/, "/api/v1"),
      },
      "/api/im": {
        target: "http://localhost:8002",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/im/, "/api/v1"),
      },
    },
  },
});
