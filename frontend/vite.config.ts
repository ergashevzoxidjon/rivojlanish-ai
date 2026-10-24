import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build natijasi to'g'ridan-to'g'ri backend/app/static ga tushadi — FastAPI uni o'zi beradi
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../backend/app/static",
    emptyOutDir: true,
    chunkSizeWarningLimit: 900,
  },
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
