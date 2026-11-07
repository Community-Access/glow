"""Ask Accessibility Agents a question, with the visitor's own AI key.

The visitor's key arrives with each request and is used for that request
only. It is never stored in the session, a cookie, a file or a log; the page
keeps it in the tab's sessionStorage, which the browser clears when the tab
or the browser closes.

The model answers as an accessibility specialist and may call the hosted
Accessibility Agents MCP server's tools (contrast, reading level, HTML
checks, guidelines). GLOW runs that tool loop here, because the page's
Content Security Policy only lets the browser talk to this site.

Providers:
    openai      api.openai.com, Chat Completions with function tools
    gemini      Google's OpenAI-compatible endpoint
    openrouter  openrouter.ai, OpenAI-compatible (and the PKCE key exchange)
    anthropic   api.anthropic.com, Messages with tools
"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any

import requests

#: Where GLOW reaches the hosted MCP server: inside the Docker network on the
#: server, the public address anywhere else.
MCP_URL = os.environ.get("A11Y_MCP_INTERNAL_URL", "http://a11y-mcp:3100/mcp")

PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {
        "label": "OpenAI",
        "style": "openai",
        "url": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o-mini",
        "key_url": "https://platform.openai.com/api-keys",
    },
    "gemini": {
        "label": "Google Gemini",
        "style": "openai",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "default_model": "gemini-2.5-flash",
        "key_url": "https://aistudio.google.com/app/apikey",
    },
    "anthropic": {
        "label": "Claude (Anthropic)",
        "style": "anthropic",
        "url": "https://api.anthropic.com/v1/messages",
        "default_model": "claude-haiku-5-5",
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    "openrouter": {
        "label": "OpenRouter",
        "style": "openai",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "openai/gpt-4o-mini",
        "key_url": "https://openrouter.ai/keys",
    },
}

OPENROUTER_KEY_EXCHANGE_URL = "https://openrouter.ai/api/v1/auth/keys"

MAX_QUESTION_CHARS = 8_000
MAX_MATERIAL_CHARS = 50_000
MAX_ROUNDS = 6
HTTP_TIMEOUT = 60

SYSTEM_PROMPT = (
    "You are Accessibility Agents, a team of accessibility specialists. Judge "
    "everything against WCAG 2.2 Level AA. For each problem, name the success "
    "criterion by number and name, say how severe it is (critical, serious, "
    "moderate or minor), say where it is, and give the fix. When a question "
    "needs a measurement, such as a contrast ratio, a reading level, or "
    "whether headings, link text or form labels in some HTML are correct, call "
    "the tool rather than estimating, and say that you did. If something "
    "cannot be checked from what you were given, say so plainly instead of "
    "guessing. Answer in plain language, with short paragraphs or lists. The "
    "person may use a screen reader: no tables wider than three columns, no "
    "decorative symbols."
)


class AskError(Exception):
    """A problem to show the visitor. Never carries the key."""


# ---------------------------------------------------------------------------
# The MCP server
# ---------------------------------------------------------------------------

def _mcp(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    try:
        resp = requests.post(
            MCP_URL,
            json=body,
            headers={"Accept": "application/json, text/event-stream"},
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise AskError("The Accessibility Agents server could not be reached.") from exc
    if resp.status_code != 200:
        raise AskError(f"The Accessibility Agents server answered {resp.status_code}.")
    text = resp.text.strip()
    if not text.startswith("{"):
        text = "".join(
            line[5:].strip() for line in text.splitlines() if line.startswith("data:")
        )
    message = json.loads(text)
    if "error" in message:
        raise AskError(message["error"].get("message", "The tool call failed."))
    return message.get("result") or {}


#: Tools the model is not offered: it only ever has the file's text, and
#: GLOW has already sent the file itself to the scanner (scan_file).
_NOT_FOR_THE_MODEL = {"scan_uploaded_document"}

#: Specialist names look like skill folder names.
_SPECIALIST_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,60}$")
MAX_SPECIALIST_CHARS = 24_000
MAX_SCAN_CHARS = 30_000


def list_tools() -> list[dict[str, Any]]:
    return [t for t in _mcp("tools/list").get("tools") or []
            if t.get("name") not in _NOT_FOR_THE_MODEL]


def scan_file(path: Path) -> dict[str, str]:
    """Scan a file with the server's own scanner. Returns {"report", "specialist"}.

    The bytes go to scan_uploaded_document, which writes them to a private
    folder, runs the Office, PDF, ePub, Markdown or HTML checks a local
    install runs, and deletes them before answering.
    """
    content = base64.b64encode(path.read_bytes()).decode("ascii")
    result = _mcp("tools/call", {"name": "scan_uploaded_document",
                                 "arguments": {"filename": path.name, "content_base64": content}})
    report = "\n".join(part.get("text", "") for part in result.get("content") or []).strip()
    if result.get("isError"):
        raise AskError(report or "The scanner could not read that file.")
    found = re.search(r"Specialist for this file: ([a-z0-9-]+)", report)
    return {"report": report[:MAX_SCAN_CHARS], "specialist": found.group(1) if found else ""}


def get_specialist(name: str) -> str:
    """One specialist's instructions (its SKILL.md), or "" when there is none."""
    if not _SPECIALIST_RE.match(name or ""):
        return ""
    try:
        result = _mcp("tools/call", {"name": "get_specialist", "arguments": {"name": name}})
    except AskError:
        return ""
    if result.get("isError"):
        return ""
    text = "\n".join(part.get("text", "") for part in result.get("content") or [])
    return text[:MAX_SPECIALIST_CHARS]


