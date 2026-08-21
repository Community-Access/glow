"""
GLOW MCP Server - FastAPI entrypoint

This server exposes GLOW's accessibility audit, fix, convert, and reporting features via a Model Context Protocol (MCP) API for integration with Accessibility Agents and other tools.

Endpoints:
- /health: Health check
- /audit: Audit a document (Markdown, HTML, DOCX)
- /fix: Auto-fix accessibility issues
- /convert: Convert between formats (Markdown, HTML, DOCX)
- /report: Generate accessibility reports
- /page-flow: Extract readable article text from a web URL

See README.md and openapi.yaml for full documentation.
"""


from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
from pathlib import Path
try:
    from .glow_mcp_utils import run_audit, run_report, run_page_flow_extract
except ImportError:  # Support direct module execution in tests.
    from glow_mcp_utils import run_audit, run_report, run_page_flow_extract

try:
    from quill_glow_core import (
        configure_default_services as _configure_shared_core_default,
        get_startup_telemetry_dict as _get_shared_core_startup_telemetry,
    )
except Exception:
    _configure_shared_core_default = None

    def _get_shared_core_startup_telemetry() -> dict:
        return {
            "backend": "unknown",
            "configured_by": "unknown",
            "auto_selected": None,
        }

if _configure_shared_core_default is not None:
    try:
        _configure_shared_core_default()
    except Exception:
        pass

app = FastAPI(title="GLOW MCP Server", description="Accessibility audit/fix/convert/report API for agent integration.", version="8.0.0")

# Wildcard origins with allow_credentials=True is an invalid (and unsafe) CORS
# combination — browsers reject it and it invites credential leakage if a
# future endpoint ever sets cookies. The MCP API is token/credential-free, so
# credentials stay off.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "shared_core": _get_shared_core_startup_telemetry(),
    }


@app.post("/audit")
async def audit(file: UploadFile = File(...), format: str = Form(...)):
    """Audit a document for accessibility issues."""
    # Save uploaded file to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = Path(tmp.name)
    try:
        audit_result = run_audit(tmp_path, format)
        report_json = run_report(audit_result, report_type="json")
        # run_report returns a JSON string; deliver a real JSON object so
        # clients are not forced to double-decode.
        import json as _json
        return JSONResponse(content=_json.loads(report_json))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/fix")
async def fix(file: UploadFile = File(...), format: str = Form(...)):
    """Auto-fix accessibility issues in a document."""
    try:
        from .glow_mcp_utils import run_fix
    except ImportError:
        from glow_mcp_utils import run_fix
    import tempfile
    from pathlib import Path
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = Path(tmp.name)
    try:
        # run_fix normalizes legacy tuples and shared-core FixResult objects
        # into one JSON-safe dict (slotted contract dataclasses have no
        # __dict__, so serialization happens inside glow_mcp_utils). The
        # repaired document ships inline as fixed_file_base64; the server-side
        # temp artifact is deleted there.
        return JSONResponse(run_fix(tmp_path, format))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/convert")
async def convert(file: UploadFile = File(...), from_format: str = Form(...), to_format: str = Form(...)):
    """Convert a document between supported formats."""
    try:
        from .glow_mcp_utils import run_convert
    except ImportError:
        from glow_mcp_utils import run_convert
    import tempfile
    from pathlib import Path
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = Path(tmp.name)
    try:
        output_path, converted_text = run_convert(tmp_path, from_format, to_format)
        return JSONResponse({
            "output_file": str(output_path),
            "converted_text": converted_text
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/report")
async def report(file: UploadFile = File(...), format: str = Form(...), report_type: str = Form("json")):
    """Generate a detailed accessibility report."""
    try:
        from .glow_mcp_utils import run_audit, run_report
    except ImportError:
        from glow_mcp_utils import run_audit, run_report
    import tempfile
    from pathlib import Path
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = Path(tmp.name)
    try:
        audit_result = run_audit(tmp_path, format)
        report = run_report(audit_result, report_type=report_type)
        return JSONResponse({"report": report})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/page-flow")
async def page_flow_extract(
    source_url: str = Form(...),
    max_pages: int = Form(5),
    follow_pagination: bool = Form(True),
):
    """Extract readable article text from a web page URL.

    This endpoint mirrors GLOW PageFlow extraction behavior for MCP clients.
    """
    try:
        result = run_page_flow_extract(
            source_url,
            max_pages=max_pages,
            follow_pagination=follow_pagination,
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
