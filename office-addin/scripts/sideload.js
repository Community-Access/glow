#!/usr/bin/env node

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { randomUUID } = require("node:crypto");
const { spawnSync } = require("node:child_process");
const AdmZip = require("adm-zip");

const projectRoot = path.resolve(__dirname, "..");
const manifestPath = path.join(projectRoot, "manifest.xml");
const templatePath = path.join(__dirname, "templates", "WordDocumentWithTaskPane.docx");
const developerKey = "HKCU\\SOFTWARE\\Microsoft\\Office\\16.0\\Wef\\Developer";
const generatedDirectory = path.join(os.tmpdir(), "glow-office-addin-sideload");
let generatedDocument;

function printHelp() {
    console.log(`Usage: node scripts/sideload.js <start|stop|--help>

start  Register manifest.xml for local Word development and open a test document.
       Add --document <path> to open an existing document instead.
stop   Remove this manifest from the local Word development registration.

Run npm run dev in another terminal first. Local HTTPS is provided by Vite and
vite-plugin-mkcert. This command supports Windows and macOS desktop Word.`);
}

function readManifestIdentity() {
    const xml = fs.readFileSync(manifestPath, "utf8");
    const tag = (name) => {
        const match = xml.match(new RegExp(`<${name}\\b[^>]*>([^<]+)<\\/${name}\\s*>`, "i"));
        if (!match) throw new Error(`manifest.xml is missing <${name}>.`);
        return match[1].trim();
    };

    const id = tag("Id");
    const version = tag("Version");
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
        throw new Error("manifest.xml contains an invalid add-in ID.");
    }
    if (!/^\d+(?:\.\d+){2,3}$/.test(version)) {
        throw new Error(`Unsupported manifest version: ${version}`);
    }
    if (!/<Host\s+Name="Document"\s*\/>/i.test(xml)) {
        throw new Error("manifest.xml does not declare the Word Document host.");
    }
    return { id, version };
}

function run(command, args) {
    const result = spawnSync(command, args, { encoding: "utf8", windowsHide: true });
    if (result.error) throw result.error;
    if (result.status !== 0) {
        throw new Error((result.stderr || result.stdout || `${command} failed`).trim());
    }
}

function macSideloadPath(id) {
    return path.join(os.homedir(), "Library/Containers/com.microsoft.Word/Data/Documents/wef", `${id}.manifest.xml`);
}

function register(id) {
    if (process.platform === "win32") {
        run("reg.exe", ["add", developerKey, "/v", id, "/t", "REG_SZ", "/d", manifestPath, "/f"]);
        return;
    }
    if (process.platform === "darwin") {
        const destination = macSideloadPath(id);
        fs.mkdirSync(path.dirname(destination), { recursive: true });
        fs.copyFileSync(manifestPath, destination);
        return;
    }
    throw new Error("Desktop Word sideload is supported here on Windows and macOS only.");
}

function unregister(id) {
    if (process.platform === "win32") {
        const query = spawnSync("reg.exe", ["query", developerKey, "/v", id], {
            encoding: "utf8",
            windowsHide: true,
        });
        if (query.error) throw query.error;
        if (query.status === 0) run("reg.exe", ["delete", developerKey, "/v", id, "/f"]);
        return;
    }
    if (process.platform === "darwin") {
        fs.rmSync(macSideloadPath(id), { force: true });
        return;
    }
    throw new Error("Desktop Word sideload is supported here on Windows and macOS only.");
}

function createSideloadDocument({ id, version }) {
    if (!fs.existsSync(templatePath)) throw new Error("The Word sideload document template is missing.");
    fs.mkdirSync(generatedDirectory, { recursive: true });
    generatedDocument = path.join(generatedDirectory, `${id}-${randomUUID()}.docx`);
    const zip = new AdmZip(templatePath);
    const entryName = "word/webextensions/webextension.xml";
    const entry = zip.getEntry(entryName);
    if (!entry) throw new Error("The Word sideload template is missing its web extension entry.");
    const extensionXml = zip.readAsText(entry)
        .replaceAll("00000000-0000-0000-0000-000000000000", id)
        .replaceAll("1.0.0.0", version);
    zip.updateFile(entryName, Buffer.from(extensionXml, "utf8"));
    zip.writeZip(generatedDocument);
}

function openDocument(documentPath) {
    if (process.platform === "win32") {
        run("powershell.exe", [
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            path.join(__dirname, "open-document.ps1"),
            "-Path",
            documentPath,
        ]);
    } else if (process.platform === "darwin") {
        run("open", [documentPath]);
    }
}

async function main() {
    const action = process.argv[2];
    if (!action || action === "--help" || action === "-h") {
        printHelp();
        return;
    }
    if (action !== "start" && action !== "stop") throw new Error(`Unknown command: ${action}`);

    const documentIndex = process.argv.indexOf("--document", 3);
    const requestedDocument = documentIndex >= 0 ? process.argv[documentIndex + 1] : undefined;
    if (documentIndex >= 0 && !requestedDocument) throw new Error("--document requires a file path.");
    if (requestedDocument && !fs.existsSync(path.resolve(requestedDocument))) {
        throw new Error(`Document not found: ${requestedDocument}`);
    }

    const { id, version } = readManifestIdentity();
    if (action === "stop") {
        unregister(id);
        if (fs.existsSync(generatedDirectory)) {
            for (const name of fs.readdirSync(generatedDirectory)) {
                if (!name.startsWith(`${id}-`) || !name.endsWith(".docx")) continue;
                try {
                    fs.rmSync(path.join(generatedDirectory, name), { force: true });
                } catch (error) {
                    if (error.code !== "EBUSY" && error.code !== "EPERM") throw error;
                    console.warn(`Close Word to remove its temporary sideload document: ${name}`);
                }
            }
        }
        console.log("Removed the local Word add-in registration.");
        return;
    }

    const documentPath = requestedDocument ? path.resolve(requestedDocument) : generatedDocument;
    if (!requestedDocument) createSideloadDocument({ id, version });
    register(id);
    openDocument(documentPath);
    console.log(`Registered ${id} for local Word development and opened ${path.basename(documentPath)}.`);
}

main().catch((error) => {
    console.error(error.message || error);
    process.exitCode = 1;
});
