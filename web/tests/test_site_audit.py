from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask, render_template

import acb_large_print_web.routes.site_audit as site_audit_route
import acb_large_print_web.site_audit as site_audit
from acb_large_print_web.app import create_app


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "MAX_CONTENT_LENGTH": 50 * 1024 * 1024,
        }
    )
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def test_site_audit_form_loads(client):
    res = client.get("/site-audit/")
    assert res.status_code == 200
    assert "Site Audit" in res.get_data(as_text=True)


def test_site_audit_requires_valid_source(client):
    res = client.post(
        "/site-audit/",
        data={
            "sources": "",
            "sitemap_url": "",
        },
    )
    assert res.status_code == 400
    body = res.get_data(as_text=True)
    assert "Provide at least one valid URL" in body


def test_site_audit_submit_with_stubbed_runner(client, monkeypatch: pytest.MonkeyPatch):
    def _fake_run_site_audit(*, run_id, base_dir, sources, options):
        return {
            "run_id": run_id,
            "elapsed_ms": 25,
            "options": {
                "max_pages": options.max_pages,
                "crawl_links": options.crawl_links,
                "crawl_depth": options.crawl_depth,
                "include_subdomains": options.include_subdomains,
                "same_path_only": options.same_path_only,
                "exclude_url_patterns": list(options.exclude_url_patterns),
                "force": options.force,
            },
            "totals": {
                "pages_total": 1,
                "scanned": 1,
                "failed": 0,
                "skipped": 0,
                "findings": 1,
            },
            "wcag_rollup": {"wcag2aa": 1},
            "pages": [
                {
                    "index": 1,
                    "url": "https://example.com",
                    "title": "Example Domain",
                    "result": "ok",
                    "finding_count": 1,
                }
            ],
        }

    monkeypatch.setattr(site_audit_route, "run_site_audit", _fake_run_site_audit)

    res = client.post(
        "/site-audit/",
        data={
            "sources": "https://example.com",
            "max_pages": "10",
            "crawl_links": "on",
        },
    )
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "Run Summary" in body
    assert "Example Domain" in body


