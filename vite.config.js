import { defineConfig } from "vite";
import webfontDownload from "vite-plugin-webfont-dl";

export default defineConfig({
    root: "tablo_legacy_m3u/static/src",
    base: "/static/dist/",
    build: {
        outDir: "../dist",
        emptyOutDir: true,
        manifest: true,
        rollupOptions: {
            input: "main.js",
            treeshake: {
                moduleSideEffects: true,
            },
            // HTMX uses eval() in a way that Vite's default warning handler doesn't recognize as safe
            onwarn(warning, warn) {
                if (warning.code === "EVAL" && warning.id?.includes("htmx")) return;
                warn(warning);
            },
        },
    },
    plugins: [
        webfontDownload([
            "https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap",
        ]),
    ],
});
