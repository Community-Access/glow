#!/usr/bin/env node

const os = require("node:os");
const path = require("node:path");
const fs = require("node:fs");
const { spawnSync } = require("node:child_process");

const executableName = process.platform === "win32" ? "mkcert.exe" : "mkcert";
const executablePath = path.join(os.homedir(), ".vite-plugin-mkcert", executableName);

if (!fs.existsSync(executablePath)) {
    console.log("No vite-plugin-mkcert installation was found; no local CA was removed.");
    process.exit(0);
}

const result = spawnSync(executablePath, ["-uninstall"], {
    encoding: "utf8",
    windowsHide: true,
});
if (result.error) throw result.error;
if (result.status !== 0) {
    console.error((result.stderr || result.stdout || "mkcert could not remove its local CA.").trim());
    process.exitCode = result.status || 1;
} else {
    console.log("Removed mkcert's shared local CA from the system trust stores. Other local projects using mkcert may need it installed again.");
}
