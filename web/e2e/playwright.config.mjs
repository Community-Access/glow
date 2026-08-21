import { defineConfig } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Serve the checkout, not whatever `python` happens to resolve to. A stale
// editable install elsewhere on the machine will shadow web/src, and the
// suite would then audit code that is not in this repository. Prefer the
// project virtualenv; fall back to PATH (CI installs into the job's env).
const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const venvPython = process.platform === 'win32'
  ? path.join(webRoot, '.venv', 'Scripts', 'python.exe')
  : path.join(webRoot, '.venv', 'bin', 'python');
const python = process.env.E2E_PYTHON
  || (fs.existsSync(venvPython) ? venvPython : 'python');

const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5100';
const port = process.env.E2E_PORT || '5100';
const automationConsentToken = process.env.GLOW_AUTOMATION_CONSENT_TOKEN || 'GLOW';

export default defineConfig({
  testDir: './tests',
  timeout: 90000,
  expect: {
    timeout: 15000,
  },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'artifacts/html-report' }],
    ['json', { outputFile: 'artifacts/results.json' }],
    ['junit', { outputFile: 'artifacts/junit.xml' }],
  ],
  use: {
    baseURL,
    extraHTTPHeaders: {
      'X-GLOW-Automation-Consent': automationConsentToken,
    },
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: {
    command: `"${python}" -m flask --app acb_large_print_web.app:create_app run --no-debugger --no-reload --port ${port}`,
    url: `${baseURL}/health`,
    env: {
      ...process.env,
      GLOW_BYPASS_CONSENT_FOR_AUTOMATION: process.env.GLOW_BYPASS_CONSENT_FOR_AUTOMATION || '1',
      GLOW_ENABLE_AUTOMATION_CONSENT_ENDPOINT: process.env.GLOW_ENABLE_AUTOMATION_CONSENT_ENDPOINT || '1',
      GLOW_AUTOMATION_CONSENT_TOKEN: automationConsentToken,
    },
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});