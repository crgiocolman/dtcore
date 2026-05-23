import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import mkcert from "vite-plugin-mkcert";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    mkcert(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "DTCore",
        short_name: "DTCore",
        theme_color: "#ffffff",
        icons: [],
      },
    }),
  ],
  server: { https: true },
});
