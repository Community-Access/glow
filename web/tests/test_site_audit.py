from __future__ import annotations

from pathlib import Path
import json
import hashlib
import time

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
import acb_large_print_web.routes.site_audit as site_audit_route
import acb_large_print_web.site_audit as site_audit


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

    def _fake_get(url: str, timeout: int, headers: dict[str, str]):
        return _Resp(url, pages.get(url, ""))

    monkeypatch.setattr(site_audit.requests, "get", _fake_get)

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

    def _fake_get(url: str, timeout: int, headers: dict[str, str]):
        return _Resp(url, pages.get(url, ""))

    monkeypatch.setattr(site_audit.requests, "get", _fake_get)

    urls = site_audit._expand_with_crawl(
        ["https://example.com"],
        max_pages=10,
        crawl_depth=2,
        include_subdomains=False,
        same_path_only=False,
        exclude_url_patterns=("/blog/",),
    )
    assert urls == ["https://example.com", "https://example.com/about"]


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
