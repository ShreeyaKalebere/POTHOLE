import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import basicSsl from "@vitejs/plugin-basic-ssl";

// npm run dev        -> http://localhost:5173           (laptop)
// npm run dev:phone  -> https://<laptop-ip>:5173       (phone: camera + GPS need HTTPS)
// /api and /media are forwarded to the FastAPI backend on port 8000
export default defineConfig(({ mode }) => ({
  plugins: [react(), ...(mode === "phone" ? [basicSsl()] : [])],
  server: {
    port: 5173,
    host: true, // reachable from a phone on the same Wi-Fi / hotspot
    proxy: {
      "/api": "http://localhost:8000",
      "/media": "http://localhost:8000",
    },
  },
}));
