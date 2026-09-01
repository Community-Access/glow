declare module "*.css";

// Injected at build time by webpack DefinePlugin (see webpack.config.js),
// sourced from the repo-root VERSION file so the add-in stays in sync with
// the desktop and web components without reading the filesystem at runtime.
declare const __APP_VERSION__: string;
