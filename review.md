# GLOW Repository Review — 2026-07-02

An overnight code review of `s:\code\glow`, focused on the MCP server, the
shared-core deployment contract with QUILL, and repo health. Companion log:
`S:\QUILL\review.md` (Parts 1-3) covers the QUILL-side integration work.
Findings are split into **fixed tonight** and **recommended follow-ups**.

---

## 1. Fixed tonight (working tree, not committed)

### 1.1 MCP server could not serve the post-split shared core (the deploy breaker)

**Symptom.** With the current `quill-glow-core` 0.1.1 + `acb-large-print`
8.0.0 wheels installed (the deployment configuration), every `/audit` and
`/report` call failed with HTTP 400:
`'AuditResult' object has no attribute 'critical_count'`. The endpoint tests
passed only when run against the repo *source tree* (which fell back to the
legacy import path) — the classic "works from source, breaks deployed".

**Root cause.** The 8.0.0 shared-core split changed what
`audit_by_extension()` returns: the slim `quill_glow_core.models.AuditResult`
(file_path / score / grade / findings, `slots=True`) instead of the legacy
rich result. Three endpoint paths still assumed the legacy shape:

- `/audit` and `/report` piped the result into
  `acb_large_print.reporter.generate_json_report`, which dereferences
  `result.critical_count`, `high_count`, `total_paragraphs`, and
  `finding.rule.acb_reference` — none of which exist on the contract model.
- `/fix` unpacked a legacy 5-tuple and serialized records via `r.__dict__`,
  which slotted dataclasses do not have.

**Fix** (`glow_mcp_utils.py`, `main.py`):

- New duck-typed adapters — `_finding_to_dict`, `_audit_result_to_dict`,
  `_severity_text` — accept both shapes (enum or string severities, missing
  counts computed from findings, `passed` derived when absent).
- `run_report` keeps the rich bundled reporter for legacy results and renders
  contract results through new JSON / text / accessible-HTML builders
  (`_contract_*_report`; the HTML carries `lang="en"`, headings, and a list —
  it is an accessibility tool, its own reports should pass its own audit).
- `run_fix` now normalizes legacy tuples *and* contract `FixResult` objects
  into one JSON-safe dict; `/fix` returns it directly.
- `/audit` returns a real JSON object instead of a double-encoded JSON string.

### 1.2 `mcp_server/requirements.txt` deployed a server with no backend

It listed `quill-glow-core>=0.1.0` **without** the `[glow]` extra and without
`acb-large-print`, so a fresh pip-based deploy answered every functional
endpoint with "Shared core services unavailable". Now:
`quill-glow-core[glow]>=0.1.1` **plus** `acb-large-print>=8.0.0` — the
explicit backend floor matters because the contract wheel's own extra floor
(`>=3.0.0`) is loose enough for a stale pre-split backend to satisfy the
resolver and leave the engine silently dead (exactly what had happened on
this machine: an editable acb-large-print 7.5.0 from `C:\Users\jeffb\glow`).

### 1.3 Dockerfile installed the shared core from a moving ref

`pip install .../archive/refs/heads/main.zip` builds whatever `main` is that
day — unpinned, unauditable, and the mechanism by which the deployed image
and the endpoints drifted apart. Now pinned to commit
`6fded95d2972e64154b6375d678f2ecd57da177a` (== the v0.1.1 wheel QUILL
vendors), with a comment describing the verify-then-bump upgrade path.
Note: the *live* container at `letitglow.app/mcp` still reports
`shared_core.backend = "unknown"` — it predates the current shared core; the
next image build picks up both the pin and the endpoint fixes.

### 1.4 Invalid CORS configuration

`allow_origins=["*"]` combined with `allow_credentials=True` is spec-invalid
(browsers refuse to honor it) and a credential-leak invitation if any future
endpoint sets cookies. The MCP API is credential-free; `allow_credentials` is
now `False`.

### 1.5 Tests and docs brought up to the real contract

- `tests/test_endpoints.py`: added `/report` (json + text), `/fix` (real
  docx through the real backend, asserting a JSON-safe payload), and
  `/convert` (endpoint plumbing without a pandoc dependency). **8 passed**
  against the installed wheels — the configuration that used to fail.
