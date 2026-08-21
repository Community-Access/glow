"""Postmark email integration for GLOW audit report delivery.

Sends audit results (scorecard + findings CSV attachment) to a user-provided
email address via the Postmark transactional email API.

Configuration (environment variables):
  POSTMARK_SERVER_TOKEN  -- Postmark server API token (required to send)
  POSTMARK_FROM_EMAIL    -- Sender address (default: no-reply@notify.letitglow.app)

If POSTMARK_SERVER_TOKEN is not set, send attempts are skipped and callers
receive (False, "Email service not configured") rather than raising.

Error handling follows Postmark Skills guidance:
  200   -- success
  400   -- bad request (user/config error) -- do not retry
  401   -- authentication failure -- do not retry
  422   -- validation error (template/field issue) -- do not retry
  429   -- rate limited -- caller should surface "try again" message
  5xx   -- server error -- transient, caller can retry later
  Timeout -- Postmark unreachable -- surface to user, do not block audit
"""

import base64
import csv
import io
import logging
import os
from typing import Optional

import requests

log = logging.getLogger(__name__)

_POSTMARK_API_URL = "https://api.postmarkapp.com/email"
_POSTMARK_STREAM = "transactional"  # Always transactional for audit reports
_DEFAULT_FROM = "no-reply@notify.letitglow.app"
_REQUEST_TIMEOUT = 8  # seconds


def _token() -> str:
    return os.environ.get("POSTMARK_SERVER_TOKEN", "")


def _from_address() -> str:
    return os.environ.get("POSTMARK_FROM_EMAIL", _DEFAULT_FROM)


def email_configured() -> bool:
    """Return True if the Postmark token env var is set."""
    return bool(_token())


# ---------------------------------------------------------------------------
# CSV generation
# ---------------------------------------------------------------------------

def _findings_to_csv_bytes(findings) -> bytes:
    """Convert a list of Finding objects to UTF-8 CSV bytes."""
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "Rule ID",
        "Description",
        "Severity",
        "Category",
        "WCAG Criteria",
        "Auto-fixable",
        "Context",
    ])
    for f in findings:
        writer.writerow([
            getattr(f, "rule_id", ""),
            getattr(f, "description", ""),
            str(getattr(f, "severity", {}).value if hasattr(getattr(f, "severity", None), "value") else getattr(f, "severity", "")),
            getattr(f, "category", ""),
            getattr(f, "wcag_criterion", "") or "",
            "Yes" if getattr(f, "auto_fixable", False) else "No",
            (getattr(f, "context", "") or "")[:200],  # cap long context strings
        ])
    return buf.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility


def _base64_attachment(data: bytes, filename: str, content_type: str) -> dict:
    return {
        "Name": filename,
        "Content": base64.b64encode(data).decode("ascii"),
        "ContentType": content_type,
    }


# ---------------------------------------------------------------------------
# HTML email body
# ---------------------------------------------------------------------------

_SEVERITY_COLORS = {
    "Critical": "#8b0000",
    "High":     "#b35900",
    "Medium":   "#856404",
    "Low":      "#1a5c1a",
}

_GRADE_COLORS = {
    "A": "#1a5c1a",
    "B": "#2e6b00",
    "C": "#856404",
    "D": "#b35900",
    "F": "#8b0000",
}


def _severity_pill(label: str, count: int) -> str:
    if not count:
        return ""
    color = _SEVERITY_COLORS.get(label, "#333")
    return (
        f'<span style="display:inline-block;margin:0 4px 4px 0;padding:2px 10px;'
        f'background:{color};color:#fff;border-radius:3px;'
        f'font-family:Arial,sans-serif;font-size:16px;font-weight:700;">'
        f'{label}: {count}</span>'
    )


