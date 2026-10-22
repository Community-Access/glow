#!/usr/bin/env node

const path = require("node:path");
const webpack = require("webpack");

const projectRoot = path.resolve(__dirname, "..");
const distRoot = path.join(projectRoot, "dist");
const args = process.argv.slice(2);
function optionValue(name, fallback) {
    const index = args.indexOf(name);
    return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
}
const openBrowser = args.includes("--open");
const host = optionValue("--host", "127.0.0.1");
const port = Number(optionValue("--port", "3000"));
if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("--port must be an integer from 1 to 65535.");
}
const baseConfig = require(path.join(projectRoot, "webpack.config.js"));
const config = {
    ...baseConfig,
    mode: "development",
    devtool: "eval-source-map",
};
delete config.devServer;

const compiler = webpack(config);
let viteServer;
let firstBuild = true;
let closing = false;

function close(exitCode = 0) {
    if (closing) return;
    closing = true;
    const closeVite = viteServer ? viteServer.close() : Promise.resolve();
    compiler.close(() => {
        closeVite.finally(() => {
            process.exitCode = exitCode;
        });
    });
}

process.once("SIGINT", () => close());
process.once("SIGTERM", () => close());

compiler.watch({}, async (error, stats) => {
    if (error) {
        console.error(error.stack || error);
        if (firstBuild) close(1);
        return;
    }

    if (stats.hasErrors()) {
        console.error(stats.toString({ all: false, errors: true, colors: true }));
        if (firstBuild) close(1);
        return;
    }

    console.log(stats.toString({
        all: false,
        assets: true,
        colors: true,
        timings: true,
    }));

    if (!viteServer) {
        try {
            const { createServer } = await import("vite");
            viteServer = await createServer({
                configFile: path.join(projectRoot, "vite.config.mjs"),
                root: distRoot,
                server: {
                    host,
                    open: openBrowser ? "/taskpane.html" : false,
                    port,
                    strictPort: true,
                },
            });
            await viteServer.listen();
            viteServer.printUrls();
        } catch (startError) {
            console.error(startError.stack || startError);
            close(1);
        }
    } else {
        viteServer.ws.send({ type: "full-reload", path: "*" });
    }

    firstBuild = false;
});
