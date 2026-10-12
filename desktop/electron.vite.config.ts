import { resolve } from "node:path";
import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  main: { build: { lib: { entry: resolve(__dirname, "electron/main.ts") } }, plugins: [externalizeDepsPlugin()] },
  preload: { build: { lib: { entry: resolve(__dirname, "electron/preload.ts") } }, plugins: [externalizeDepsPlugin()] },
  renderer: {
    root: resolve(__dirname, "renderer"),
    build: { rollupOptions: { input: resolve(__dirname, "renderer/index.html") } },
    resolve: { alias: { "@renderer": resolve(__dirname, "renderer/src") } },
    plugins: [react()],
  },
});