def _build_single_html(
    filename: str,
    doc_format: str,
    score: int,
    grade: str,
    findings_count: int,
    severity_breakdown: dict,
) -> str:
    grade_color = _GRADE_COLORS.get(grade, "#333")
    severity_pills = "".join(
        _severity_pill(sev, severity_breakdown.get(sev, 0))
        for sev in ("Critical", "High", "Medium", "Low")
    ) or '<span style="color:#1a5c1a;font-weight:700;">No findings -- document passes all checked rules.</span>'

    passed = findings_count == 0

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GLOW Audit Report</title></head>
<body style="margin:0;padding:0;background:#f4f4f4;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f4f4;">
  <tr><td style="padding:32px 16px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:640px;margin:0 auto;background:#fff;border:1px solid #ddd;border-radius:4px;">
      <!-- Header -->
      <tr>
        <td style="background:#1a1a1a;padding:24px 32px;">
          <p style="margin:0;font-family:Arial,sans-serif;font-size:22px;font-weight:700;color:#fff;">GLOW</p>
          <p style="margin:4px 0 0;font-family:Arial,sans-serif;font-size:18px;color:#ccc;">Audit Report</p>
        </td>
      </tr>
      <!-- Score card -->
      <tr>
        <td style="padding:32px 32px 16px;">
          <h1 style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:22px;font-weight:700;color:#1a1a1a;">{filename}</h1>
          <p style="margin:0 0 24px;font-family:Arial,sans-serif;font-size:18px;color:#555;">Format: {doc_format.upper()}</p>
          <table role="presentation" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="padding-right:32px;text-align:center;border:2px solid #1a1a1a;border-radius:4px;padding:16px 24px;">
                <p style="margin:0;font-family:Arial,sans-serif;font-size:36px;font-weight:700;color:{grade_color};">{score}/100</p>
                <p style="margin:4px 0 0;font-family:Arial,sans-serif;font-size:18px;color:#555;">Score (Grade {grade})</p>
              </td>
              <td style="width:24px;"></td>
              <td style="text-align:center;border:2px solid #1a1a1a;border-radius:4px;padding:16px 24px;">
                <p style="margin:0;font-family:Arial,sans-serif;font-size:36px;font-weight:700;color:#1a1a1a;">{findings_count}</p>
                <p style="margin:4px 0 0;font-family:Arial,sans-serif;font-size:18px;color:#555;">Total Findings</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
      <!-- Status -->
      <tr>
        <td style="padding:0 32px 24px;">
          {'<p style="font-family:Arial,sans-serif;font-size:20px;font-weight:700;color:#1a5c1a;">This document passes all checked rules.</p>' if passed else '<p style="font-family:Arial,sans-serif;font-size:20px;color:#1a1a1a;">Findings by severity:</p>' + f'<p style="margin:0;">{severity_pills}</p>'}
        </td>
      </tr>
      <!-- CSV note -->
      <tr>
        <td style="padding:0 32px 24px;">
          <p style="font-family:Arial,sans-serif;font-size:18px;color:#1a1a1a;">The full findings list is attached as a CSV file. Open it in Excel or any spreadsheet application to review every finding, its severity, WCAG criterion, and whether it can be auto-fixed.</p>
        </td>
      </tr>
      <!-- Footer -->
      <tr>
        <td style="background:#f4f4f4;padding:20px 32px;border-top:1px solid #ddd;">
          <p style="margin:0;font-family:Arial,sans-serif;font-size:16px;color:#666;">Sent by <strong>GLOW</strong> &mdash; ACB Large Print Guidelines &amp; WCAG 2.2 AA compliance auditing.</p>
          <p style="margin:8px 0 0;font-family:Arial,sans-serif;font-size:16px;color:#666;">This report was sent because you requested it during an audit session. Your email address was not stored.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def _build_batch_html(
    file_summaries: list[dict],  # [{filename, doc_format, score, grade, findings_count, severity_breakdown}]
    avg_score: Optional[int],
    total_findings: int,
) -> str:
    rows = ""
    for s in file_summaries:
        grade_color = _GRADE_COLORS.get(s.get("grade", "F"), "#333")
        rows += (
            f'<tr>'
            f'<td style="padding:10px 12px;font-family:Arial,sans-serif;font-size:17px;border-bottom:1px solid #eee;">{s["filename"]}</td>'
            f'<td style="padding:10px 12px;font-family:Arial,sans-serif;font-size:17px;border-bottom:1px solid #eee;text-align:center;">{s["doc_format"].upper()}</td>'
            f'<td style="padding:10px 12px;font-family:Arial,sans-serif;font-size:17px;font-weight:700;color:{grade_color};border-bottom:1px solid #eee;text-align:center;">{s.get("score", 0)}/100 ({s.get("grade", "F")})</td>'
            f'<td style="padding:10px 12px;font-family:Arial,sans-serif;font-size:17px;border-bottom:1px solid #eee;text-align:center;">{s.get("findings_count", 0)}</td>'
            f'</tr>'
        )

    avg_display = f"{avg_score}/100" if avg_score is not None else "N/A"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GLOW Batch Audit Report</title></head>
