/* eslint-disable @typescript-eslint/no-var-requires */
const fs = require("fs");
const path = require("path");
const webpack = require("webpack");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const CopyWebpackPlugin = require("copy-webpack-plugin");

const isProduction = process.env.NODE_ENV === "production";

// Resolve the add-in version at build time from the repo-root VERSION file so
// it stays in sync with the desktop and web components. Fall back to this
// package's version, then a hard-coded default, so a build never fails on a
// missing file. Injected into the bundle via DefinePlugin (see below).
function resolveAppVersion() {
    try {
        return fs.readFileSync(path.resolve(__dirname, "../VERSION"), "utf-8").trim();
    } catch (e) {
        try {
            return require("./package.json").version || "0.0.0";
        } catch (e2) {
            return "0.0.0";
        }
    }
}

const appVersion = resolveAppVersion();

module.exports = {
    entry: {
        taskpane: "./src/taskpane.ts",
        commands: "./src/commands.ts",
    },
    output: {
        filename: "[name].js",
        path: path.resolve(__dirname, "dist"),
        clean: true,
    },
    resolve: {
        extensions: [".ts", ".js"],
    },
    module: {
        rules: [
            {
                test: /\.ts$/,
                use: "ts-loader",
                exclude: /node_modules/,
            },
            {
                test: /\.css$/,
                use: ["style-loader", "css-loader"],
            },
        ],
    },
    plugins: [
        new webpack.DefinePlugin({
            __APP_VERSION__: JSON.stringify(appVersion),
        }),
        new HtmlWebpackPlugin({
            template: "./src/taskpane.html",
            filename: "taskpane.html",
            chunks: ["taskpane"],
        }),
        new HtmlWebpackPlugin({
            template: "./src/commands.html",
            filename: "commands.html",
            chunks: ["commands"],
        }),
        new CopyWebpackPlugin({
            patterns: [
                {
                    from: "assets",
                    to: "assets",
                    noErrorOnMissing: true,
                },
            ],
        }),
    ],
    devServer: {
        static: path.resolve(__dirname, "dist"),
        port: 3000,
        https: true, // Office add-ins require HTTPS
        headers: {
            "Access-Control-Allow-Origin": "*",
        },
    },
    devtool: isProduction ? "source-map" : "eval-source-map",
};
