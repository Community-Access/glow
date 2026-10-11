"""Tests for the Postmark email integration module (email.py)."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from acb_large_print_web.email import (
    _findings_to_csv_bytes,
    _send,
    email_configured,
    send_audit_report_email,
    send_batch_audit_report_email,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding(
    rule_id="ACB-FONT-FAMILY",
    description="Font is not Arial",
    severity="Critical",
    category="acb",
    wcag_criterion="1.4.12",
    auto_fixable=True,
    context="Paragraph 1",
):
    """Build a minimal Finding-like object."""
    sev = SimpleNamespace(value=severity)
    return SimpleNamespace(
        rule_id=rule_id,
        description=description,
        severity=sev,
        category=category,
        wcag_criterion=wcag_criterion,
        auto_fixable=auto_fixable,
        context=context,
    )


# ---------------------------------------------------------------------------
# email_configured()
# ---------------------------------------------------------------------------

class TestEmailConfigured:
    def test_false_when_token_missing(self, monkeypatch):
        monkeypatch.delenv("POSTMARK_SERVER_TOKEN", raising=False)
        assert email_configured() is False

    def test_false_when_token_empty(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "")
        assert email_configured() is False

    def test_true_when_token_set(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "test-token-abc")
        assert email_configured() is True


# ---------------------------------------------------------------------------
# _findings_to_csv_bytes()
# ---------------------------------------------------------------------------

class TestFindingsToCsvBytes:
    def test_returns_bytes(self):
        result = _findings_to_csv_bytes([])
        assert isinstance(result, bytes)

    def test_bom_present_for_excel(self):
        result = _findings_to_csv_bytes([])
        assert result.startswith(b"\xef\xbb\xbf"), "CSV must start with UTF-8 BOM for Excel"

    def test_header_row(self):
        csv_text = _findings_to_csv_bytes([]).decode("utf-8-sig")
        first_line = csv_text.splitlines()[0]
        assert "Rule ID" in first_line
        assert "Severity" in first_line
        assert "WCAG Criteria" in first_line
        assert "Auto-fixable" in first_line

    def test_single_finding_row(self):
        f = _finding()
        csv_text = _findings_to_csv_bytes([f]).decode("utf-8-sig")
        lines = csv_text.splitlines()
        assert len(lines) == 2  # header + 1 data row
        assert "ACB-FONT-FAMILY" in lines[1]
        assert "Critical" in lines[1]
        assert "Yes" in lines[1]  # auto_fixable=True

    def test_non_fixable_finding(self):
        f = _finding(auto_fixable=False)
        csv_text = _findings_to_csv_bytes([f]).decode("utf-8-sig")
        assert "No" in csv_text

    def test_context_truncated_at_200_chars(self):
        long_ctx = "x" * 300
        f = _finding(context=long_ctx)
        csv_text = _findings_to_csv_bytes([f]).decode("utf-8-sig")
        # The context cell should not contain more than 200 x's
        assert "x" * 201 not in csv_text
        assert "x" * 200 in csv_text

    def test_empty_wcag_criterion(self):
        f = _finding(wcag_criterion=None)
        csv_text = _findings_to_csv_bytes([f]).decode("utf-8-sig")
        # Should not raise -- empty cell expected
        assert "ACB-FONT-FAMILY" in csv_text

    def test_multiple_findings(self):
        findings = [_finding(rule_id=f"RULE-{i}") for i in range(5)]
        csv_text = _findings_to_csv_bytes(findings).decode("utf-8-sig")
        lines = csv_text.splitlines()
        assert len(lines) == 6  # header + 5 rows


# ---------------------------------------------------------------------------
# _send() -- internal HTTP helper
# ---------------------------------------------------------------------------

class TestSend:
    """Tests for _send() using a mocked requests.post."""

    def _mock_response(self, status_code: int, text: str = "") -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        return resp

    def test_200_returns_success(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "tok")
        with patch("acb_large_print_web.email.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(200)
            ok, msg = _send({"From": "a@b.com"}, "user@example.com")
        assert ok is True
        assert "user@example.com" in msg

    def test_429_returns_rate_limit_message(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "tok")
        with patch("acb_large_print_web.email.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(429)
            ok, msg = _send({}, "user@example.com")
        assert ok is False
        assert "busy" in msg.lower() or "rate" in msg.lower()

    def test_401_returns_config_error(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "bad-tok")
        with patch("acb_large_print_web.email.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(401)
            ok, msg = _send({}, "user@example.com")
        assert ok is False
        assert "not properly configured" in msg.lower() or "administrator" in msg.lower()

    def test_400_returns_config_error(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "tok")
        with patch("acb_large_print_web.email.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(400, "Bad Request")
            ok, msg = _send({}, "user@example.com")
        assert ok is False

    def test_422_returns_validation_error(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "tok")
        with patch("acb_large_print_web.email.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(422, "Template error")
            ok, msg = _send({}, "user@example.com")
        assert ok is False
        assert "validation" in msg.lower()

    def test_500_returns_server_error(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "tok")
        with patch("acb_large_print_web.email.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(500)
            ok, msg = _send({}, "user@example.com")
        assert ok is False
        assert "500" in msg

    def test_timeout_returns_timeout_message(self, monkeypatch):
        import requests as req_lib
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "tok")
        with patch("acb_large_print_web.email.requests.post", side_effect=req_lib.Timeout):
            ok, msg = _send({}, "user@example.com")
        assert ok is False
        assert "timed out" in msg.lower()

    def test_network_error_returns_unreachable_message(self, monkeypatch):
        import requests as req_lib
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "tok")
        with patch(
            "acb_large_print_web.email.requests.post",
            side_effect=req_lib.RequestException("connection refused"),
        ):
            ok, msg = _send({}, "user@example.com")
        assert ok is False
        assert "unreachable" in msg.lower()


# ---------------------------------------------------------------------------
# send_audit_report_email() -- unconfigured guard
# ---------------------------------------------------------------------------

class TestSendAuditReportEmail:
    def test_skips_when_not_configured(self, monkeypatch):
        monkeypatch.delenv("POSTMARK_SERVER_TOKEN", raising=False)
        ok, msg = send_audit_report_email(
            to_email="user@example.com",
            filename="test.docx",
            doc_format="docx",
            score=72,
            grade="C",
            findings_count=3,
            severity_breakdown={"Critical": 1, "High": 2},
            findings=[],
        )
        assert ok is False
        assert "not configured" in msg.lower()

    def test_sends_when_configured(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "tok")
        with patch("acb_large_print_web.email.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200, text="")
            ok, msg = send_audit_report_email(
                to_email="user@example.com",
                filename="report.docx",
                doc_format="docx",
                score=85,
                grade="B",
                findings_count=2,
                severity_breakdown={"High": 2},
                findings=[_finding()],
            )
        assert ok is True
        # CSV attachment should have been included in payload
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs.args[0] if call_kwargs.args else {}
        # The transactional stream. Postmark's id for the one every server is
        # created with is "outbound"; "transactional" is the stream's type,
        # not its id, and sending to it returns 422.
        assert payload.get("MessageStream") == "outbound"
        # CSV attachment present
        attachments = payload.get("Attachments", [])
        assert len(attachments) == 1
        assert attachments[0]["ContentType"] == "text/csv"


# ---------------------------------------------------------------------------
# send_batch_audit_report_email() -- unconfigured guard + merged CSV
# ---------------------------------------------------------------------------

class TestSendBatchAuditReportEmail:
    def _make_file_result(self, filename: str, score: int = 80, grade: str = "B"):
        result = SimpleNamespace(
            score=score,
            grade=grade,
            findings=[_finding()],
        )
        return {"filename": filename, "doc_format": "docx", "result": result, "error": None}

    def test_skips_when_not_configured(self, monkeypatch):
        monkeypatch.delenv("POSTMARK_SERVER_TOKEN", raising=False)
        ok, msg = send_batch_audit_report_email(
            to_email="user@example.com",
            file_results=[self._make_file_result("a.docx")],
            avg_score=80,
            total_findings=1,
        )
        assert ok is False
        assert "not configured" in msg.lower()

    def test_merged_csv_has_file_column(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "tok")
        with patch("acb_large_print_web.email.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200, text="")
            ok, _ = send_batch_audit_report_email(
                to_email="user@example.com",
                file_results=[
                    self._make_file_result("file1.docx"),
                    self._make_file_result("file2.docx"),
                ],
                avg_score=80,
                total_findings=2,
            )
        assert ok is True
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or {}
        attachments = payload.get("Attachments", [])
        assert len(attachments) == 1
        import base64
        csv_content = base64.b64decode(attachments[0]["Content"]).decode("utf-8-sig")
        assert "File" in csv_content.splitlines()[0]
        assert "file1.docx" in csv_content
        assert "file2.docx" in csv_content

    def test_skips_failed_results(self, monkeypatch):
        monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "tok")
        with patch("acb_large_print_web.email.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200, text="")
            ok, _ = send_batch_audit_report_email(
                to_email="user@example.com",
                file_results=[
                    self._make_file_result("good.docx"),
                    {"filename": "bad.docx", "doc_format": None, "result": None, "error": "corrupt"},
                ],
                avg_score=80,
                total_findings=1,
            )
        assert ok is True
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or {}
        attachments = payload.get("Attachments", [])
        import base64
        csv_content = base64.b64decode(attachments[0]["Content"]).decode("utf-8-sig")
        assert "bad.docx" not in csv_content