<body style="margin:0;padding:0;background:#f4f4f4;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f4f4;">
  <tr><td style="padding:32px 16px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:640px;margin:0 auto;background:#fff;border:1px solid #ddd;border-radius:4px;">
      <!-- Header -->
      <tr>
        <td style="background:#1a1a1a;padding:24px 32px;">
          <p style="margin:0;font-family:Arial,sans-serif;font-size:22px;font-weight:700;color:#fff;">GLOW</p>
          <p style="margin:4px 0 0;font-family:Arial,sans-serif;font-size:18px;color:#ccc;">Batch Audit Report &mdash; {len(file_summaries)} file{"s" if len(file_summaries) != 1 else ""}</p>
        </td>
      </tr>
      <!-- Summary -->
      <tr>
        <td style="padding:32px 32px 16px;">
          <h1 style="margin:0 0 16px;font-family:Arial,sans-serif;font-size:22px;font-weight:700;color:#1a1a1a;">Batch Summary</h1>
          <table role="presentation" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="text-align:center;border:2px solid #1a1a1a;border-radius:4px;padding:16px 24px;margin-right:16px;">
                <p style="margin:0;font-family:Arial,sans-serif;font-size:36px;font-weight:700;color:#1a1a1a;">{avg_display}</p>
                <p style="margin:4px 0 0;font-family:Arial,sans-serif;font-size:18px;color:#555;">Average Score</p>
              </td>
              <td style="width:16px;"></td>
              <td style="text-align:center;border:2px solid #1a1a1a;border-radius:4px;padding:16px 24px;">
                <p style="margin:0;font-family:Arial,sans-serif;font-size:36px;font-weight:700;color:#1a1a1a;">{total_findings}</p>
                <p style="margin:4px 0 0;font-family:Arial,sans-serif;font-size:18px;color:#555;">Total Findings</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
      <!-- Per-file table -->
      <tr>
        <td style="padding:0 32px 24px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;border:1px solid #ddd;">
            <thead>
              <tr style="background:#f5f5f5;">
                <th style="padding:10px 12px;font-family:Arial,sans-serif;font-size:17px;text-align:left;border-bottom:2px solid #ddd;">File</th>
                <th style="padding:10px 12px;font-family:Arial,sans-serif;font-size:17px;text-align:center;border-bottom:2px solid #ddd;">Format</th>
                <th style="padding:10px 12px;font-family:Arial,sans-serif;font-size:17px;text-align:center;border-bottom:2px solid #ddd;">Score</th>
                <th style="padding:10px 12px;font-family:Arial,sans-serif;font-size:17px;text-align:center;border-bottom:2px solid #ddd;">Findings</th>
              </tr>
            </thead>
            <tbody>
              {rows}
            </tbody>
          </table>
        </td>
      </tr>
      <!-- CSV note -->
      <tr>
        <td style="padding:0 32px 24px;">
          <p style="font-family:Arial,sans-serif;font-size:18px;color:#1a1a1a;">The combined findings for all files are attached as a CSV file. The <strong>File</strong> column identifies which document each finding belongs to.</p>
        </td>
      </tr>
      <!-- Footer -->
      <tr>
        <td style="background:#f4f4f4;padding:20px 32px;border-top:1px solid #ddd;">
          <p style="margin:0;font-family:Arial,sans-serif;font-size:16px;color:#666;">Sent by <strong>GLOW</strong> &mdash; ACB Large Print Guidelines &amp; WCAG 2.2 AA compliance auditing.</p>
          <p style="margin:8px 0 0;font-family:Arial,sans-serif;font-size:16px;color:#666;">This report was sent because you requested it during an audit session. Your email address was not stored.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_audit_report_email(
    to_email: str,
    filename: str,
    doc_format: str,
    score: int,
    grade: str,
    findings_count: int,
    severity_breakdown: dict,
    findings,
) -> tuple[bool, str]:
    """Send a single-file audit report email with a CSV attachment.

    Returns:
        (True, success_message) on success
        (False, error_message) on failure
    """
    if not email_configured():
        log.warning("POSTMARK_SERVER_TOKEN not set -- email send skipped")
        return False, "Email service is not configured. Contact the site administrator."

    csv_bytes = _findings_to_csv_bytes(findings)
    csv_name = filename.rsplit(".", 1)[0] + "-findings.csv"
    html_body = _build_single_html(
        filename, doc_format, score, grade, findings_count, severity_breakdown
    )

    subject = f"{filename} \u2013 Audit Report ({score}/100, Grade {grade}) | GLOW"

    payload = {
        "From": _from_address(),
        "To": to_email,
        "Subject": subject,
        "HtmlBody": html_body,
        "TextBody": (
            f"GLOW -- Audit Report\n\n"
            f"File: {filename}\n"
            f"Format: {doc_format.upper()}\n"
            f"Score: {score}/100 (Grade {grade})\n"
            f"Findings: {findings_count}\n\n"
            f"The findings CSV is attached to this email.\n\n"
            f"Your email address was not stored."
        ),
        "MessageStream": _POSTMARK_STREAM,
        "Attachments": [
            _base64_attachment(csv_bytes, csv_name, "text/csv"),
        ],
    }

    return _send(payload, to_email)


