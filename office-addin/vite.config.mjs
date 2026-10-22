import { defineConfig } from "vite";
import mkcert from "vite-plugin-mkcert";

const useHttp = process.env.GLOW_OFFICE_DEV_HTTP === "1";

export default defineConfig({
    appType: "mpa",
    plugins: useHttp ? [] : [mkcert({ hosts: ["localhost"] })],
    server: {
        host: "127.0.0.1",
        port: 3000,
        strictPort: true,
        https: useHttp ? undefined : {},
        headers: {
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store",
        },
    },
});
