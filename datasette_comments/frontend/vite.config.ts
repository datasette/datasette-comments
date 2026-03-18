import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

export default defineConfig({
  server: {
    port: 5179,
    strictPort: true,
    cors: true,
    hmr: {
      host: "localhost",
      port: 5179,
      protocol: "ws",
    },
  },
  plugins: [preact()],
  build: {
    manifest: "manifest.json",
    outDir: "../",
    assetsDir: "static/gen",
    rollupOptions: {
      input: {
        activity: "src/pages/activity/index.tsx",
        content_script: "src/content_script/index.tsx",
      },
    },
  },
});