def send_batch_audit_report_email(
    to_email: str,
    file_results: list,  # list of dicts with filename, doc_format, result
    avg_score: Optional[int],
    total_findings: int,
) -> tuple[bool, str]:
    """Send a combined batch audit report email with a single merged CSV.

    Each finding row in the CSV includes the originating filename.
    Returns: (True, success_message) or (False, error_message)
    """
    if not email_configured():
        log.warning("POSTMARK_SERVER_TOKEN not set -- email send skipped")
        return False, "Email service is not configured. Contact the site administrator."

    # Build merged CSV with a File column prepended
    text_buf = io.StringIO()
    writer = csv.writer(text_buf, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "File",
        "Rule ID",
        "Description",
        "Severity",
        "Category",
        "WCAG Criteria",
        "Auto-fixable",
        "Context",
    ])
    file_summaries = []
    for r in file_results:
        if r.get("result") is None:
            continue
        result = r["result"]
        fname = r["filename"]
        findings = result.findings

        sev_breakdown: dict[str, int] = {}
        for f in findings:
            sev = str(f.severity.value if hasattr(f.severity, "value") else f.severity)
            sev_breakdown[sev] = sev_breakdown.get(sev, 0) + 1

        file_summaries.append({
            "filename": fname,
            "doc_format": r.get("doc_format", ""),
            "score": getattr(result, "score", 0),
            "grade": getattr(result, "grade", "F"),
            "findings_count": len(findings),
            "severity_breakdown": sev_breakdown,
        })

        for f in findings:
            writer.writerow([
                fname,
                getattr(f, "rule_id", ""),
                getattr(f, "description", ""),
                str(f.severity.value if hasattr(f.severity, "value") else f.severity),
                getattr(f, "category", ""),
                getattr(f, "wcag_criterion", "") or "",
                "Yes" if getattr(f, "auto_fixable", False) else "No",
                (getattr(f, "context", "") or "")[:200],
            ])

    csv_bytes = text_buf.getvalue().encode("utf-8-sig")
    file_count = len(file_summaries)
    html_body = _build_batch_html(file_summaries, avg_score, total_findings)

    subject = (
        f"Batch Audit Report ({file_count} file{'s' if file_count != 1 else ''}, "
        f"avg {avg_score}/100) | GLOW"
    )

    payload = {
        "From": _from_address(),
        "To": to_email,
        "Subject": subject,
        "HtmlBody": html_body,
        "TextBody": (
            f"GLOW -- Batch Audit Report\n\n"
            f"Files audited: {file_count}\n"
            f"Average score: {avg_score}/100\n"
            f"Total findings: {total_findings}\n\n"
            f"The combined findings CSV is attached to this email.\n\n"
            f"Your email address was not stored."
        ),
        "MessageStream": _POSTMARK_STREAM,
        "Attachments": [
            _base64_attachment(csv_bytes, "batch-findings.csv", "text/csv"),
        ],
    }

    return _send(payload, to_email)


