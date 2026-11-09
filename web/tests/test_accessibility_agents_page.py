"""The Accessibility Agents page: its route, nav entry, forms and script."""

from __future__ import annotations

from pathlib import Path

import pytest

from acb_large_print_web.app import create_app
from acb_large_print_web.routes.consent import CONSENT_COOKIE_NAME

STATIC = Path(__file__).resolve().parents[1] / "src" / "acb_large_print_web" / "static"


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    app.instance_path = str(tmp_path / "instance")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    c = app.test_client()
    c.set_cookie(CONSENT_COOKIE_NAME, "1")
    return c


def test_page_renders_with_one_h1_and_the_server_address(client):
    resp = client.get("/accessibility-agents/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert body.count("<h1") == 1
    assert "https://letitglow.app/a11y/mcp" in body
    assert 'aria-current="page"' in body  # the nav entry marks itself


def test_page_separates_hosted_checks_from_upload_chat_and_local_plugins(client):
    body = " ".join(client.get("/accessibility-agents/").get_data(as_text=True).split())
    for text in (
        "offers twelve tools",
        "stores a temporary copy while it works",
        "public sharing link that the server fetches",
        "one hour, then deleted",
        "GLOW's own chat above",
        "after optional dependencies are installed",
        "full plugin submission was refused under directory policy",
        "but not review hooks",
    ):
        assert text in body
    assert "cannot reach into your computer" in body
    assert "cannot scan files or fetch websites" not in body
    assert "full Accessibility Agents plugin is in review" not in body


def test_accessibility_agents_page_links_to_the_standalone_chat(client):
    body = client.get("/accessibility-agents/").get_data(as_text=True)
    assert 'id="aa-ask-form"' not in body
    assert 'href="/accessibility-agents/chat/"' in body
    assert "Open Accessibility Agents chat" in body


def test_short_aa_url_redirects_to_the_accessibility_agents_page(client):
    resp = client.get("/aa")
    assert resp.status_code == 301
    assert resp.headers["Location"].endswith("/accessibility-agents/")


def test_chat_page_has_one_h1_accessible_form_and_no_focus_stealing(client):
    body = client.get("/accessibility-agents/chat/").get_data(as_text=True)
    assert body.count("<h1") == 1
    assert 'id="aa-ask-form"' in body
    assert 'data-api-base="/accessibility-agents/"' in body
    assert 'data-return-url="/accessibility-agents/chat/"' in body
    assert 'id="aa-ask-status" class="aa-status" role="status" aria-live="polite"' in body
    for field_id in ("aa-provider", "aa-key", "aa-model", "aa-question", "aa-material", "aa-file"):
        assert f'for="{field_id}"' in body, f"{field_id} has no label"
    assert "accessibility-agents-ask.js" in body
    script = (STATIC / "accessibility-agents-ask.js").read_text(encoding="utf-8")
    assert "answerHeading.focus()" not in script
    assert "Answer ready. The answer is below." in script


def test_every_field_has_a_label(client):
    body = client.get("/accessibility-agents/").get_data(as_text=True)
    for field_id in ("aa-foreground", "aa-background", "aa-apca", "aa-text", "aa-html", "aa-html-check", "aa-component"):
        assert f'id="{field_id}"' in body
        assert f'for="{field_id}"' in body, f"{field_id} has no label"


def test_results_and_status_are_announced(client):
    body = client.get("/accessibility-agents/").get_data(as_text=True)
    assert 'id="aa-status"' in body and 'role="status"' in body
    assert 'id="aa-result-heading" tabindex="-1"' in body


def test_script_is_loaded_with_the_page_nonce_and_calls_the_hosted_server(client):
    body = client.get("/accessibility-agents/").get_data(as_text=True)
    assert "accessibility-agents-check.js" in body
    script = (STATIC / "accessibility-agents-check.js").read_text(encoding="utf-8")
    assert '"/a11y/mcp"' in script
    for tool in ("check_contrast", "check_apca_contrast", "check_reading_level",
                 "get_accessibility_guidelines"):
        assert tool in script


# ---------------------------------------------------------------------------
# Asking with the visitor's own key
# ---------------------------------------------------------------------------

import json as _json  # noqa: E402

from acb_large_print_web import aa_ask  # noqa: E402


class _Resp:
    def __init__(self, status, payload, text=None):
        self.status_code = status
        self._payload = payload
        self.text = text if text is not None else _json.dumps(payload)

    def json(self):
        return self._payload


TOOLS = [{"name": "check_contrast", "description": "Contrast",
          "inputSchema": {"type": "object", "properties": {"foreground": {"type": "string"},
                                                           "background": {"type": "string"}}}}]


def _fake_post(calls, replies):
    def fake(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers or {}})
        if url == aa_ask.MCP_URL:
            if json["method"] == "tools/list":
                return _Resp(200, {"jsonrpc": "2.0", "id": 1, "result": {"tools": TOOLS}})
            return _Resp(200, None, text='event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"Contrast Ratio: 4.54:1"}]}}\n')
        return replies.pop(0)
    return fake


