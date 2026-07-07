import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev-only proxy so the frontend can call relative /dashboard/* URLs without
// CORS -- points at the FastAPI backend (uvicorn main:app, default port 8000).
// Override with VITE_API_PROXY_TARGET if the backend runs elsewhere.
const apiTarget = process.env.VITE_API_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/dashboard": {
        target: apiTarget,
        changeOrigin: true,
      },
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