def send_whisperer_status_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> tuple[bool, str]:
    """Send a lifecycle status email for BITS Whisperer jobs.

    Used for queued/started/completed/cleared notifications in background
    transcription flows.
    """
    if not email_configured():
        log.warning("POSTMARK_SERVER_TOKEN not set -- whisperer email send skipped")
        return False, "Email service is not configured. Contact the site administrator."

    payload = {
        "From": _from_address(),
        "To": to_email,
        "Subject": subject,
        "HtmlBody": html_body,
        "TextBody": text_body,
        "MessageStream": _POSTMARK_STREAM,
    }
    return _send(payload, to_email)


def send_workshop_return_link_email(
    to_email: str,
    *,
    link: str,
    ttl_days: int,
    session_title: str = "",
    participant_name: str = "",
) -> tuple[bool, str]:
    """Email a participant a single-use link back to their workshop work.

    Workshop identity is a cookie on one device. This is how someone picks up
    their morning's work on a phone at lunch, or opens their 30-day action
    plan a month later. The address is given voluntarily and is never shown in
    the gallery, the facilitator dashboard, or any export.
    """
    if not email_configured():
        log.warning("POSTMARK_SERVER_TOKEN not set -- workshop return link email skipped")
        return False, "Email is not configured on this server, so return links cannot be sent."

    greeting = f"Hello {participant_name}," if participant_name.strip() else "Hello,"
    where = f" for {session_title}" if session_title.strip() else ""
    expiry = f"This link works once and expires in {ttl_days} days."

    html_body = (
        f"<p>{greeting}</p>"
        f"<p>Here is your link back to your workshop work{where}. "
        "Open it on any device to pick up where you left off.</p>"
        f'<p><a href="{link}">Return to my workshop work</a></p>'
        f"<p>{expiry} You can request another one at any time from your "
        "workshop content page.</p>"
        "<p>If you did not ask for this link, you can ignore this message.</p>"
    )
    text_body = (
        f"{greeting}\n\n"
        f"Here is your link back to your workshop work{where}. "
        "Open it on any device to pick up where you left off.\n\n"
        f"{link}\n\n"
        f"{expiry} You can request another one at any time from your workshop "
        "content page.\n\n"
        "If you did not ask for this link, you can ignore this message."
    )

    payload = {
        "From": _from_address(),
        "To": to_email,
        "Subject": "Your link back to your GLOW workshop work",
        "HtmlBody": html_body,
        "TextBody": text_body,
        "MessageStream": _POSTMARK_STREAM,
    }
    return _send(payload, to_email)


# ---------------------------------------------------------------------------
# Internal send helper
# ---------------------------------------------------------------------------

def _send(payload: dict, to_email: str) -> tuple[bool, str]:
    """POST payload to Postmark API and return (success, message).

    Error handling follows Postmark Skills guidance:
      200   -- success
      400   -- bad request, do not retry
      401   -- auth failure, do not retry
      422   -- validation error, do not retry
      429   -- rate limited, surface "try again" to user
      5xx   -- transient server error
      Timeout -- Postmark unreachable
    """
    headers = {
        "X-Postmark-Server-Token": _token(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            _POSTMARK_API_URL,
            json=payload,
            headers=headers,
            timeout=_REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        log.warning("Postmark request timed out sending to %s", to_email)
        return False, "Email service timed out. The audit report is available on-screen. Please try again later."
    except requests.RequestException as exc:
        log.exception("Postmark network error: %s", exc)
        return False, "Email service is unreachable. The audit report is available on-screen."

    status = response.status_code

    if status == 200:
        log.info("Audit report emailed to %s", to_email)
        return True, f"Report sent to {to_email}. Check your spam folder if it does not arrive within a few minutes."

    if status == 429:
        log.warning("Postmark rate limited (429) sending to %s", to_email)
        return False, "Email service is temporarily busy. Please try again in a minute. The audit report is still available on-screen."

    if status in (400, 401):
        log.error("Postmark auth/config error %d: %s", status, response.text[:300])
        return False, "Email service is not properly configured. Contact the site administrator."

    if status == 422:
        log.error("Postmark validation error (422): %s", response.text[:300])
        return False, "Email could not be sent due to a validation error. Contact the site administrator."

    # 5xx or unexpected
    log.error("Postmark unexpected error %d: %s", status, response.text[:300])
    return False, f"Email service returned an error (HTTP {status}). The audit report is available on-screen."
