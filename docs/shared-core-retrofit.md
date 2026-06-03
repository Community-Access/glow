# Shared Core Retrofit Plan and Status

## Goal

Retrofit GLOW so desktop CLI, desktop GUI, and web routes use a shared internal service layer for document audit/fix/convert dispatch, preparing extraction into a standalone cross-product core.

## Implemented in this retrofit

## 1) Shared package introduced

- Added `desktop/src/acb_large_print_core/` with:
  - `services.py`: canonical extension-based dispatch for audit/fix/convert
  - `versions.py`: normalized component-version manifest for diagnostics
  - `__init__.py`: exported core APIs

## 2) Desktop CLI wired to shared services

- `acb_large_print.cli` now routes audit/fix/convert dispatch through:
  - `acb_large_print_core.services.audit_by_extension`
  - `acb_large_print_core.services.fix_by_extension`
  - `acb_large_print_core.services.convert_to_markdown`

## 3) Web routes/tasks wired to shared services

- `routes/audit.py` now uses shared `audit_by_extension`.
- `routes/fix.py` now uses shared `audit_by_extension` + `fix_by_extension`.
- `routes/convert.py`, `upload.py`, `routes/speech.py`, and `magic_features.py` now use shared conversion entry points.
- `tasks/convert_tasks.py` now uses shared audit/markdown conversion dispatch.
- `chat_handler.py` now routes live audit via shared `audit_by_extension`.

## 4) Version-provenance plumbing

- Added `acb_large_print_core.versions.get_component_versions()`.
- Web template context now includes `component_versions` for About/support surfaces.
- Desktop package `acb_large_print.__version__` now resolves from repository `VERSION` file.

## 5) MCP server wiring

- `mcp_server/glow_mcp_utils.py` now dispatches docx/markdown audit, docx fix, and markdown conversion via `acb_large_print_core.services`.

## Contract surface (internal v1)

Use these as canonical internal service contracts:

- `audit_by_extension(path, **policy_overrides) -> AuditResult`
- `fix_by_extension(path, output_path=None, **fix_options) -> tuple`
- `convert_to_markdown(path, output_path=None) -> tuple[Path, str]`
- `get_component_versions() -> dict[str, str]`

## Next extraction step

When ready to externalize for QUILL integration:

1. Move `acb_large_print_core` to its own package/repo.
2. Preserve function signatures and return types.
3. Keep thin adapter modules in GLOW (`acb_large_print`) to prevent breaking consumers.
4. Add semver and compatibility matrix (`glow_min`, `quill_min`) to version manifest.

## Server deployment readiness checklist (for PR review and rollout)

Use this checklist before promoting `feature/shared-core-retrofit` to production:

1. **Branch + PR readiness**
   - Confirm PR #81 is approved and mergeable.
   - Confirm deployment target references the merged commit SHA (not a stale image/revision).

2. **Build/runtime alignment**
   - Rebuild application image/environment from the merged commit.
   - Verify runtime imports resolve to repository source used in deployment (avoid stale site-packages path drift).

3. **Automated verification gates**
   - Desktop targeted checks:
     - `python -m pytest tests/test_conversion_format_support.py tests/test_pdf_table_extraction.py -q`
   - Web targeted checks:
     - `python -m pytest tests/test_upload.py tests/test_fix_routes.py -q`
   - Version surface checks (from repo root with source paths):
     - `PYTHONPATH=desktop/src;web/src python -m pytest web/tests/test_app.py -k release_from_version_file -q`

4. **Runtime smoke tests (staging first)**
   - Audit flow works for `.docx`, `.md`, `.pdf`.
   - Fix flow works for `.docx`; advisory/manual paths remain correct for unsupported auto-fix formats.
   - Convert flow produces markdown via shared service dispatch.
   - Chat audit summary still functions.
   - MCP utility endpoints still run docx/markdown audit/fix/convert paths.

5. **Observability + metadata**
   - About page renders component versions (`release`, `markitdown`, `pymupdf`, core package).
   - Logs show no import-dispatch errors for `acb_large_print_core`.

6. **Rollout strategy**
   - Deploy to staging.
   - Run smoke checks above.
   - Promote to production.
   - Monitor first 24h for audit/fix/convert error-rate regressions.
