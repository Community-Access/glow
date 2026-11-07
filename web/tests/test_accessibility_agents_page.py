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
    body = client.get("/accessibility-agents/").get_data(as_text=True)
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
    body = client.get("/accessibility-agents/").get_data(as_text=True)
    assert 'for="aa-model-pick"' in body
    assert 'id="aa-models-button"' in body
    script = (STATIC / "accessibility-agents-ask.js").read_text(encoding="utf-8")
    assert '"models"' in script and "aa.models." in script
    assert "model.value.trim() || pick.value" in script