def test_ask_runs_the_tool_loop_and_keeps_no_key(client, monkeypatch):
    calls = []
    replies = [
        _Resp(200, {"choices": [{"message": {"content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "check_contrast",
             "arguments": '{"foreground":"#767676","background":"#ffffff"}'}}]}}]}),
        _Resp(200, {"choices": [{"message": {"content": "It passes 1.4.3 at 4.54:1."}}]}),
    ]
    monkeypatch.setattr(aa_ask.requests, "post", _fake_post(calls, replies))
    resp = client.post("/accessibility-agents/ask", json={
        "provider": "openai", "key": "sk-test-secret", "question": "Does #767676 on white pass?"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["answer"] == "It passes 1.4.3 at 4.54:1."
    assert data["tools_used"] == ["check_contrast"]
    assert resp.headers["Cache-Control"] == "no-store"
    # The key went to the provider and nowhere else, and nothing was stored.
    provider_calls = [c for c in calls if c["url"] != aa_ask.MCP_URL]
    assert all(c["headers"]["Authorization"] == "Bearer sk-test-secret" for c in provider_calls)
    assert all("sk-test-secret" not in _json.dumps(c["json"]) for c in calls)
    assert "sk-test-secret" not in resp.headers.get("Set-Cookie", "")
    with client.session_transaction() as sess:
        assert "sk-test-secret" not in _json.dumps(dict(sess), default=str)


def test_ask_with_claude_uses_the_messages_api(client, monkeypatch):
    calls = []
    replies = [_Resp(200, {"content": [{"type": "text", "text": "Use a visible label (3.3.2)."}]})]
    monkeypatch.setattr(aa_ask.requests, "post", _fake_post(calls, replies))
    resp = client.post("/accessibility-agents/ask", json={
        "provider": "anthropic", "key": "sk-ant-test", "question": "Is a placeholder enough?"})
    assert resp.status_code == 200
    provider_call = [c for c in calls if c["url"] == aa_ask.PROVIDERS["anthropic"]["url"]][0]
    assert provider_call["headers"]["x-api-key"] == "sk-ant-test"
    assert provider_call["json"]["tools"][0]["name"] == "check_contrast"


def test_a_rejected_key_gives_a_plain_message(client, monkeypatch):
    calls = []
    monkeypatch.setattr(aa_ask.requests, "post", _fake_post(calls, [_Resp(401, {})]))
    resp = client.post("/accessibility-agents/ask", json={
        "provider": "gemini", "key": "bad", "question": "Hello?"})
    assert resp.status_code == 400
    assert "did not accept the key" in resp.get_json()["error"]


def test_missing_key_is_refused_before_any_call(client, monkeypatch):
    calls = []
    monkeypatch.setattr(aa_ask.requests, "post", _fake_post(calls, []))
    resp = client.post("/accessibility-agents/ask", json={"provider": "openai", "question": "Hi"})
    assert resp.status_code == 400
    assert calls == []


def test_openrouter_exchange_returns_the_key_and_stores_nothing(client, monkeypatch):
    seen = {}

    def fake(url, json=None, headers=None, timeout=None):
        seen.update(url=url, json=json)
        return _Resp(200, {"key": "sk-or-test"})

    monkeypatch.setattr(aa_ask.requests, "post", fake)
    resp = client.post("/accessibility-agents/openrouter/exchange",
                       json={"code": "abc", "code_verifier": "xyz"})
    assert resp.status_code == 200
    assert resp.get_json() == {"key": "sk-or-test"}
    assert seen["url"] == aa_ask.OPENROUTER_KEY_EXCHANGE_URL
    assert seen["json"]["code_challenge_method"] == "S256"
    with client.session_transaction() as sess:
        assert "sk-or-test" not in _json.dumps(dict(sess), default=str)


def test_ask_form_fields_are_labelled(client):
    body = client.get("/accessibility-agents/chat/").get_data(as_text=True)
    for field_id in ("aa-provider", "aa-key", "aa-model", "aa-question", "aa-material"):
        assert f'for="{field_id}"' in body, f"{field_id} has no label"
    assert 'type="password" id="aa-key"' in body
    for label in ("OpenAI", "Google Gemini", "Claude (Anthropic)", "OpenRouter"):
        assert label in body


def _fake_get(seen, resp):
    def fake(url, headers=None, timeout=None):
        seen.update(url=url, headers=headers or {})
        return resp
    return fake


def test_models_lists_only_chat_models_for_openai(client, monkeypatch):
    seen = {}
    payload = {"data": [{"id": "gpt-4o-mini"}, {"id": "text-embedding-3-small"},
                        {"id": "gpt-4o-realtime-preview"}, {"id": "o3-mini"},
                        {"id": "whisper-1"}, {"id": "gpt-4o-mini"}]}
    monkeypatch.setattr(aa_ask.requests, "get", _fake_get(seen, _Resp(200, payload)))
    resp = client.post("/accessibility-agents/models", json={"provider": "openai", "key": "sk-test"})
    assert resp.status_code == 200
    assert [m["id"] for m in resp.get_json()["models"]] == ["gpt-4o-mini", "o3-mini"]
    assert seen["headers"]["Authorization"] == "Bearer sk-test"
    assert resp.headers["Cache-Control"] == "no-store"


def test_models_for_gemini_keeps_the_key_out_of_the_url(client, monkeypatch):
    seen = {}
    payload = {"models": [
        {"name": "models/gemini-2.5-flash", "displayName": "Gemini 2.5 Flash",
         "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["generateContent"]},
    ]}
    monkeypatch.setattr(aa_ask.requests, "get", _fake_get(seen, _Resp(200, payload)))
    resp = client.post("/accessibility-agents/models", json={"provider": "gemini", "key": "AIza-test"})
    assert resp.get_json()["models"] == [{"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"}]
    assert "AIza-test" not in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == "AIza-test"


def test_models_for_claude_and_openrouter(client, monkeypatch):
    seen = {}
    monkeypatch.setattr(aa_ask.requests, "get", _fake_get(seen, _Resp(200, {"data": [
        {"id": "claude-haiku-5-5", "display_name": "Claude Haiku 5.5"}]})))
    resp = client.post("/accessibility-agents/models", json={"provider": "anthropic", "key": "sk-ant"})
    assert resp.get_json()["models"][0]["name"] == "Claude Haiku 5.5"
    assert seen["headers"]["x-api-key"] == "sk-ant"
    # OpenRouter's catalogue is public: no key needed, and only tool-capable models.
    resp = client.post("/accessibility-agents/models", json={"provider": "openrouter"})
    assert resp.status_code == 200
    assert "supported_parameters=tools" in seen["url"]


def test_models_needs_a_key_and_reports_a_bad_one(client, monkeypatch):
    seen = {}
    monkeypatch.setattr(aa_ask.requests, "get", _fake_get(seen, _Resp(401, {})))
    resp = client.post("/accessibility-agents/models", json={"provider": "openai"})
    assert resp.status_code == 400 and seen == {}
    resp = client.post("/accessibility-agents/models", json={"provider": "openai", "key": "bad"})
    assert "did not accept the key" in resp.get_json()["error"]


def test_model_pick_list_is_labelled_and_wired(client):
    body = client.get("/accessibility-agents/chat/").get_data(as_text=True)
    assert 'for="aa-model-pick"' in body
    assert 'id="aa-models-button"' in body
    script = (STATIC / "accessibility-agents-ask.js").read_text(encoding="utf-8")
    assert '"models"' in script and "aa.models." in script
    assert "model.value.trim() || pick.value" in script


def test_extract_reads_an_html_file_and_keeps_nothing(client):
    import io

    from acb_large_print_web.upload import UPLOAD_TEMP_BASE

    before = set(UPLOAD_TEMP_BASE.iterdir()) if UPLOAD_TEMP_BASE.exists() else set()
    resp = client.post("/accessibility-agents/extract", content_type="multipart/form-data",
                       data={"file": (io.BytesIO(b"<h1>Title</h1><h3>Skipped</h3>"), "page.html")})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["text"] == "<h1>Title</h1><h3>Skipped</h3>"
    assert data["kind"] == "HTML" and data["truncated"] is False
    assert resp.headers["Cache-Control"] == "no-store"
    after = set(UPLOAD_TEMP_BASE.iterdir()) if UPLOAD_TEMP_BASE.exists() else set()
    assert after <= before, "the uploaded file was kept"


def test_extract_converts_a_word_file(client):
    import io

    import docx

    doc = docx.Document()
    doc.add_heading("Syllabus", level=1)
    doc.add_paragraph("Click here for the reading list.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    resp = client.post("/accessibility-agents/extract", content_type="multipart/form-data",
                       data={"file": (buf, "syllabus.docx")})
    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json()
    assert data["kind"] == "DOCX"
    assert "Syllabus" in data["text"] and "reading list" in data["text"]


def test_extract_refuses_other_files(client):
    import io

    resp = client.post("/accessibility-agents/extract", content_type="multipart/form-data",
                       data={"file": (io.BytesIO(b"MZ"), "tool.exe")})
    assert resp.status_code == 400
    assert "not supported" in resp.get_json()["error"]
    resp = client.post("/accessibility-agents/extract", content_type="multipart/form-data",
                       data={"file": (io.BytesIO(b"not a zip"), "fake.docx")})
    assert resp.status_code == 400


def test_ask_names_the_file_it_reviews(client, monkeypatch):
    calls = []
    replies = [_Resp(200, {"choices": [{"message": {"content": "Heading 3 skips a level."}}]})]
    monkeypatch.setattr(aa_ask.requests, "post", _fake_post(calls, replies))
    resp = client.post("/accessibility-agents/ask", json={
        "provider": "openai", "key": "sk-test", "question": "Review this.",
        "material": "# Title", "source": "syllabus.docx (DOCX)"})
    assert resp.status_code == 200
    sent = [c for c in calls if c["url"] == aa_ask.PROVIDERS["openai"]["url"]][0]
    assert "the file syllabus.docx (DOCX), converted to text" in sent["json"]["messages"][1]["content"]


def test_file_chooser_is_labelled(client):
    body = client.get("/accessibility-agents/chat/").get_data(as_text=True)
    assert 'for="aa-file"' in body and 'type="file" id="aa-file"' in body


@pytest.mark.parametrize("status, payload", [
    (429, {"error": {"message": "You have no credits remaining.", "code": "credit_balance_exhausted"}}),
    (402, [{"error": {"code": 402, "message": "Your prepayment credits are depleted."}}]),
    (400, {"type": "error", "error": {"message": "Your credit balance is too low."}}),
])
def test_an_empty_account_says_so(client, monkeypatch, status, payload):
    monkeypatch.setattr(aa_ask.requests, "post", _fake_post([], [_Resp(status, payload)]))
    resp = client.post("/accessibility-agents/ask", json={
        "provider": "openai", "key": "sk-test", "question": "Hi"})
    error = resp.get_json()["error"]
    assert "out of credit" in error
    assert "sk-test" not in error


_REAL_SCAN_FILE = aa_ask.scan_file


@pytest.fixture(autouse=True)
def _no_live_scanner(monkeypatch):
    """Extract tests never reach the real MCP server."""
    monkeypatch.setattr(aa_ask, "scan_file", lambda path: {"report": "", "specialist": ""})


def test_extract_returns_the_scanners_report_and_specialist(client, monkeypatch):
    import io

    seen = {}

    def fake_scan(path):
        seen["name"] = path.name
        seen["bytes"] = path.read_bytes()
        return {"report": "Scan complete: syllabus.docx\nIssues: 2\n[ERROR] doc-alt-text: no alt text",
                "specialist": "word-accessibility"}

    monkeypatch.setattr(aa_ask, "scan_file", fake_scan)
    import docx

    doc = docx.Document()
    doc.add_paragraph("Hello")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    resp = client.post("/accessibility-agents/extract", content_type="multipart/form-data",
                       data={"file": (buf, "syllabus.docx")})
    data = resp.get_json()
    assert resp.status_code == 200, data
    assert data["specialist"] == "word-accessibility"
    assert data["issues"] == 2
    assert "doc-alt-text" in data["scan"]
    assert seen["name"] == "syllabus.docx" and seen["bytes"][:2] == b"PK"


def test_scan_file_sends_the_bytes_and_reads_the_specialist(tmp_path, monkeypatch):
    import base64

    calls = []

    def fake(url, json=None, headers=None, timeout=None):
        calls.append(json)
        text = "Scan complete: a.pdf\nIssues: 1\n\nSpecialist for this file: pdf-accessibility (load it with get_specialist)."
        return _Resp(200, {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": text}]}})

    monkeypatch.setattr(aa_ask.requests, "post", fake)
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF-1.4 test")
    result = _REAL_SCAN_FILE(f)
    assert result["specialist"] == "pdf-accessibility"
    args = calls[0]["params"]["arguments"]
    assert calls[0]["params"]["name"] == "scan_uploaded_document"
    assert base64.b64decode(args["content_base64"]) == b"%PDF-1.4 test"


def test_ask_follows_the_specialist_and_gives_the_model_the_scan(client, monkeypatch):
    calls = []

    def fake(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json})
        if url == aa_ask.MCP_URL:
            if json["method"] == "tools/list":
                return _Resp(200, {"jsonrpc": "2.0", "id": 1, "result": {"tools": TOOLS + [
                    {"name": "scan_uploaded_document", "inputSchema": {"type": "object"}}]}})
            return _Resp(200, {"jsonrpc": "2.0", "id": 1, "result": {"content": [
                {"type": "text", "text": "# Word specialist\nCheck heading styles."}]}})
        return _Resp(200, {"choices": [{"message": {"content": "Image 1 needs alt text (1.1.1)."}}]})

    monkeypatch.setattr(aa_ask.requests, "post", fake)
    resp = client.post("/accessibility-agents/ask", json={
        "provider": "openrouter", "key": "sk-or-test", "question": "Review it.",
        "material": "# Syllabus", "source": "syllabus.docx (DOCX)",
        "scan": "[ERROR] doc-alt-text: Image 1 has no alt text", "specialist": "word-accessibility"})
    data = resp.get_json()
    assert resp.status_code == 200, data
    assert data["specialist"] == "word-accessibility"
    model_call = [c for c in calls if c["url"] == aa_ask.PROVIDERS["openrouter"]["url"]][0]
    system = model_call["json"]["messages"][0]["content"]
    user = model_call["json"]["messages"][1]["content"]
    assert "word-accessibility specialist" in system and "Check heading styles." in system
    assert "never JSON" in system and system.index("never JSON") > system.index("Check heading styles.")
    assert "doc-alt-text" in user and "scanned with the Accessibility Agents" in user
    # The model only has the text, so it is not offered the upload scanner.
    assert [t["function"]["name"] for t in model_call["json"]["tools"]] == ["check_contrast"]


def test_a_bad_specialist_name_is_never_fetched(client, monkeypatch):
    calls = []
    replies = [_Resp(200, {"choices": [{"message": {"content": "OK"}}]})]
    monkeypatch.setattr(aa_ask.requests, "post", _fake_post(calls, replies))
    resp = client.post("/accessibility-agents/ask", json={
        "provider": "openai", "key": "sk-test", "question": "Hi", "specialist": "../../etc"})
    assert resp.get_json()["specialist"] == ""
    assert not any(c["json"].get("params", {}).get("name") == "get_specialist"
                   for c in calls if c["url"] == aa_ask.MCP_URL)


def test_scanner_report_region_is_on_the_page(client):
    body = client.get("/accessibility-agents/chat/").get_data(as_text=True)
    assert 'id="aa-scan"' in body and "<summary>Scanner report</summary>" in body


_PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4"
        "z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC")


def _image_fake(calls, answer):
    def fake(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json})
        if url == aa_ask.MCP_URL:
            if json["method"] == "tools/list":
                return _Resp(200, {"jsonrpc": "2.0", "id": 1, "result": {"tools": TOOLS}})
            return _Resp(200, {"jsonrpc": "2.0", "id": 1, "result": {"content": [
                {"type": "text", "text": "# Alt text specialist"}]}})
        return answer
    return fake


def test_an_image_goes_to_the_model_with_the_alt_text_specialist(client, monkeypatch):
    calls = []
    answer = _Resp(200, {"choices": [{"message": {"content": "Alt text: A red dot."}}]})
    monkeypatch.setattr(aa_ask.requests, "post", _image_fake(calls, answer))
    resp = client.post("/accessibility-agents/ask", json={
        "provider": "gemini", "key": "k", "question": "Write alt text.",
        "image": _PNG, "source": "dot.png"})
    data = resp.get_json()
    assert resp.status_code == 200, data
    assert data["specialist"] == "alt-text-headings"
    model = [c for c in calls if c["url"] == aa_ask.PROVIDERS["gemini"]["url"]][0]["json"]
    parts = model["messages"][1]["content"]
    assert parts[1]["image_url"]["url"] == _PNG
    assert "dot.png" in parts[0]["text"]
    assert "Alt text: one line" in model["messages"][0]["content"]
    assert [c["json"]["params"]["arguments"] for c in calls
            if c["url"] == aa_ask.MCP_URL and c["json"]["method"] == "tools/call"] == [
        {"name": "alt-text-headings"}]


def test_an_image_to_claude_uses_an_image_block(client, monkeypatch):
    calls = []
    answer = _Resp(200, {"content": [{"type": "text", "text": "Alt text: A red dot."}]})
    monkeypatch.setattr(aa_ask.requests, "post", _image_fake(calls, answer))
    resp = client.post("/accessibility-agents/ask", json={
        "provider": "anthropic", "key": "k", "question": "Alt text?", "image": _PNG})
    assert resp.status_code == 200
    model = [c for c in calls if c["url"] == aa_ask.PROVIDERS["anthropic"]["url"]][0]["json"]
    block = model["messages"][0]["content"][0]
    assert block["type"] == "image" and block["source"]["media_type"] == "image/png"


def test_bad_images_are_refused_before_any_call(client, monkeypatch):
    calls = []
    monkeypatch.setattr(aa_ask.requests, "post", _image_fake(calls, None))
    for bad in ("data:image/svg+xml;base64,PHN2Zz4=", "data:text/html;base64,PGI+",
                "https://example.com/a.png", "data:image/png;base64,!!!"):
        resp = client.post("/accessibility-agents/ask", json={
            "provider": "openai", "key": "k", "question": "Alt?", "image": bad})
        assert resp.status_code == 400, bad
    big = "data:image/png;base64," + "A" * (7 * 1024 * 1024)
    resp = client.post("/accessibility-agents/ask", json={
        "provider": "openai", "key": "k", "question": "Alt?", "image": big})
    assert "under 5 MB" in resp.get_json()["error"]
    assert calls == []


def test_the_file_chooser_takes_images(client):
    body = client.get("/accessibility-agents/chat/").get_data(as_text=True)
    assert ".png,.jpg,.jpeg,.gif,.webp" in body and 'id="aa-image-help"' in body
    script = (STATIC / "accessibility-agents-ask.js").read_text(encoding="utf-8")
    assert "readAsDataURL" in script and "image: fileImage" in script


def test_answers_are_rendered_without_parsing_model_html():
    script = (STATIC / "accessibility-agents-ask.js").read_text(encoding="utf-8")
    assert "renderAnswer(answerBody, data.answer)" in script
    # The renderer builds nodes; it never hands model text to the HTML parser.
    assert "innerHTML" not in script and "insertAdjacentHTML" not in script


# ---- Alt text for every image in a document ----

def _png_bytes(color=(200, 30, 30)):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, "PNG")
    return buf.getvalue()


def _docx_with_two_images():
    import io

    import docx

    doc = docx.Document()
    doc.add_paragraph("Week one readings.")
    doc.add_picture(io.BytesIO(_png_bytes()))
    doc.add_paragraph("Enrollment by term.")
    doc.add_picture(io.BytesIO(_png_bytes((30, 30, 200))))
    doc.inline_shapes[0]._inline.docPr.set("descr", "Red square")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pptx_with_image():
    import io

    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Results"
    slide.shapes.add_picture(io.BytesIO(_png_bytes()), Inches(1), Inches(2))
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def test_images_lists_each_picture_with_a_key_and_keeps_nothing(client):
    import io

    from acb_large_print_web.upload import UPLOAD_TEMP_BASE

    before = set(UPLOAD_TEMP_BASE.iterdir()) if UPLOAD_TEMP_BASE.exists() else set()
    resp = client.post("/accessibility-agents/images", content_type="multipart/form-data",
                       data={"file": (io.BytesIO(_docx_with_two_images()), "syllabus.docx")})
    data = resp.get_json()
    assert resp.status_code == 200, data
    assert data["writable"] is True
    assert [i["key"] for i in data["images"]] == ["docx:1", "docx:2"]
    assert data["images"][0]["current_alt"] == "Red square"
    assert data["images"][1]["image"].startswith("data:image/png;base64,")
    after = set(UPLOAD_TEMP_BASE.iterdir()) if UPLOAD_TEMP_BASE.exists() else set()
    assert after <= before


def test_describe_returns_the_fields_from_the_model(client, monkeypatch):
    calls = []
    reply = ("Alt text: Bar chart of enrollment: Fall 120, Spring 90, Summer 40\n"
             "Decorative: no\nLong description: Three bars, highest in Fall.\nText in image: none")
    answer = _Resp(200, {"choices": [{"message": {"content": reply}}]})
    monkeypatch.setattr(aa_ask.requests, "post", _image_fake(calls, answer))
    resp = client.post("/accessibility-agents/describe", json={
        "provider": "openrouter", "key": "sk-or", "image": _PNG, "label": "Word image 2",
        "location": "Word document image 2", "context": ["Enrollment by term."]})
    data = resp.get_json()
    assert resp.status_code == 200, data
    assert data["alt"].startswith("Bar chart of enrollment")
    assert data["decorative"] is False and data["text_in_image"] == ""
    assert data["long"] == "Three bars, highest in Fall."
    model_call = [c for c in calls if c["url"] == aa_ask.PROVIDERS["openrouter"]["url"]][0]["json"]
    assert "tools" not in model_call
    assert "Enrollment by term." in model_call["messages"][1]["content"][0]["text"]


def test_write_alt_puts_the_alt_text_into_word(client):
    import io

    import docx

    resp = client.post("/accessibility-agents/write-alt", content_type="multipart/form-data", data={
        "file": (io.BytesIO(_docx_with_two_images()), "syllabus.docx"),
        "alts": _json.dumps({"docx:2": "Blue square", "../etc": "x", "docx:9": "missing"})})
    assert resp.status_code == 200, resp.get_data(as_text=True)[:200]
    assert resp.headers["X-Alt-Text-Written"] == "1"
    assert "syllabus-with-alt-text.docx" in resp.headers["Content-Disposition"]
    doc = docx.Document(io.BytesIO(resp.data))
    alts = [s._inline.docPr.get("descr") for s in doc.inline_shapes]
    assert alts == ["Red square", "Blue square"]


def test_write_alt_puts_the_alt_text_into_powerpoint(client):
    import io

    from pptx import Presentation

    listed = client.post("/accessibility-agents/images", content_type="multipart/form-data",
                         data={"file": (io.BytesIO(_pptx_with_image()), "talk.pptx")}).get_json()
    key = listed["images"][0]["key"]
    resp = client.post("/accessibility-agents/write-alt", content_type="multipart/form-data", data={
        "file": (io.BytesIO(_pptx_with_image()), "talk.pptx"), "alts": _json.dumps({key: "Red square"})})
    assert resp.status_code == 200
    prs = Presentation(io.BytesIO(resp.data))
    pics = [s for s in prs.slides[0].shapes if s.shape_type == 13]
    assert pics[0]._element.nvPicPr.cNvPr.get("descr") == "Red square"


def test_write_alt_refuses_files_it_cannot_write(client):
    import io

    resp = client.post("/accessibility-agents/write-alt", content_type="multipart/form-data", data={
        "file": (io.BytesIO(b"%PDF-1.4 x"), "a.pdf"), "alts": _json.dumps({"docx:1": "x"})})
    assert resp.status_code == 400
    resp = client.post("/accessibility-agents/write-alt", content_type="multipart/form-data", data={
        "file": (io.BytesIO(_docx_with_two_images()), "a.docx"), "alts": "not json"})
    assert resp.status_code == 400


def test_the_alt_text_controls_are_on_the_page(client):
    body = client.get("/accessibility-agents/chat/").get_data(as_text=True)
    assert 'id="aa-alt-button"' in body and 'id="aa-alt-heading"' in body
    assert 'id="aa-alt-download"' in body
    script = (STATIC / "accessibility-agents-ask.js").read_text(encoding="utf-8")
    assert '"write-alt"' in script and '"describe"' in script and '"images"' in script
