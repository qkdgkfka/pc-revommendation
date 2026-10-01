import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    proxy: {
      "/api": { target: "http://127.0.0.1:4000", changeOrigin: false },
      "/health": { target: "http://127.0.0.1:4000", changeOrigin: false },
    },
  },
  build: {
    target: "es2022",
    minify: true,
    cssMinify: true,
    sourcemap: false,
    assetsDir: "assets",
  },
});