def test_site_audit_submit_passes_advanced_options(client, monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def _fake_run_site_audit(*, run_id, base_dir, sources, options):
        captured["sources"] = sources
        captured["options"] = options
        return {
            "run_id": run_id,
            "elapsed_ms": 25,
            "options": {
                "max_pages": options.max_pages,
                "crawl_links": options.crawl_links,
                "crawl_depth": options.crawl_depth,
                "include_subdomains": options.include_subdomains,
                "same_path_only": options.same_path_only,
                "exclude_url_patterns": list(options.exclude_url_patterns),
                "force": options.force,
            },
            "totals": {
                "pages_total": 1,
                "scanned": 1,
                "failed": 0,
                "skipped": 0,
                "findings": 0,
            },
            "wcag_rollup": {},
            "pages": [],
        }

    monkeypatch.setattr(site_audit_route, "run_site_audit", _fake_run_site_audit)

    res = client.post(
        "/site-audit/",
        data={
            "sources": "https://example.com/start",
            "max_pages": "12",
            "crawl_links": "on",
            "crawl_depth": "2",
            "include_subdomains": "on",
            "same_path_only": "on",
            "exclude_patterns": "/tag/\n?replytocom=",
            "force": "on",
        },
    )

    assert res.status_code == 200
    options = captured.get("options")
    assert options is not None
    assert options.max_pages == 12
    assert options.crawl_links is True
    assert options.crawl_depth == 2
    assert options.include_subdomains is True
    assert options.same_path_only is True
    assert options.exclude_url_patterns == ("/tag/", "?replytocom=")
    assert options.force is True


def test_site_audit_artifact_download(client, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    run_id = "11111111-1111-1111-1111-111111111111"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text('{"ok": true}', encoding="utf-8")
    (run_dir / "findings.csv").write_text("a,b\n", encoding="utf-8")
    (run_dir / "session.log").write_text("log\n", encoding="utf-8")
    (run_dir / "artifacts.zip").write_bytes(b"PK\x03\x04")

    monkeypatch.setattr(site_audit_route, "_runs_root", lambda: tmp_path / "runs")

    res = client.get(f"/site-audit/runs/{run_id}/download/summary")
    assert res.status_code == 200
    assert res.mimetype == "application/json"

    res_csv = client.get(f"/site-audit/runs/{run_id}/download/csv")
    assert res_csv.status_code == 200
    assert res_csv.mimetype in {"text/csv", "text/plain"}


def test_site_audit_feature_flag_404(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(site_audit_route, "_enabled", lambda: False)
    res = client.get("/site-audit/")
    assert res.status_code == 404


def test_expand_with_crawl_respects_depth_and_path_scope(monkeypatch: pytest.MonkeyPatch):
    pages = {
        "https://example.com/docs": '<a href="/docs/guide">Guide</a><a href="/blog/post">Blog</a>',
        "https://example.com/docs/guide": '<a href="/docs/guide/advanced">Advanced</a>',
        "https://example.com/docs/guide/advanced": "",
    }

    class _Resp:
        def __init__(self, url: str, text: str):
            self.url = url
            self.text = text

    def _fake_get(url: str, timeout: int = 15):
        return _Resp(url, pages.get(url, ""))

    monkeypatch.setattr(site_audit, "_http_get", _fake_get)

    urls_depth_1 = site_audit._expand_with_crawl(
        ["https://example.com/docs"],
        max_pages=10,
        crawl_depth=1,
        include_subdomains=False,
        same_path_only=True,
        exclude_url_patterns=(),
    )
    assert urls_depth_1 == ["https://example.com/docs", "https://example.com/docs/guide"]

    urls_depth_2 = site_audit._expand_with_crawl(
        ["https://example.com/docs"],
        max_pages=10,
        crawl_depth=2,
        include_subdomains=False,
        same_path_only=True,
        exclude_url_patterns=(),
    )
    assert urls_depth_2 == [
        "https://example.com/docs",
        "https://example.com/docs/guide",
        "https://example.com/docs/guide/advanced",
    ]


def test_expand_with_crawl_respects_exclusions(monkeypatch: pytest.MonkeyPatch):
    pages = {
        "https://example.com": '<a href="/about">About</a><a href="/blog/post-1">Blog</a>',
        "https://example.com/about": "",
        "https://example.com/blog/post-1": "",
    }

    class _Resp:
        def __init__(self, url: str, text: str):
            self.url = url
            self.text = text

    def _fake_get(url: str, timeout: int = 15):
        return _Resp(url, pages.get(url, ""))

    monkeypatch.setattr(site_audit, "_http_get", _fake_get)

    urls = site_audit._expand_with_crawl(
        ["https://example.com"],
        max_pages=10,
        crawl_depth=2,
        include_subdomains=False,
        same_path_only=False,
        exclude_url_patterns=("/blog/",),
    )
    assert urls == ["https://example.com", "https://example.com/about"]


def test_is_public_url_blocks_internal_targets(monkeypatch: pytest.MonkeyPatch):
    # Loopback / private / link-local literals are rejected without any DNS.
    for blocked in (
        "http://127.0.0.1/",
        "http://localhost/",  # resolves to loopback
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://[::1]/",
        "http://redis:6379/",  # non-web port
        "ftp://example.com/",  # non-http scheme
    ):
        assert site_audit._is_public_url(blocked) is False, blocked


def test_is_public_url_allows_public_host(monkeypatch: pytest.MonkeyPatch):
    # Stub DNS so the test needs no network and is deterministic.
    def _fake_getaddrinfo(host, port, *args, **kwargs):
        return [(2, 1, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(site_audit.socket, "getaddrinfo", _fake_getaddrinfo)
    assert site_audit._is_public_url("https://example.com/page") is True


def test_scan_single_page_blocks_ssrf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    # A non-public target must be turned into a per-page error, never fetched.
    called = {"n": 0}

    def _should_not_run(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("requests.get must not be reached for a blocked URL")

    monkeypatch.setattr(site_audit.requests, "get", _should_not_run)
    page_dir = tmp_path / "page"
    page_dir.mkdir()
    result = site_audit._scan_single_page("http://169.254.169.254/", page_dir)
    assert result["result"] == "error"
    assert "non-public" in result["reason"].lower()
    assert called["n"] == 0


def test_normalize_url_rejects_non_web_schemes():
    assert site_audit._normalize_url("mailto:info@example.com") == ""
    assert site_audit._normalize_url("tel:+15551234") == ""
    assert site_audit._normalize_url("javascript:alert(1)") == ""
    # Bare hosts still get https://, real links pass through.
    assert site_audit._normalize_url("example.com/path") == "https://example.com/path"
    assert site_audit._normalize_url("https://example.com/a") == "https://example.com/a"


def test_normalize_url_strips_fragment():
    assert site_audit._normalize_url("https://example.com/page#section") == "https://example.com/page"
    assert site_audit._normalize_url("https://example.com/#top") == "https://example.com/"


def test_page_parser_flushes_title_and_link_without_closing_tags():
    parser = site_audit._PageParser()
    parser.feed("<html lang='en'><head><title>My Page")
    parser.close()
    assert parser.title == "My Page"

    parser = site_audit._PageParser()
    parser.feed("<a href='/y'>Home</a><a href='/z'>Docs")
    parser.close()
    hrefs = [h for h, _ in parser.links]
    assert hrefs == ["/y", "/z"]


def test_scan_single_page_marks_http_error_as_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    class _Resp:
        status_code = 404
        url = "https://example.com/missing"
        text = "<html><body>Not found</body></html>"

    monkeypatch.setattr(site_audit, "_http_get", lambda url, timeout=20: _Resp())
    page_dir = tmp_path / "page"
    page_dir.mkdir()
    result = site_audit._scan_single_page("https://example.com/missing", page_dir)
    assert result["result"] == "error"
    assert result["status_code"] == 404
    assert result["findings"] == []


def test_finding_includes_open_learning_resources():
    finding = site_audit._finding(
        "https://example.com",
        "HEURISTIC-IMG-ALT",
        "serious",
        "Image missing alt text.",
        "img",
        wcag_tags=["wcag111"],
    )
    resources = finding.get("resources") or []

    assert finding.get("wcag_criteria") == ["1.1.1"]
    assert resources
    urls = [r.get("url") for r in resources]
    assert "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html" in urls
    assert "https://www.a11yproject.com/checklist/" in urls


def test_site_audit_protected_run_requires_token_and_password(
    client,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    run_id = "22222222-2222-2222-2222-222222222222"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "elapsed_ms": 10,
                "options": {"max_pages": 1, "crawl_links": False, "strict_open_source_only": False},
                "totals": {"pages_total": 1, "scanned": 1, "failed": 0, "skipped": 0, "findings": 0},
                "wcag_rollup": {},
                "pages": [],
            }
        ),
        encoding="utf-8",
    )

    token = "abc123token"
    (run_dir / "access.json").write_text(
        json.dumps(
            {
                "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                "password_hash": site_audit_route.generate_password_hash("secretpw"),
                "expires_at": "2099-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(site_audit_route, "_runs_root", lambda: tmp_path / "runs")

    denied = client.get(f"/site-audit/runs/{run_id}")
    assert denied.status_code == 403

    needs_password = client.get(f"/site-audit/runs/{run_id}?access={token}")
    assert needs_password.status_code == 200
    assert "Unlock Protected Site Audit Run" in needs_password.get_data(as_text=True)

    bad = client.post(
        f"/site-audit/runs/{run_id}/unlock",
        data={"access": token, "access_password": "wrong"},
    )
    assert bad.status_code == 200
    assert "Incorrect password" in bad.get_data(as_text=True)

    ok = client.post(
        f"/site-audit/runs/{run_id}/unlock",
        data={"access": token, "access_password": "secretpw"},
        follow_redirects=True,
    )
    assert ok.status_code == 200
    assert "Site Audit Results" in ok.get_data(as_text=True)


def test_site_audit_background_job_status(client, monkeypatch: pytest.MonkeyPatch):
    site_audit_route._jobs.clear()

    def _fake_run_site_audit(*, run_id, base_dir, sources, options, is_cancelled=None, progress_callback=None):
        return {
            "run_id": run_id,
            "elapsed_ms": 20,
            "cancelled": False,
            "options": {
                "max_pages": options.max_pages,
                "crawl_links": options.crawl_links,
                "strict_open_source_only": options.strict_open_source_only,
            },
            "totals": {
                "pages_total": 1,
                "scanned": 1,
                "failed": 0,
                "skipped": 0,
                "findings": 0,
            },
            "wcag_rollup": {},
            "pages": [],
        }

    monkeypatch.setattr(site_audit_route, "run_site_audit", _fake_run_site_audit)

    res = client.post(
        "/site-audit/",
        data={
            "sources": "https://example.com",
            "run_in_background": "on",
            "protect_results": "on",
        },
    )
    assert res.status_code == 200

    assert site_audit_route._jobs
    job = next(iter(site_audit_route._jobs.values()))
    assert job.access_token_value

    deadline = time.monotonic() + 5.0
    while job.status not in {"complete", "failed", "cancelled"} and time.monotonic() < deadline:
        time.sleep(0.02)
    assert job.error is None
    assert job.status == "complete"

    status = client.get(f"/site-audit/jobs/{job.job_id}/status?access={job.access_token_value}")
    assert status.status_code == 200
    payload = status.get_json()
    assert payload["job_id"] == job.job_id
    assert "attempt" in payload
    assert "max_attempts" in payload


def test_site_audit_background_job_retry(client, monkeypatch: pytest.MonkeyPatch):
    site_audit_route._jobs.clear()
    job = site_audit_route._SiteAuditJob(
        job_id="retry-audit-1",
        run_id="run-retry-1",
        status="failed",
        progress=0,
        message="failed",
        error="boom",
        attempt=1,
        max_attempts=2,
        deadline_at=9999999999.0,
        access_token_hash=site_audit_route._hash_token("token-1"),
        access_token_value="token-1",
        sources=("https://example.com",),
        options=site_audit.SiteAuditOptions(max_pages=10),
    )
    site_audit_route._jobs[job.job_id] = job

    started: list[str] = []

    def _fake_start(*, job, sources, options):
        started.append(job.job_id)

    monkeypatch.setattr(site_audit_route, "_start_site_audit_job", _fake_start)

    res = client.post(
        f"/site-audit/jobs/{job.job_id}/retry",
        data={"access": "token-1"},
    )
    assert res.status_code == 302
    assert started == [job.job_id]
    assert job.status == "queued"


# ---------------------------------------------------------------------------
# Regression tests for the confirmed site-audit findings.
# ---------------------------------------------------------------------------


class _FakeResp:
    """Minimal stand-in for the _http_get response object."""

    def __init__(
        self,
        content: bytes,
        content_type: str,
        *,
        apparent: str = "utf-8",
        encoding: str = "ISO-8859-1",
        status: int = 200,
        url: str = "https://example.com/",
    ):
        self._content = content
        self.headers = {"Content-Type": content_type}
        self.apparent_encoding = apparent
        self.encoding = encoding
        self.status_code = status
        self.url = url

    @property
    def text(self) -> str:
        return self._content.decode(self.encoding or "utf-8", errors="replace")


def test_scan_single_page_recovers_utf8_without_charset(monkeypatch, tmp_path):
    # Finding 4: a UTF-8 page served as text/html with no charset must not mojibake.
    title = "Caf\u00e9 D\u00e9j\u00e0 Vu"
    body = (
        "<html lang='en'><head><title>" + title + "</title></head><body></body></html>"
    ).encode("utf-8")
    resp = _FakeResp(body, "text/html")  # no charset -> requests would use ISO-8859-1
    monkeypatch.setattr(site_audit, "_http_get", lambda url, timeout=20: resp)
    monkeypatch.setattr(site_audit, "_axe_available", lambda: False)
    page_dir = tmp_path / "p"
    page_dir.mkdir()
    result = site_audit._scan_single_page("https://example.com/", page_dir)
    assert result["result"] == "ok"
    assert result["title"] == title


def test_scan_single_page_skips_non_html_content(monkeypatch, tmp_path):
    # Finding 5: a linked PDF must be recorded as skipped, never fed to the parser.
    resp = _FakeResp(b"%PDF-1.7 binary garbage", "application/pdf")
    monkeypatch.setattr(site_audit, "_http_get", lambda url, timeout=20: resp)
    monkeypatch.setattr(site_audit, "_axe_available", lambda: False)
    page_dir = tmp_path / "p"
    page_dir.mkdir()
    result = site_audit._scan_single_page("https://example.com/file.pdf", page_dir)
    assert result["result"] == "skipped"
    assert result["findings"] == []
    assert "content type" in result["reason"].lower()


def test_severity_vocab_maps_axe_critical_to_critical():
    # Finding 7: one taxonomy; axe critical -> critical (not the old -> serious).
    assert site_audit._severity_for_impact("critical") == "critical"
    assert site_audit._severity_for_impact("serious") == "serious"
    assert site_audit._severity_for_impact("moderate") == "moderate"
    assert site_audit._severity_for_impact("minor") == "minor"
    assert site_audit._severity_for_impact("bogus") == "minor"


def test_heuristic_findings_use_shared_severity_vocab(monkeypatch, tmp_path):
    # Finding 7: heuristics must emit vocabulary values, never "high".
    resp = _FakeResp(b"<html><body></body></html>", "text/html")  # no lang, no title
    monkeypatch.setattr(site_audit, "_http_get", lambda url, timeout=20: resp)
    monkeypatch.setattr(site_audit, "_axe_available", lambda: False)
    page_dir = tmp_path / "p"
    page_dir.mkdir()
    result = site_audit._scan_single_page("https://example.com/", page_dir)
    severities = {f["severity"] for f in result["findings"]}
    assert severities
    assert "high" not in severities
    assert severities <= set(site_audit.SEVERITY_LEVELS)


def test_run_axe_uses_resolved_npx_path(monkeypatch, tmp_path):
    # Finding 6: the resolved npx path (npx.cmd on Windows) is used, not bare "npx".
    monkeypatch.setattr(
        site_audit.shutil, "which", lambda name: r"C:\tools\npx.cmd" if name == "npx" else None
    )
    captured: dict[str, object] = {}

    class _Proc:
        returncode = 0
        stderr = ""
        stdout = ""

    def _fake_run(command, **kwargs):
        captured["command"] = command
        return _Proc()

    monkeypatch.setattr(site_audit.subprocess, "run", _fake_run)
    assert site_audit._axe_available() is True
    site_audit._run_axe("https://example.com/", tmp_path / "axe.json")
    assert captured["command"][0] == r"C:\tools\npx.cmd"


def test_run_axe_raises_when_npx_missing(monkeypatch, tmp_path):
    # Finding 6: guard against None from shutil.which instead of FileNotFoundError.
    monkeypatch.setattr(site_audit.shutil, "which", lambda name: None)
    assert site_audit._axe_available() is False
    with pytest.raises(RuntimeError):
        site_audit._run_axe("https://example.com/", tmp_path / "axe.json")


def test_expand_with_crawl_dedupes_shared_frontier(monkeypatch):
    # Finding 10: a candidate linked from two pages is queued once (O(1) set).
    pages = {
        "https://example.com/": '<a href="/a">A</a><a href="/b">B</a>',
        "https://example.com/a": '<a href="/shared">S</a>',
        "https://example.com/b": '<a href="/shared">S</a>',
        "https://example.com/shared": "",
    }

    class _Resp:
        def __init__(self, url, text):
            self.url = url
            self.text = text
            self.headers = {"Content-Type": "text/html"}

    monkeypatch.setattr(
        site_audit, "_http_get", lambda url, timeout=15: _Resp(url, pages.get(url, ""))
    )
    urls = site_audit._expand_with_crawl(
        ["https://example.com/"],
        max_pages=10,
        crawl_depth=3,
        include_subdomains=False,
        same_path_only=False,
        exclude_url_patterns=(),
    )
    assert urls.count("https://example.com/shared") == 1
    assert sorted(urls) == [
        "https://example.com/",
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/shared",
    ]


def test_run_site_audit_skip_branch_aggregates_findings(monkeypatch, tmp_path):
    # Finding 3: reusing cached page.json must still report its findings.
    run_id = "33333333-3333-3333-3333-333333333333"
    base = tmp_path / "runs"
    url = "https://example.com/"
    slug = site_audit._slug_for_url(url)
    page_dir = base / run_id / "pages" / slug
    page_dir.mkdir(parents=True)
    cached = {
        "url": url,
        "result": "ok",
        "status_code": 200,
        "title": "Cached",
        "findings": [
            {
                "page_url": url,
                "rule_id": "HEURISTIC-HTML-LANG",
                "severity": "serious",
                "message": "x",
                "location": "html",
                "help_url": "",
                "wcag_criteria": ["3.1.1"],
                "resources": [],
            }
        ],
        "finding_count": 1,
        "wcag_tags": {"wcag311": 1},
    }
    (page_dir / "page.json").write_text(json.dumps(cached), encoding="utf-8")
    monkeypatch.setattr(site_audit, "_axe_available", lambda: False)
    options = site_audit.SiteAuditOptions(max_pages=5, crawl_links=False, force=False)
    summary = site_audit.run_site_audit(run_id=run_id, base_dir=base, sources=[url], options=options)
    assert summary["totals"]["findings"] == 1
    assert summary["totals"]["skipped"] == 1
    assert summary["wcag_rollup"].get("wcag311") == 1


def test_run_site_audit_rescans_corrupt_page_json(monkeypatch, tmp_path):
    # Finding 9: a corrupt cached page.json must be re-scanned, not rendered raw.
    run_id = "44444444-4444-4444-4444-444444444444"
    base = tmp_path / "runs"
    url = "https://example.com/"
    slug = site_audit._slug_for_url(url)
    page_dir = base / run_id / "pages" / slug
    page_dir.mkdir(parents=True)
    (page_dir / "page.json").write_text("{ this is not valid json", encoding="utf-8")
    resp = _FakeResp(
        b"<html lang='en'><head><title>Fresh</title></head><body></body></html>", "text/html"
    )
    monkeypatch.setattr(site_audit, "_http_get", lambda url, timeout=20: resp)
    monkeypatch.setattr(site_audit, "_axe_available", lambda: False)
    options = site_audit.SiteAuditOptions(max_pages=5, crawl_links=False, force=False)
    summary = site_audit.run_site_audit(run_id=run_id, base_dir=base, sources=[url], options=options)
    pages = summary["pages"]
    assert len(pages) == 1
    assert pages[0]["url"] == url
    assert pages[0]["result"] == "ok"
    assert pages[0]["title"] == "Fresh"


def test_sweep_site_audit_runs_removes_old_dirs(app, monkeypatch):
    # Finding 1: run directories past the TTL are swept; fresh ones survive.
    with app.app_context():
        root = site_audit_route._runs_root()
        old = root / "old-run"
        old.mkdir()
        (old / "summary.json").write_text("{}", encoding="utf-8")
        fresh = root / "fresh-run"
        fresh.mkdir()
        old_mtime = time.time() - (site_audit_route._access_ttl_hours + 1) * 3600
        os.utime(old, (old_mtime, old_mtime))
        removed = site_audit_route.sweep_site_audit_runs()
        assert removed == 1
        assert not old.exists()
        assert fresh.exists()


def test_evict_stale_jobs_drops_old_terminal_jobs():
    # Finding 1: terminal jobs past the TTL are evicted; fresh/running ones stay.
    site_audit_route._jobs.clear()
    old = site_audit_route._SiteAuditJob(
        job_id="old",
        run_id="r1",
        status="complete",
        created_at=datetime.now(UTC) - timedelta(hours=100),
        completed_at=datetime.now(UTC) - timedelta(hours=100),
    )
    fresh = site_audit_route._SiteAuditJob(
        job_id="fresh",
        run_id="r2",
        status="complete",
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    running = site_audit_route._SiteAuditJob(
        job_id="running",
        run_id="r3",
        status="running",
        created_at=datetime.now(UTC) - timedelta(hours=100),
    )
    site_audit_route._jobs.update({"old": old, "fresh": fresh, "running": running})
    removed = site_audit_route._evict_stale_jobs()
    assert removed == 1
    assert "old" not in site_audit_route._jobs
    assert "fresh" in site_audit_route._jobs
    assert "running" in site_audit_route._jobs
    site_audit_route._jobs.clear()


def test_retry_refused_while_worker_alive(client, monkeypatch):
    # Finding 2: an immediate retry must not spawn a second worker over the run dir.
    site_audit_route._jobs.clear()
    release = threading.Event()
    worker = threading.Thread(target=lambda: release.wait(5), daemon=True)
    worker.start()
    job = site_audit_route._SiteAuditJob(
        job_id="rw1",
        run_id="run-rw1",
        status="cancelled",
        attempt=1,
        max_attempts=2,
        deadline_at=9999999999.0,
        worker=worker,
        sources=("https://example.com",),
        options=site_audit.SiteAuditOptions(max_pages=10),
    )
    site_audit_route._jobs[job.job_id] = job
    started: list[str] = []
    monkeypatch.setattr(
        site_audit_route, "_start_site_audit_job", lambda **kw: started.append(kw["job"].job_id)
    )
    try:
        res = client.post(f"/site-audit/jobs/{job.job_id}/retry", data={})
        assert res.status_code == 302
        assert started == []  # refused because the previous worker is still alive
    finally:
        release.set()
        worker.join()
        site_audit_route._jobs.clear()


def test_retry_forces_fresh_crawl(client, monkeypatch):
    # Finding 3: retry must force=True so it does not reuse cached page output.
    site_audit_route._jobs.clear()
    job = site_audit_route._SiteAuditJob(
        job_id="rf1",
        run_id="run-rf1",
        status="failed",
        attempt=1,
        max_attempts=2,
        deadline_at=9999999999.0,
        sources=("https://example.com",),
        options=site_audit.SiteAuditOptions(max_pages=10, force=False),
    )
    site_audit_route._jobs[job.job_id] = job
    captured: dict[str, object] = {}

    def _fake_start(*, job, sources, options):
        captured["options"] = options

    monkeypatch.setattr(site_audit_route, "_start_site_audit_job", _fake_start)
    try:
        res = client.post(f"/site-audit/jobs/{job.job_id}/retry", data={})
        assert res.status_code == 302
        assert captured["options"].force is True
        assert job.options.force is True
    finally:
        site_audit_route._jobs.clear()


def test_naive_expires_at_does_not_500(client, monkeypatch, tmp_path):
    # Finding 8: a tz-naive expires_at must yield a clean gate, never a TypeError 500.
    run_id = "55555555-5555-5555-5555-555555555555"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    run_dir_summary = {
        "run_id": run_id,
        "elapsed_ms": 10,
        "options": {"max_pages": 1, "crawl_links": False, "strict_open_source_only": False},
        "totals": {"pages_total": 1, "scanned": 1, "failed": 0, "skipped": 0, "findings": 0},
        "wcag_rollup": {},
        "pages": [],
    }
    (run_dir / "summary.json").write_text(json.dumps(run_dir_summary), encoding="utf-8")
    token = "naivetoken"
    (run_dir / "access.json").write_text(
        json.dumps(
            {
                "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                "password_hash": None,
                "expires_at": "2099-01-01T00:00:00",  # tz-naive
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(site_audit_route, "_runs_root", lambda: tmp_path / "runs")
    res = client.get(f"/site-audit/runs/{run_id}?access={token}")
    assert res.status_code == 200
    assert "Site Audit Results" in res.get_data(as_text=True)


def test_result_template_labels_new_tab_links(app):
    # Finding 11: new-tab links warn and fall back to the URL when the title is empty.
    summary = {
        "elapsed_ms": 10,
        "options": {
            "max_pages": 1,
            "crawl_links": False,
            "crawl_depth": 1,
            "include_subdomains": False,
            "same_path_only": False,
            "strict_open_source_only": False,
            "force": False,
            "exclude_url_patterns": [],
        },
        "totals": {"pages_total": 1, "scanned": 1, "failed": 0, "skipped": 0, "findings": 1},
        "wcag_rollup": {},
        "pages": [
            {
                "index": 1,
                "url": "https://example.com/x",
                "title": "",
                "result": "ok",
                "finding_count": 1,
                "findings": [
                    {
                        "rule_id": "R",
                        "message": "m",
                        "wcag_criteria": [],
                        "resources": [{"url": "https://help.example/r", "title": ""}],
                    }
                ],
            }
        ],
    }
    with app.test_request_context():
        html = render_template("site_audit_result.html", summary=summary, run_id="rid", access=None)
    assert 'aria-label="Open scanned page in a new tab: https://example.com/x"' in html
    assert 'aria-label="Open learning resource in a new tab: https://help.example/r"' in html


# --- David/Carroll Center feedback: scanner errors, headings, title quality ---


def _parse(html):
    parser = site_audit._PageParser()
    parser.feed(html)
    parser.close()
    return parser


def _sparse_page_html():
    # Shaped like the reported page: one h1, graphics standing in for section
    # headings, and a lot of body text with nothing to navigate by.
    body = "<p>" + ("Stow Lions Club community service work. " * 40) + "</p>"
    return (
        '<html lang="en"><head><title>Lions Clubs</title></head><body>'
        "<h1>Stow Lions Club</h1>"
        '<img src="a.png" alt="Eyeglass collection">' + body +
        '<img src="b.png" alt="Food pantry">' + body +
        '<img src="c.png" alt="Scholarships">' + body +
        "</body></html>"
    )


def test_scanner_failure_is_not_reported_as_a_page_finding(monkeypatch, tmp_path):
    # David could not act on a raw npm trace attached to every page. A scanner
    # outage is run-level status, never a finding against the scanned site.
    resp = _FakeResp(
        b"<html lang='en'><head><title>T</title></head><body></body></html>", "text/html"
    )
    monkeypatch.setattr(site_audit, "_http_get", lambda url, timeout=20: resp)
    monkeypatch.setattr(site_audit, "_axe_available", lambda: True)

    def _boom(url, output_path):
        raise RuntimeError("npm ERR! code EACCES\nnpm ERR! path /app/.npm")

    monkeypatch.setattr(site_audit, "_run_axe", _boom)
    page_dir = tmp_path / "p"
    page_dir.mkdir()
    result = site_audit._scan_single_page("https://example.com/", page_dir)

    assert all(f["rule_id"] != "AXE-UNAVAILABLE" for f in result["findings"])
    assert result["deep_scan"]["ok"] is False
    assert "npm" not in result["deep_scan"]["message"].lower()
    assert "EACCES" not in result["deep_scan"]["message"]
    assert "Nothing is wrong with your page" in result["deep_scan"]["message"]
    # The raw text stays available for whoever maintains the server.
    assert "EACCES" in result["deep_scan"]["detail"]


def test_run_notice_summarises_scanner_outage_once():
    # One outage, one message -- not one row per scanned page.
    pages = [
        {
            "url": f"https://example.com/{i}",
            "result": "ok",
            "title": f"P{i}",
            "deep_scan": {
                "ok": False,
                "message": "The deep scanner could not start.",
                "detail": "raw",
            },
        }
        for i in range(4)
    ]
    notices = site_audit._build_run_notices(pages)
    assert len(notices) == 1
    assert notices[0]["affected_pages"] == 4
    assert "all 4 pages" in notices[0]["message"]
    assert notices[0]["consequence"]


def test_run_notice_absent_when_deep_scan_succeeds():
    pages = [
        {"url": "https://example.com/", "result": "ok", "title": "P", "deep_scan": {"ok": True}}
    ]
    assert site_audit._build_run_notices(pages) == []


@pytest.mark.parametrize(
    "raw,expected_fragment",
    [
        ("npm ERR! code EACCES mkdir /app/.npm", "file-permission problem"),
        ("spawn axe ENOENT", "not installed"),
        ("session not created: chromedriver mismatch", "browser could not start"),
        ("axe timed out after 90 seconds", "took too long"),
        ("something nobody anticipated", "could not run"),
    ],
)
def test_friendly_scanner_messages_avoid_jargon(raw, expected_fragment):
    message = site_audit._friendly_scanner_message(raw)
    assert expected_fragment in message
    for jargon in ("npm ERR", "EACCES", "errno", "syscall", "chown", "stderr"):
        assert jargon not in message


def test_heading_checks_flag_sparse_and_image_led_page():
    parser = _parse(_sparse_page_html())
    rules = {f["rule_id"] for f in site_audit._heading_findings("https://example.com/x.php", parser)}
    assert "HEURISTIC-HEADING-SPARSE" in rules
    assert "HEURISTIC-IMAGE-AS-HEADING" in rules


def test_heading_checks_stay_quiet_on_well_structured_page():
    html = (
        '<html lang="en"><head><title>Projects | Stow Lions Club</title></head><body>'
        "<h1>Projects</h1><p>We run three programmes.</p>"
        "<h2>Eyeglasses</h2><p>Details.</p><h2>Food pantry</h2><p>Details.</p>"
        "</body></html>"
    )
    parser = _parse(html)
    assert site_audit._heading_findings("https://example.com/projects", parser) == []
    assert site_audit._title_findings("https://example.com/projects", parser) == []


def test_heading_checks_detect_missing_h1_skips_and_silent_headings():
    html = (
        "<html><body><h2>One</h2><h4>Deep</h4>"
        '<h2><img src="x.png" alt=""></h2></body></html>'
    )
    parser = _parse(html)
    rules = {f["rule_id"] for f in site_audit._heading_findings("https://example.com/", parser)}
    assert "HEURISTIC-HEADING-NO-H1" in rules
    assert "HEURISTIC-HEADING-SKIPPED-LEVEL" in rules
    assert "HEURISTIC-HEADING-EMPTY" in rules


def test_heading_checks_flag_page_with_no_headings_at_all():
    parser = _parse("<html><body><p>Content with no structure at all.</p></body></html>")
    rules = {f["rule_id"] for f in site_audit._heading_findings("https://example.com/", parser)}
    assert rules == {"HEURISTIC-HEADING-NONE"}


def test_aria_role_heading_counts_as_a_heading():
    html = '<html><body><h1>Top</h1><div role="heading" aria-level="2">Section</div></body></html>'
    parser = _parse(html)
    assert [(h.level, h.text) for h in parser.headings] == [(1, "Top"), (2, "Section")]


def test_title_quality_flags_generic_and_undescriptive_titles():
    generic = _parse(
        "<html><head><title>Home</title></head><body><h1>Projects</h1></body></html>"
    )
    assert {
        f["rule_id"] for f in site_audit._title_findings("https://example.com/projects", generic)
    } == {"HEURISTIC-TITLE-GENERIC"}

    mismatched = _parse(
        "<html><head><title>Acme Corporation</title></head>"
        "<body><h1>Annual Report</h1></body></html>"
    )
    assert {
        f["rule_id"] for f in site_audit._title_findings("https://example.com/report", mismatched)
    } == {"HEURISTIC-TITLE-NOT-DESCRIPTIVE"}


def test_title_quality_silent_when_title_matches_the_page():
    parser = _parse(
        "<html><head><title>Annual Report 2026</title></head>"
        "<body><h1>Annual Report</h1></body></html>"
    )
    assert site_audit._title_findings("https://example.com/report", parser) == []


def test_duplicate_titles_are_flagged_across_pages():
    pages = [
        {"url": "https://example.com/a", "result": "ok", "title": "Lions Clubs", "findings": []},
        {"url": "https://example.com/b", "result": "ok", "title": "Lions Clubs", "findings": []},
        {"url": "https://example.com/c", "result": "ok", "title": "Unique Page", "findings": []},
    ]
    findings = site_audit._duplicate_title_findings(pages)
    assert len(findings) == 2
    assert all(f["rule_id"] == "HEURISTIC-TITLE-DUPLICATE" for f in findings)
    # The finding is attached to each affected page, and counts stay in sync.
    assert pages[0]["finding_count"] == 1
    assert pages[2]["findings"] == []


def test_best_practice_findings_are_labelled_and_carry_plain_guidance():
    parser = _parse(_sparse_page_html())
    findings = site_audit._heading_findings("https://example.com/x.php", parser)
    assert findings
    for finding in findings:
        assert finding["best_practice"] is True
        assert finding["guidance"], f"{finding['rule_id']} has no plain-language guidance"
    # Conformance failures are not mislabelled as best practice.
    conformance = site_audit._finding(
        "https://example.com/", "HEURISTIC-IMG-ALT", "serious", "m", "img"
    )
    assert conformance["best_practice"] is False
    assert conformance["guidance"]


def test_best_practice_checks_can_be_switched_off(monkeypatch, tmp_path):
    resp = _FakeResp(_sparse_page_html().encode("utf-8"), "text/html; charset=utf-8")
    monkeypatch.setattr(site_audit, "_http_get", lambda url, timeout=20: resp)
    monkeypatch.setattr(site_audit, "_axe_available", lambda: False)
    page_dir = tmp_path / "p"
    page_dir.mkdir()

    on = site_audit._scan_single_page("https://example.com/x.php", page_dir)
    off = site_audit._scan_single_page(
        "https://example.com/x.php",
        page_dir,
        check_heading_structure=False,
        check_title_quality=False,
    )
    assert any(f["best_practice"] for f in on["findings"])
    assert not any(f["best_practice"] for f in off["findings"])


def test_run_axe_prefers_installed_binary_over_npx(monkeypatch, tmp_path):
    # npx downloads the package at scan time, which needs a writable npm cache
    # the container does not have. A build-time install must win.
    monkeypatch.setattr(
        site_audit.shutil,
        "which",
        lambda name: {"axe": "/usr/bin/axe", "chromedriver": "/usr/bin/chromedriver"}.get(name),
    )
    captured = {}

    class _Proc:
        returncode = 0
        stderr = ""
        stdout = ""

    def _fake_run(command, **kwargs):
        captured["command"] = command
        return _Proc()

    monkeypatch.setattr(site_audit.subprocess, "run", _fake_run)
    site_audit._run_axe("https://example.com/", tmp_path / "axe.json")
    command = captured["command"]
    assert command[0] == "/usr/bin/axe"
    assert "npx" not in " ".join(command)
    # Chrome cannot use its sandbox in an unprivileged container.
    assert any(
        str(arg).startswith("--chrome-options=") and "no-sandbox" in str(arg) for arg in command
    )
    assert "/usr/bin/chromedriver" in command


@pytest.mark.parametrize(
    "fragment,expected_text",
    [
        # A heading must close on its own end tag, not on the first nested one.
        # Closing early truncated the text and reported real headings as silent.
        ('<h2><span class="icon"></span>Projects</h2>', "Projects"),
        ("<h2><strong>A</strong> B <em>C</em></h2>", "A B C"),
        ('<h2><a href="/x">Our Projects</a></h2>', "Our Projects"),
        ('<div role="heading" aria-level="2"><div><span>Deep</span></div></div>', "Deep"),
        ("<h2>Dangling", "Dangling"),  # unclosed heading still recorded
    ],
)
def test_headings_close_on_their_own_tag(fragment, expected_text):
    parser = _parse(f"<html><body><h1>Top</h1>{fragment}</body></html>")
    assert [h.text for h in parser.headings] == ["Top", expected_text]
    rules = {f["rule_id"] for f in site_audit._heading_findings("https://example.com/", parser)}
    assert "HEURISTIC-HEADING-EMPTY" not in rules


def test_image_only_heading_is_silent_only_when_alt_is_empty():
    labelled = _parse('<html><body><h1>T</h1><h2><img src="a.png" alt="Projects"></h2></body></html>')
    assert labelled.headings[1].text == "Projects"
    assert labelled.headings[1].image_only is True
    assert "HEURISTIC-HEADING-EMPTY" not in {
        f["rule_id"] for f in site_audit._heading_findings("https://example.com/", labelled)
    }

    silent = _parse('<html><body><h1>T</h1><h2><img src="a.png" alt=""></h2></body></html>')
    assert silent.headings[1].text == ""
    assert "HEURISTIC-HEADING-EMPTY" in {
        f["rule_id"] for f in site_audit._heading_findings("https://example.com/", silent)
    }
