import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// Read backend URL from env in production
const backendUrl = process.env.VITE_API_URL || "http://127.0.0.1:8000";

export default defineConfig(({ command }) => ({
  server: {
    host: "127.0.0.1", // Force IPv4
    port: 3000,
    proxy:
      command === "serve"
        ? {
            "/api": {
              target: backendUrl, // FastAPI backend
              changeOrigin: true,
              secure: false,
            },
          }
        : undefined, // no proxy in build
  },
  build: {
    outDir: "dist",
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./client"),
    },
  },
}));
