/**
 * Version helper for office-addin.
 *
 * The version is injected at build time by webpack's DefinePlugin (see
 * webpack.config.js), sourced from the centralized VERSION file at the
 * repository root. This keeps the add-in version in sync with the desktop and
 * web components without reading the filesystem at runtime -- the add-in runs
 * in a browser task pane where `fs`/`path`/`__dirname` do not exist.
 */

export function getVersion(): string {
  return __APP_VERSION__;
}

export default getVersion();
