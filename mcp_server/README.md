# GLOW MCP Server

This server exposes GLOW's accessibility audit, fix, convert, and reporting features via a Model Context Protocol (MCP) API for integration with Accessibility Agents and other tools.


## Endpoints

- `GET /health` — Health check
- `POST /audit` — Audit a document (Markdown, HTML, DOCX). Returns a JSON audit report.
- `POST /fix` — Auto-fix accessibility issues (DOCX only). Returns fixed file path, fix records, and post-fix audit.
- `POST /convert` — Convert between formats (Markdown, HTML, DOCX). Returns output file path and converted text.
- `POST /report` — Generate accessibility reports (JSON, text, or HTML) from a document. Returns the report as a string.
- `POST /page-flow` — Extract readable article text from a web URL. Returns normalized text, title, page URLs, and counts.


## Usage

Run the server:

```bash
uvicorn mcp_server.main:app --reload --host 0.0.0.0 --port 8000
```

### Example: Audit a Markdown file

```bash
curl -F "file=@example.md" -F "format=markdown" http://localhost:8000/audit
```

### Example: Fix a DOCX file

```bash
curl -F "file=@example.docx" -F "format=docx" http://localhost:8000/fix
```

### Example: Convert DOCX to Markdown

```bash
curl -F "file=@example.docx" -F "from_format=docx" -F "to_format=markdown" http://localhost:8000/convert
```

### Example: Generate HTML report

```bash
curl -F "file=@example.docx" -F "format=docx" -F "report_type=html" http://localhost:8000/report
```

### Example: Extract article text with PageFlow

```bash
curl -F "source_url=https://www.macstories.net/stories/macos-monterey-the-macstories-review/" \
	-F "max_pages=5" \
	-F "follow_pagination=true" \
	http://localhost:8000/page-flow
```


## Integration

- Designed for agent-to-agent and workflow integration (e.g., Accessibility Agents, markdown-a11y-assistant)
- Accepts file uploads and format parameters
- Returns JSON results (and files for conversion/fix endpoints)
- All endpoints are CORS-enabled for easy integration


## Implementation Notes

- Core logic is delegated to GLOW's Python modules (audit, fix, convert, report)
- Only features that make sense for agent integration are exposed
- See `openapi.yaml` for full API schema
- All endpoints are documented and return clear error messages on failure

## TODO

- Add authentication if needed
- Add more formats and advanced options as needed
- Add tests and examples

---

© 2026 Community Access. See LICENSE.txt.
