import path from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const projectRoot = process.cwd();
const srcRoot = path.join(projectRoot, "src");
const testSetupFile = path.join(projectRoot, "src", "test", "setup.ts");

export default defineConfig({
  root: projectRoot,
  plugins: [react()],
  resolve: {
    preserveSymlinks: true,
    alias: {
      "@": srcRoot,
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: [testSetupFile],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/test/**",
        "src/main.tsx",
        "src/vite-env.d.ts",
        "**/*.d.ts",
      ],
    },
  },
});