def call_tool(name: str, arguments: dict[str, Any]) -> str:
    result = _mcp("tools/call", {"name": name, "arguments": arguments})
    text = "\n".join(part.get("text", "") for part in result.get("content") or [])
    return text or json.dumps(result.get("structuredContent") or {})


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------

_CREDIT_WORDS = ("credit", "quota", "billing", "prepay", "balance", "insufficient")


def _provider_message(resp: requests.Response) -> str:
    """The provider's own error sentence, if it sent one (never contains the key)."""
    try:
        data = resp.json()
    except ValueError:
        return ""
    if isinstance(data, list) and data:
        data = data[0]
    err = data.get("error") if isinstance(data, dict) else None
    message = err.get("message") if isinstance(err, dict) else err if isinstance(err, str) else ""
    message = " ".join(str(message or "").split())
    return message[:300]


def _provider_error(resp: requests.Response, label: str) -> AskError:
    said = _provider_message(resp)
    if resp.status_code in (401, 403) and not any(w in said.lower() for w in _CREDIT_WORDS):
        return AskError(f"{label} did not accept the key. Check it and try again.")
    if resp.status_code == 402 or any(w in said.lower() for w in _CREDIT_WORDS):
        return AskError(f"{label} says this account is out of credit. Add credit with "
                        f"{label}, or choose OpenRouter or a free Gemini key." +
                        (f" {label} said: {said}" if said else ""))
    if resp.status_code == 429:
        return AskError(f"{label} says the key is over its rate limit. Wait a minute and try again.")
    if resp.status_code == 404:
        return AskError(f"{label} does not offer that model to this key. Choose Show my models.")
    return AskError(f"{label} answered {resp.status_code}." + (f" It said: {said}" if said else ""))


def _post(url: str, headers: dict[str, str], body: dict[str, Any], label: str) -> dict[str, Any]:
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        raise AskError(f"{label} could not be reached.") from exc
    if resp.status_code != 200:
        raise _provider_error(resp, label)
    return resp.json()