- `openapi.yaml`: `/health` response now documents the `shared_core`
  telemetry object.
- Ruff: mcp_server is clean (removed an unused import and a shadowed
  re-import in the tests; annotated the two intentionally-late imports).

---

## 2. Recommended follow-ups (not changed tonight)

1. **Legacy reporter quirks.** The live `/audit` response said
   `"passed": false` alongside score 95 / grade A, and
   `"tool": "ACB Large Print Tool vunknown"`. The pass/fail predicate and the
   version discovery in `acb_large_print.reporter` deserve a look — they
   predate the split.
2. **`/fix` leaks a server-local path and leaves the artifact behind.** The
   response's `fixed_file` is a path inside the container's temp dir; the
   fixed file itself is never cleaned up and cannot be fetched by the client.
   Either return the repaired file's bytes (e.g. base64 or a follow-up
   download endpoint) and delete the temp artifact, or document that `/fix`
   is metadata-only.
3. **Broken virtualsenvs.** `S:\code\glow\.venv` points at
   `C:\Users\jeffbis\...\python.exe` (a different user profile — likely
   copied from the server) and cannot run. `web\.venv` is present but was not
   exercised tonight. Rebuild or delete; everything runs fine on the system
   Python 3.13.
4. **Stale editable install (fixed on this machine, worth a doc note).** The
   machine-wide `acb-large-print 7.5.0` editable install from
   `C:\Users\jeffb\glow\desktop` was uninstalled and replaced with the 8.0.0
   wheel; if that old checkout is dead, consider deleting it so nobody
   `pip install -e`'s it again.
5. **Root-directory clutter.** `log.txt`, `debug.log`, `failed-deploy.log`,
   `latest-deploy.log`, `recovery-failed.log`, `failed-job.log`,
   `desktop_pytest.log`, `web_pytest.log`, `pdf.md/html`, `plan5.md`,
   `post_findings.json`, `server.credentials`, `key.txt` sit untracked at the
   repo root. None are committed (checked `git ls-files`) — but
   `server.credentials` and `key.txt` living inside a repo working tree is an
   accident waiting for a `git add -A`. Move secrets out of the tree and add
   explicit `.gitignore` entries for the log/scratch patterns.
6. **Tracked Keycloak fixtures.** `keycloak-users.json` and
   `glow-oidc-client.json` are tracked; a field scan found no
   password/secret/clientSecret keys in them tonight, but dev-realm exports
   drift — consider generating them at setup time instead of tracking them.
7. **MCP `openapi.yaml` `version: 7.2.0` vs repo `VERSION` 8.0.0** — bump
   together in the release process.
8. **`INTEGRATION.md` step numbering** repeats "3." twice; trivial but it is
   the first document an integrator reads.

---

## 3. What was verified

| Check | Result |
|---|---|
| `mcp_server` endpoint tests vs installed wheels | 8 passed |
| `ruff check mcp_server` | clean |
| QUILL GLOW suites after the QUILL-side integration | 45 + 64 passed (see S:\QUILL\review.md) |
| `quill_glow_core` telemetry on this machine | `backend: glow`, release 8.0.0, rules 8.0.0 |
| Live `letitglow.app/mcp/health` | 200 (legacy image; redeploy to pick up fixes) |
| Live `letitglow.app/mcp/audit` (markdown sample) | 200 via legacy fallback path |
| Sensitive files tracked in git | none (`server.credentials`/`key.txt`/`.env` untracked) |

## 4. Change inventory (this repo, uncommitted)

- `mcp_server/glow_mcp_utils.py` — dual-shape adapters + contract report
  builders + normalized `run_fix`.
- `mcp_server/main.py` — `/audit` JSON object response, `/fix` uses the
  normalized dict, CORS credentials off (with rationale comment).
- `mcp_server/requirements.txt` — `[glow]` extra + backend floor pin.
- `mcp_server/Dockerfile` — shared-core install pinned to a commit SHA.
- `mcp_server/openapi.yaml` — `/health` telemetry schema.
- `mcp_server/tests/test_endpoints.py` — 3 new tests; lint cleanup.
