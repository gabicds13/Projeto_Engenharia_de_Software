/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// O portal (5173) conversa com o BFF (8006). Em dev, encaminhamos /api e /ws
// para o BFF, evitando problemas de CORS e deixando a URL base relativa.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8006", changeOrigin: true },
      "/ws": { target: "ws://localhost:8006", ws: true },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