def _ask_openai_style(provider: dict[str, str], key: str, model: str,
                      user_text: str, tools: list[dict[str, Any]],
                      system: str = SYSTEM_PROMPT) -> tuple[str, list[str]]:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if provider["label"] == "OpenRouter":
        headers["HTTP-Referer"] = "https://letitglow.app/accessibility-agents"
        headers["X-Title"] = "Accessibility Agents on GLOW"
    functions = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema") or {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ]
    used: list[str] = []
    for _ in range(MAX_ROUNDS):
        data = _post(provider["url"], headers,
                     {"model": model, "messages": messages, "tools": functions},
                     provider["label"])
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        calls = message.get("tool_calls") or []
        if not calls:
            return str(message.get("content") or "").strip(), used
        messages.append({"role": "assistant", "content": message.get("content") or "",
                         "tool_calls": calls})
        for call in calls:
            fn = call.get("function") or {}
            name = str(fn.get("name") or "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            output = call_tool(name, args) if any(t["name"] == name for t in tools) else "Unknown tool."
            used.append(name)
            messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": output})
    raise AskError("The answer needed too many checks. Try a narrower question.")


def _ask_anthropic(provider: dict[str, str], key: str, model: str,
                   user_text: str, tools: list[dict[str, Any]],
                   system: str = SYSTEM_PROMPT) -> tuple[str, list[str]]:
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    tool_defs = [
        {
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("inputSchema") or {"type": "object", "properties": {}},
        }
        for t in tools
    ]
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_text}]
    used: list[str] = []
    for _ in range(MAX_ROUNDS):
        data = _post(provider["url"], headers,
                     {"model": model, "max_tokens": 4096, "system": system,
                      "messages": messages, "tools": tool_defs},
                     provider["label"])
        blocks = data.get("content") or []
        calls = [b for b in blocks if b.get("type") == "tool_use"]
        if not calls:
            return "\n\n".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip(), used
        messages.append({"role": "assistant", "content": blocks})
        results = []
        for call in calls:
            name = str(call.get("name") or "")
            output = (call_tool(name, call.get("input") or {})
                      if any(t["name"] == name for t in tools) else "Unknown tool.")
            used.append(name)
            results.append({"type": "tool_result", "tool_use_id": call.get("id"), "content": output})
        messages.append({"role": "user", "content": results})
    raise AskError("The answer needed too many checks. Try a narrower question.")


def ask(provider_id: str, key: str, model: str, question: str, material: str = "",
        source: str = "", scan: str = "", specialist: str = "") -> dict[str, Any]:
    """Answer one question. Returns {"answer", "tools_used", "provider", "model", "specialist"}.

    ``scan`` is the scanner's report on the file the text came from, and
    ``specialist`` the Accessibility Agents specialist whose instructions the
    model follows for that kind of file (word-accessibility for .docx, and so on).
    """
    provider = PROVIDERS.get(provider_id)
    if provider is None:
        raise AskError("Choose a provider.")
    key = (key or "").strip()
    if not key:
        raise AskError(f"Enter your {provider['label']} key first.")
    question = (question or "").strip()
    if not question:
        raise AskError("Type a question.")
    if len(question) > MAX_QUESTION_CHARS:
        raise AskError(f"Keep the question under {MAX_QUESTION_CHARS:,} characters.")
    material = (material or "").strip()
    if len(material) > MAX_MATERIAL_CHARS:
        raise AskError(f"Keep the pasted material under {MAX_MATERIAL_CHARS:,} characters.")
    model = (model or "").strip() or provider["default_model"]

    user_text = question
    if material:
        source = (source or "").strip()[:200]
        scan = (scan or "").strip()[:MAX_SCAN_CHARS]
        if source and scan:
            user_text += (
                f"\n\nThe file {source} was scanned with the Accessibility Agents "
                "document scanner, which read the original file (properties, styles, "
                "alt text, table headers, tags). Its report:\n\n" + scan +
                "\n\nThe file's text, converted to Markdown, follows. Base your review on "
                "the scan first and the text second, and say when something needs a "
                "person to check the original:\n\n" + material
            )
        elif source:
            user_text += (
                f"\n\nMaterial to review: the file {source}, converted to text. Headings, "
                "lists, tables, links and image alt text survive the conversion as "
                "Markdown; fonts, colors, reading order tags and document properties do "
                "not, so say which checks need the original file:\n\n" + material
            )
        else:
            user_text += "\n\nMaterial to review (text, HTML or colors):\n\n" + material

    system = SYSTEM_PROMPT
    instructions = get_specialist((specialist or "").strip()) if specialist else ""
    if instructions:
        system += (
            f"\n\nFor this review you are the {specialist} specialist. Follow its "
            "instructions below. Where they mention tools or files you do not have, "
            "use the scan report and the text you were given instead.\n\n" + instructions +
            "\n\nHow to answer, which overrides any output format above: a person "
            "reads this on a web page, often with a screen reader. Write plain "
            "language, never JSON, YAML or code blocks. Start with one sentence on "
            "how the file does overall, then list each problem with its WCAG "
            "criterion, severity, where it is, and how to fix it in the program the "
            "file came from, most severe first. End with what needs a person to "
            "check in the original."
        )

    tools = list_tools()
    if provider["style"] == "anthropic":
        answer, used = _ask_anthropic(provider, key, model, user_text, tools, system)
    else:
        answer, used = _ask_openai_style(provider, key, model, user_text, tools, system)
    return {
        "answer": answer or "The model returned no answer.",
        "tools_used": sorted(set(used)),
        "provider": provider["label"],
        "model": model,
        "specialist": specialist if instructions else "",
    }


