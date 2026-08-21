"""
GLOW MCP Server - Core integration utilities

This module dispatches to the correct GLOW audit, fix, convert, and report logic
based on file format. It is used by the FastAPI endpoints in main.py.

Two result shapes flow through here:

- Legacy ``acb_large_print`` results (pre-8.0.0): rich objects with
  ``critical_count`` / ``high_count`` / severity enums; the bundled reporter
  understands these natively.
- Shared-core contract results (``quill_glow_core.models``): slim, slotted
  dataclasses with string severities and no aggregate counts. The legacy
  reporter cannot render these, so the helpers below duck-type every access
  and build reports from whichever shape arrives.
"""
import base64
from datetime import datetime, timezone
from pathlib import Path
import html as _html
import json
import tempfile
import sys

from acb_large_print.pandoc_converter import convert_to_html, convert_to_docx
from acb_large_print.reporter import generate_json_report, generate_text_report, generate_html_report

SUPPORTED_FORMATS = {"markdown", "md", "docx", "html"}

_SEVERITY_ORDER = ("critical", "high", "medium", "low")


def _severity_text(severity) -> str:
    """A lowercase severity string from either an enum or a plain string."""
    value = getattr(severity, "value", severity)
    return str(value).strip().lower()


def _finding_to_dict(finding) -> dict:
    """JSON-safe view of a finding from either result shape."""
    rule = getattr(finding, "rule", None)
    return {
        "rule_id": str(getattr(finding, "rule_id", "") or ""),
        "severity": _severity_text(getattr(finding, "severity", "") or ""),
        "message": str(getattr(finding, "message", "") or ""),
        "description": str(getattr(finding, "description", "") or ""),
        "location": str(getattr(finding, "location", "") or ""),
        "auto_fixable": bool(getattr(finding, "auto_fixable", False)),
        "reference": str(getattr(rule, "acb_reference", "") or "") if rule is not None else "",
    }


def _is_legacy_audit_result(audit_result) -> bool:
    """True when the result carries the pre-split reporter fields."""
    return hasattr(audit_result, "critical_count")


def _audit_result_to_dict(audit_result) -> dict:
    """JSON-safe audit summary from either result shape."""
    findings = [_finding_to_dict(f) for f in getattr(audit_result, "findings", ()) or ()]
    counts = {name: 0 for name in _SEVERITY_ORDER}
    for item in findings:
        if item["severity"] in counts:
            counts[item["severity"]] += 1
    score = int(getattr(audit_result, "score", 0) or 0)
    passed = bool(getattr(audit_result, "passed", score >= 90 and counts["critical"] == 0))
    return {
        "file": str(getattr(audit_result, "file_path", "") or ""),
        "score": score,
        "grade": str(getattr(audit_result, "grade", "") or ""),
        "passed": passed,
        "summary": {"total": len(findings), **counts},
        "findings": findings,
        "exitCode": 0 if passed else 2,
    }


def _contract_json_report(audit_result) -> str:
    data = {
        "tool": "GLOW MCP Server (shared core)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **_audit_result_to_dict(audit_result),
    }
    return json.dumps(data, indent=2)


def _contract_text_report(audit_result) -> str:
    data = _audit_result_to_dict(audit_result)
    lines = [
        f"GLOW accessibility audit for {data['file']}",
        f"Score: {data['score']} (grade {data['grade']})",
        f"Passed: {'yes' if data['passed'] else 'no'}",
        f"Findings: {data['summary']['total']}",
        "",
    ]
    for index, finding in enumerate(data["findings"], start=1):
        location = f" ({finding['location']})" if finding["location"] else ""
        fixable = " [auto-fix]" if finding["auto_fixable"] else ""
        lines.append(
            f"{index}. [{finding['severity'].upper()}] {finding['rule_id']}{location}{fixable}"
        )
        lines.append(f"   {finding['message']}")
        if finding["description"]:
            lines.append(f"   {finding['description']}")
    return "\n".join(lines).rstrip() + "\n"


