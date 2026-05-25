# GLOW MCP Server - Integration Plan

This document describes how the GLOW MCP server integrates with the existing GLOW core logic and Accessibility Agents ecosystem.

## Architecture

- **Framework:** Python FastAPI
- **Endpoints:** /health, /audit, /fix, /convert, /report, /page-flow
- **Integration:**
  - Calls GLOW's Python modules for audit, fix, convert, and reporting
  - Calls GLOW PageFlow extraction logic for URL-to-readable-text workflows
  - Accepts file uploads (Markdown, HTML, DOCX)
  - Returns JSON results (and files for fix/convert)
  - Designed for agent-to-agent and workflow integration

## Implementation Steps

1. Scaffold FastAPI server (done)
2. Integrate GLOW audit/fix/convert/report logic from desktop/src/acb_large_print/
3. Integrate GLOW PageFlow URL extraction from web/src/acb_large_print_web/listen_later.py
3. Implement endpoint logic and error handling
4. Write OpenAPI spec and usage docs (done)
5. Test with Accessibility Agents (markdown-a11y-assistant, etc.)
6. Update CHANGELOG.md and release as 7.2.0+

## Notes
- Only features that make sense for agent integration are exposed
- All endpoints are documented in openapi.yaml and README.md
- Designed for extensibility (future endpoints: template, CSV export, etc.)

---

For questions, see docs/ or contact the maintainers.