# ---------------------------------------------------------------------------
# The models a key can use
# ---------------------------------------------------------------------------

MODELS_URLS = {
    "openai": "https://api.openai.com/v1/models",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
    "anthropic": "https://api.anthropic.com/v1/models?limit=1000",
    "openrouter": "https://openrouter.ai/api/v1/models?supported_parameters=tools",
}

#: Words in an OpenAI or Gemini model id that mean it cannot chat with tools.
_NOT_CHAT = ("embedding", "embed", "tts", "audio", "realtime", "transcribe",
             "image", "dall-e", "whisper", "moderation", "search", "instruct",
             "davinci", "babbage", "aqa", "imagen", "veo", "computer-use", "live")


def _is_chat(model_id: str) -> bool:
    lowered = model_id.lower()
    return not any(word in lowered for word in _NOT_CHAT)


def list_models(provider_id: str, key: str) -> list[dict[str, str]]:
    """The chat models this key can use, as [{"id", "name"}], sorted by name.

    OpenRouter's catalogue is public, so its key is optional here.
    """
    provider = PROVIDERS.get(provider_id)
    if provider is None:
        raise AskError("Choose a provider.")
    key = (key or "").strip()
    if not key and provider_id != "openrouter":
        raise AskError(f"Enter your {provider['label']} key first.")
    headers: dict[str, str] = {}
    if provider_id == "anthropic":
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    elif provider_id == "gemini":
        headers = {"x-goog-api-key": key}
    elif key:
        headers = {"Authorization": f"Bearer {key}"}
    try:
        resp = requests.get(MODELS_URLS[provider_id], headers=headers, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        raise AskError(f"{provider['label']} could not be reached.") from exc
    if resp.status_code != 200:
        raise _provider_error(resp, provider["label"])
    data = resp.json() or {}

    models: list[dict[str, str]] = []
    if provider_id == "gemini":
        for m in data.get("models") or []:
            model_id = str(m.get("name") or "").removeprefix("models/")
            if ("generateContent" in (m.get("supportedGenerationMethods") or [])
                    and model_id.startswith("gemini") and _is_chat(model_id)):
                models.append({"id": model_id, "name": str(m.get("displayName") or model_id)})
    else:
        for m in data.get("data") or []:
            model_id = str(m.get("id") or "")
            if not model_id:
                continue
            if provider_id == "openai" and not (
                    model_id.startswith(("gpt-", "o1", "o3", "o4", "chatgpt-")) and _is_chat(model_id)):
                continue
            name = str(m.get("display_name") or m.get("name") or model_id)
            models.append({"id": model_id, "name": name})
    seen: set[str] = set()
    unique = [m for m in models if not (m["id"] in seen or seen.add(m["id"]))]
    return sorted(unique, key=lambda m: m["name"].lower())


def exchange_openrouter_code(code: str, code_verifier: str) -> str:
    """Trade an OpenRouter sign-in code for the visitor's key (PKCE, S256)."""
    if not code or not code_verifier:
        raise AskError("The OpenRouter sign-in did not finish. Try again.")
    try:
        resp = requests.post(
            OPENROUTER_KEY_EXCHANGE_URL,
            json={"code": code, "code_verifier": code_verifier, "code_challenge_method": "S256"},
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise AskError("OpenRouter could not be reached.") from exc
    if resp.status_code != 200:
        raise AskError("OpenRouter did not accept the sign-in. Try again.")
    key = str((resp.json() or {}).get("key") or "")
    if not key:
        raise AskError("OpenRouter returned no key. Try again.")
    return key