def _contract_html_report(audit_result) -> str:
    data = _audit_result_to_dict(audit_result)
    rows = []
    for finding in data["findings"]:
        rows.append(
            "<li>"
            f"<strong>{_html.escape(finding['severity'].upper())}</strong> "
            f"{_html.escape(finding['rule_id'])}: {_html.escape(finding['message'])}"
            + (f" <em>{_html.escape(finding['location'])}</em>" if finding["location"] else "")
            + "</li>"
        )
    body = "".join(rows) or "<li>No findings.</li>"
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        "<title>GLOW accessibility audit</title></head><body>"
        f"<h1>GLOW accessibility audit</h1>"
        f"<p>File: {_html.escape(data['file'])}</p>"
        f"<p>Score: {data['score']} (grade {_html.escape(data['grade'])}). "
        f"Passed: {'yes' if data['passed'] else 'no'}.</p>"
        f"<h2>Findings ({data['summary']['total']})</h2><ul>{body}</ul>"
        "</body></html>"
    )


def _resolve_core_services():
    """Return (audit_by_extension, convert_to_markdown, fix_by_extension).

    Import lazily so module import does not fail in environments where shared
    core packages are not installed but endpoints that need them are not used.
    """
    try:
        from quill_glow_core import audit_by_extension, convert_to_markdown, fix_by_extension

        return audit_by_extension, convert_to_markdown, fix_by_extension
    except Exception:
        try:
            from acb_large_print_core import (
                audit_by_extension,
                convert_to_markdown,
                fix_by_extension,
            )

            return audit_by_extension, convert_to_markdown, fix_by_extension
        except Exception as exc:
            raise RuntimeError(
                "Shared core services unavailable. Install quill-glow-core[glow] or acb-large-print-core."
            ) from exc


def run_page_flow_extract(source_url: str, *, max_pages: int = 5, follow_pagination: bool = True):
    """Extract readable article text from a web URL using PageFlow logic.

    Returns a JSON-serializable dictionary with normalized article details.
    """
    if not source_url or not str(source_url).strip():
        raise ValueError("source_url is required")

    # Prefer direct import when package path is already configured.
    try:
        from acb_large_print_web.listen_later import extract_article, ArticleExtractionError
    except ImportError:
        # Fallback for standalone mcp_server execution: add web/src to path.
        project_root = Path(__file__).resolve().parents[1]
        web_src = project_root / "web" / "src"
        if str(web_src) not in sys.path:
            sys.path.insert(0, str(web_src))
        try:
            from acb_large_print_web.listen_later import extract_article, ArticleExtractionError
        except Exception as exc:
            raise RuntimeError(
                "PageFlow extraction requires web/src/acb_large_print_web to be importable"
            ) from exc

    try:
        article = extract_article(
            str(source_url).strip(),
            max_pages=max(1, int(max_pages)),
            follow_pagination=bool(follow_pagination),
        )
    except ArticleExtractionError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "source_url": article.source_url,
        "final_url": article.final_url,
        "title": article.title,
        "text": article.text,
        "page_urls": list(article.page_urls),
        "page_count": len(article.page_urls),
        "char_count": len(article.text or ""),
    }


def run_audit(file_path: Path, fmt: str):
    """Dispatch to the correct audit function based on format."""
    audit_by_extension, _convert_to_markdown, _fix_by_extension = _resolve_core_services()
    fmt = fmt.lower()
    if fmt in ("markdown", "md", "docx"):
        return audit_by_extension(file_path)
    raise ValueError(f"Unsupported format for audit: {fmt}")


def _attach_fixed_file_bytes(payload: dict, *, delete_artifact: bool) -> dict:
    """Inline the repaired file as base64 and stop leaking server paths.

    The fix backends write the repaired document to a server-local temp path
    that MCP clients can never fetch. Ship the bytes in the response
    (``fixed_file_base64``), reduce ``fixed_file`` to a bare file name, and
    remove the temp artifact when the server chose the output location.
    """
    path = Path(payload.get("fixed_file") or "")
    if path.is_file():
        payload["fixed_file_base64"] = base64.b64encode(path.read_bytes()).decode("ascii")
        payload["fixed_file"] = path.name
        if delete_artifact:
            path.unlink(missing_ok=True)
    else:
        payload["fixed_file_base64"] = ""
        payload["fixed_file"] = path.name
    return payload


def run_fix(file_path: Path, fmt: str, output_path: Path = None) -> dict:
    """Dispatch to the correct fix function and normalize to a JSON-safe dict.

    Legacy backends return a 5-tuple; the shared-core contract returns a
    ``FixResult`` dataclass. Both are normalized here so the endpoint never
    depends on the backend flavor. The repaired document is returned inline
    as ``fixed_file_base64``; when ``output_path`` is None the server-side
    temp artifact is deleted after encoding.
    """
    _audit_by_extension, _convert_to_markdown, fix_by_extension = _resolve_core_services()
    fmt = fmt.lower()
    if fmt != "docx":
        raise ValueError(f"Unsupported format for fix: {fmt}")
    result = fix_by_extension(file_path, output_path=output_path)
    delete_artifact = output_path is None
    if isinstance(result, tuple) and len(result) == 5:
        fixed_path, total_fixes, fix_records, post_fix_audit, warnings = result
        records = [
            record if isinstance(record, dict) else dict(vars(record))
            for record in (fix_records or ())
        ]
        return _attach_fixed_file_bytes(
            {
                "fixed_file": str(fixed_path),
                "total_fixes": int(total_fixes),
                "fix_records": records,
                "post_fix_audit": _audit_result_to_dict(post_fix_audit),
                "warnings": [str(item) for item in (warnings or ())],
            },
            delete_artifact=delete_artifact,
        )
    return _attach_fixed_file_bytes(
        {
            "fixed_file": str(getattr(result, "output_path", "") or ""),
            "total_fixes": int(getattr(result, "total_fixes", 0) or 0),
            "fix_records": [],
            "post_fix_audit": _audit_result_to_dict(getattr(result, "audit_result", None)),
            "warnings": [str(item) for item in getattr(result, "warnings", ()) or ()],
        },
        delete_artifact=delete_artifact,
    )


def run_convert(file_path: Path, from_fmt: str, to_fmt: str, output_path: Path = None):
    """Dispatch to the correct convert function based on formats."""
    _audit_by_extension, convert_to_markdown, _fix_by_extension = _resolve_core_services()
    from_fmt = from_fmt.lower()
    to_fmt = to_fmt.lower()
    if from_fmt == "docx" and to_fmt in ("markdown", "md"):
        return convert_to_markdown(file_path, output_path)
    if from_fmt == "docx" and to_fmt == "html":
        return convert_to_html(file_path, output_path)
    if from_fmt in ("markdown", "md") and to_fmt == "docx":
        return convert_to_docx(file_path, output_path)
    if from_fmt in ("markdown", "md") and to_fmt == "html":
        # Convert markdown to docx, then docx to html
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path, _ = convert_to_docx(file_path, Path(tmpdir) / "temp.docx")
            return convert_to_html(docx_path, output_path)
    raise ValueError(f"Unsupported conversion: {from_fmt} -> {to_fmt}")


def run_report(audit_result, report_type: str = "json"):
    """Generate a report from an AuditResult of either shape.

    Legacy results keep using the bundled reporter (it renders richer
    document stats); shared-core contract results are rendered by the
    duck-typed builders above, because the legacy reporter requires
    aggregate-count attributes the contract model does not carry.
    """
    if report_type not in ("json", "text", "html"):
        raise ValueError(f"Unsupported report type: {report_type}")
    if _is_legacy_audit_result(audit_result):
        if report_type == "json":
            return generate_json_report(audit_result)
        if report_type == "text":
            return generate_text_report(audit_result)
        return generate_html_report(audit_result)
    if report_type == "json":
        return _contract_json_report(audit_result)
    if report_type == "text":
        return _contract_text_report(audit_result)
    return _contract_html_report(audit_result)
