"""OpenRouter AI gateway with budget enforcement and quota tracking.

Single control plane for all AI inference in the GLOW web app.
Replaces on-device model servers with privacy-first open models.

Architecture
------------
Default path  : Privacy-reviewed OpenRouter models with ZDR + no-data-collection routing
Escalation    : Paid fallback model via OpenRouter (only when confidence < threshold)
Audio         : OpenRouter audio transcription endpoint (same OPENROUTER_API_KEY -- no extra key)
Budget        : $20/month hardcap tracked in SQLite cost ledger
Quotas        : 50 chat turns/day per anonymous session; 100 audio min/month

Server-side environment variables (NOT user-facing)
----------------------------------------------------
OPENROUTER_API_KEY      Required. Single key for all AI: chat, vision, and audio transcription.
AI_MONTHLY_BUDGET_USD   Hard cap USD (default 20.00)
AI_CHAT_DAILY_LIMIT     Chat turns per session per day (default 50)
AI_AUDIO_MONTHLY_MIN    Audio minutes per session per month (default 100)
AI_DEFAULT_MODEL        Primary OpenRouter model or comma list of models
AI_FALLBACK_MODEL       Escalation model or comma list of models
AI_VISION_MODEL         Vision-capable OpenRouter model for image analysis
AI_ESCALATION_THRESH    Confidence 0.0-1.0 below which escalation fires (default 0.7)

Privacy notes
-------------
- Requests are routed with provider-side privacy controls enabled whenever possible.
- GLOW uses OpenRouter provider filters (`dataCollection: deny`, `zdr: true`) for text requests.
- GLOW logs: metadata only -- no document text, no user content ever logged.
- All temp upload files deleted within 1 hour of job completion.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from .credentials import (
    get_openrouter_api_key,
    get_user_ollama_key,
    get_user_ollama_model,
    get_user_ollama_model_for,
    is_ollama_configured,
    get_ollama_cloud_url,
)
from .user_ai import (
    USER_AI_PROVIDER_DEFINITIONS,
    any_user_provider_configured,
    get_user_provider_models,
    infer_model_capabilities,
    format_model_ref,
    get_user_ai_provider_and_model_for,
    get_user_provider_key,
)

log = logging.getLogger(__name__)


def _raise_for_status_explicit(resp: requests.Response) -> None:
    if resp.status_code < 400:
        return
    raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)

# ---------------------------------------------------------------------------
# Configuration (resolved once at import time from environment)
# ---------------------------------------------------------------------------

_MONTHLY_BUDGET: float = float(os.environ.get("AI_MONTHLY_BUDGET_USD", "20.00"))
_CHAT_DAILY_LIMIT: int = int(os.environ.get("AI_CHAT_DAILY_LIMIT", "50"))
_AUDIO_MONTHLY_MIN: int = int(os.environ.get("AI_AUDIO_MONTHLY_MIN", "100"))
_DEFAULT_MODEL: str = os.environ.get(
    "AI_DEFAULT_MODEL", "openai/gpt-4o-mini"
)
_FALLBACK_MODEL: str = os.environ.get("AI_FALLBACK_MODEL", "openai/gpt-4o")
_VISION_MODEL: str = os.environ.get("AI_VISION_MODEL", "openai/gpt-4o-mini")
_ESCALATION_THRESH: float = float(os.environ.get("AI_ESCALATION_THRESH", "0.70"))
_WHISPER_MODEL: str = os.environ.get("WHISPER_MODEL", "openai/whisper-large-v3")
_SESSION_QUOTA_PER_SESSION: int = int(os.environ.get("GLOW_AI_QUOTA_PER_SESSION", "0"))
_SESSION_QUOTA_RESET_HOURS: int = int(os.environ.get("GLOW_AI_QUOTA_RESET_HOURS", "24"))

_DEFAULTS = {
    "monthly_budget_usd": _MONTHLY_BUDGET,
    "chat_daily_limit": _CHAT_DAILY_LIMIT,
    "audio_monthly_min": _AUDIO_MONTHLY_MIN,
    "default_model": _DEFAULT_MODEL,
    "fallback_model": _FALLBACK_MODEL,
    "vision_model": _VISION_MODEL,
    "escalation_thresh": _ESCALATION_THRESH,
    "whisper_model": _WHISPER_MODEL,
    "session_quota_per_session": _SESSION_QUOTA_PER_SESSION,
    "quota_reset_hours": _SESSION_QUOTA_RESET_HOURS,
}

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_OPENROUTER_AUDIO_URL = f"{_OPENROUTER_BASE}/audio/transcriptions"
_OPENROUTER_CHAT_URL = f"{_OPENROUTER_BASE}/chat/completions"
_OPENAI_BASE = "https://api.openai.com/v1"
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_REQUEST_TIMEOUT = 60  # seconds

# Ollama Cloud native API
_OLLAMA_CHAT_TIMEOUT = 120  # Ollama cloud models can be slower on cold start
_OPENROUTER_MAX_RETRIES = int(os.environ.get("OPENROUTER_MAX_RETRIES", "2"))
_OPENROUTER_RETRY_BASE_SECONDS = float(os.environ.get("OPENROUTER_RETRY_BASE_SECONDS", "1.0"))

# Cost table: USD per 1 million tokens (input / output)
_COST_TABLE: dict[str, dict[str, float]] = {
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    # gpt-audio-mini: audio tokens billed at text-token equivalents via OpenRouter
    "openai/gpt-audio-mini": {"input": 0.15, "output": 0.60},
    # Legacy free models (kept for accounts that set these via AI_DEFAULT_MODEL env var)
    "meta-llama/llama-3-8b-instruct:free": {"input": 0.0, "output": 0.0},
    "mistralai/mistral-7b-instruct:free": {"input": 0.0, "output": 0.0},
}

# Phrases that signal the model is uncertain → trigger escalation
_UNCERTAINTY_MARKERS = frozenset(
    [
        "i'm not sure",
        "i don't know",
        "i cannot determine",
        "unclear",
        "i'm unable to",
        "i cannot",
        "not enough information",
        "cannot be determined",
        "i don't have enough",
        "i am not sure",
        "uncertain",
        "i'm unsure",
    ]
)


# ---------------------------------------------------------------------------
# Public availability checks
# ---------------------------------------------------------------------------


def is_ai_configured() -> bool:
    """Return True if any AI provider is available.

    Ollama (user session key) takes priority over the server OpenRouter key.
    Either alone is sufficient to enable text-based AI features.
    """
    return is_ollama_configured() or any_user_provider_configured() or bool(get_openrouter_api_key())


def is_whisper_configured() -> bool:
    """Return True if OpenRouter is configured (BITS Whisperer uses the same key).

    Ollama does not support audio transcription, so this checks OpenRouter only.
    """
    return bool(get_user_provider_key("openrouter") or get_openrouter_api_key())


def _openrouter_key() -> str:
    return get_user_provider_key("openrouter") or get_openrouter_api_key()


def _model_ref(provider: str, model: str) -> str:
    return format_model_ref(provider, model)


def fetch_user_provider_models(provider: str, api_key: str) -> list[dict[str, Any]]:
    """Fetch a normalized model catalog for a user-supplied provider key."""
    provider = provider.strip().lower()
    if provider == "ollama":
        resp = requests.get(
            f"{get_ollama_cloud_url()}/tags",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        _raise_for_status_explicit(resp)
        raw = resp.json().get("models", [])
        out: list[dict[str, Any]] = []
        for item in raw:
            model_id = str(item.get("name") or item.get("model") or "").replace(":latest", "")
            if not model_id:
                continue
            out.append(
                {
                    "id": model_id,
                    "name": model_id,
                    "provider": provider,
                    "context_length": 0,
                    "input_per_million": None,
                    "output_per_million": None,
                    "note": "Available on your Ollama account.",
                    "capabilities": infer_model_capabilities(provider, model_id, model_name=model_id, raw=item),
                }
            )
        return out

    if provider == "openrouter":
        resp = requests.get(
            f"{_OPENROUTER_BASE}/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://letitglow.app",
                "X-Title": "GLOW",
            },
            timeout=20,
        )
        _raise_for_status_explicit(resp)
        raw = resp.json().get("data", [])
        out = []
        for item in raw:
            pricing = item.get("pricing", {}) or {}
            model_id = str(item.get("id") or "")
            model_name = str(item.get("name") or item.get("id") or "")
            context_length = int(item.get("context_length") or 0)
            out.append(
                {
                    "id": model_id,
                    "name": model_name,
                    "provider": provider,
                    "context_length": context_length,
                    "input_per_million": round(float(pricing.get("prompt", 0) or 0) * 1_000_000, 6),
                    "output_per_million": round(float(pricing.get("completion", 0) or 0) * 1_000_000, 6),
                    "note": "Pricing supplied by OpenRouter model catalog.",
                    "capabilities": infer_model_capabilities(provider, model_id, model_name=model_name, context_length=context_length, raw=item),
                }
            )
        out.sort(key=lambda value: (value.get("input_per_million") or 0, value.get("id") or ""))
        return out

    if provider == "openai":
        resp = requests.get(
            f"{_OPENAI_BASE}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        _raise_for_status_explicit(resp)
        raw = resp.json().get("data", [])
        out = []
        for item in raw:
            model_id = str(item.get("id") or "")
            if not model_id:
                continue
            out.append(
                {
                    "id": model_id,
                    "name": model_id,
                    "provider": provider,
                    "context_length": 0,
                    "input_per_million": None,
                    "output_per_million": None,
                    "note": "Pricing not provided by the OpenAI models endpoint.",
                    "capabilities": infer_model_capabilities(provider, model_id, model_name=model_id, raw=item),
                }
            )
        out.sort(key=lambda value: value.get("id") or "")
        return out

    if provider == "gemini":
        resp = requests.get(
            f"{_GEMINI_BASE}/models",
            params={"key": api_key},
            timeout=20,
        )
        _raise_for_status_explicit(resp)
        raw = resp.json().get("models", [])
        out = []
        for item in raw:
            name = str(item.get("name") or "")
            if not name:
                continue
            supported = item.get("supportedGenerationMethods") or []
            if "generateContent" not in supported:
                continue
            model_id = name.split("/", 1)[-1]
            out.append(
                {
                    "id": model_id,
                    "name": str(item.get("displayName") or model_id),
                    "provider": provider,
                    "context_length": int(item.get("inputTokenLimit") or 0),
                    "input_per_million": None,
                    "output_per_million": None,
                    "note": "Pricing not provided by the Gemini model list endpoint.",
                    "capabilities": infer_model_capabilities(provider, model_id, model_name=str(item.get("displayName") or model_id), context_length=int(item.get("inputTokenLimit") or 0), raw=item),
                }
            )
        out.sort(key=lambda value: value.get("id") or "")
        return out

    raise RuntimeError(f"Unsupported AI provider: {provider}")


# ---------------------------------------------------------------------------
# SQLite cost ledger and quota tracking
# ---------------------------------------------------------------------------


def _db_path() -> Path:
    """Resolve instance path for the AI cost/quota database."""
    instance_path = Path(os.environ.get("FLASK_INSTANCE_PATH", "instance"))
    instance_path.mkdir(parents=True, exist_ok=True)
    return instance_path / "ai_quota.db"


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_cost_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_hash TEXT NOT NULL,
            request_at TEXT NOT NULL,
            workload TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            audio_seconds INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            escalated INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_quota_sessions (
            session_hash TEXT NOT NULL,
            date TEXT NOT NULL,
            chat_turns INTEGER DEFAULT 0,
            audio_seconds INTEGER DEFAULT 0,
            PRIMARY KEY (session_hash, date)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def get_runtime_config() -> dict[str, Any]:
    """Return runtime config, with DB overrides on top of environment defaults."""
    cfg = dict(_DEFAULTS)
    try:
        with _db() as conn:
            rows = conn.execute("SELECT key, value FROM ai_settings").fetchall()
        for row in rows:
            k = row["key"]
            v = row["value"]
            if k in {"monthly_budget_usd", "escalation_thresh"}:
                cfg[k] = float(v)
            elif k in {"chat_daily_limit", "audio_monthly_min", "session_quota_per_session", "quota_reset_hours"}:
                cfg[k] = int(v)
            else:
                cfg[k] = v
    except Exception:
        pass
    return cfg


def update_runtime_config(updates: dict[str, Any]) -> None:
    """Persist runtime config updates from admin UI."""
    allowed = {
        "monthly_budget_usd",
        "chat_daily_limit",
        "audio_monthly_min",
        "default_model",
        "fallback_model",
        "vision_model",
        "escalation_thresh",
        "whisper_model",
        "session_quota_per_session",
        "quota_reset_hours",
    }
    now = datetime.now(UTC).isoformat()
    with _db() as conn:
        for k, v in updates.items():
            if k not in allowed:
                continue
            conn.execute(
                """
                INSERT INTO ai_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (k, str(v), now),
            )
        conn.commit()


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a text completion."""
    rates = _COST_TABLE.get(model, {"input": 0.15, "output": 0.60})
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


def _pricing_for_model(provider: str | None, model: str) -> dict[str, float] | None:
    model = str(model or "").strip()
    if not model:
        return None
    if model in _COST_TABLE:
        return dict(_COST_TABLE[model])
    if provider == "openrouter":
        for item in get_user_provider_models("openrouter"):
            if str(item.get("id") or "") == model:
                in_price = item.get("input_per_million")
                out_price = item.get("output_per_million")
                if in_price is not None and out_price is not None:
                    return {"input": float(in_price), "output": float(out_price)}
    return None


def _estimate_tokens_from_text(text: str) -> int:
    stripped = str(text or "")
    return max(1, (len(stripped) + 3) // 4)


def _estimate_output_tokens(feature: str, input_tokens: int) -> int:
    if feature == "alt_text":
        return 90
    if feature == "playground":
        return min(700, max(180, input_tokens // 3))
    return min(900, max(220, input_tokens // 2))


def estimate_request_cost(
    *,
    feature: str,
    message: str,
    token: str = "",
    conversation_messages: int = 0,
    document_chars: int = 0,
) -> dict[str, Any]:
    """Return a rough request cost estimate for the current provider/model path."""
    provider, selected_model = get_user_ai_provider_and_model_for(feature)
    cfg = get_runtime_config()

    if feature == "alt_text":
        fallback_model = str(cfg.get("vision_model") or _VISION_MODEL)
        resolved_provider = provider or ("openrouter" if get_openrouter_api_key() else None)
    else:
        fallback_model = str(cfg.get("default_model") or _DEFAULT_MODEL)
        resolved_provider = provider or ("openrouter" if get_openrouter_api_key() else None)

    resolved_model = selected_model or fallback_model
    pricing = _pricing_for_model(resolved_provider, resolved_model)

    base_chars = len(str(message or ""))
    history_chars = max(0, int(conversation_messages or 0)) * 350
    doc_chars = min(max(0, int(document_chars or 0)), 4000)
    system_chars = 700 if feature in {"chat", "playground"} else 450
    input_tokens = _estimate_tokens_from_text("x" * (base_chars + history_chars + doc_chars + system_chars))
    output_tokens = _estimate_output_tokens(feature, input_tokens)
    cost_usd = None
    if pricing is not None:
        cost_usd = round((input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000, 6)

    return {
        "feature": feature,
        "provider": resolved_provider or "",
        "model": resolved_model,
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_total_tokens": input_tokens + output_tokens,
        "estimated_cost_usd": cost_usd,
        "cost_available": cost_usd is not None,
        "note": (
            "Estimate based on message length, recent conversation context, and current model pricing."
            if cost_usd is not None
            else "Token estimate available, but this provider/model does not expose reliable per-token pricing in GLOW yet."
        ),
    }


def _record_usage(
    session_hash: str,
    workload: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    audio_seconds: int = 0,
    escalated: bool = False,
) -> float:
    """Write a usage record and return the cost incurred."""
    cost = _compute_cost(model, input_tokens, output_tokens)
    now = datetime.now(UTC).isoformat()
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    with _db() as conn:
        conn.execute(
            """
            INSERT INTO ai_cost_ledger
                (session_hash, request_at, workload, model, input_tokens,
                 output_tokens, audio_seconds, cost_usd, escalated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_hash,
                now,
                workload,
                model,
                input_tokens,
                output_tokens,
                audio_seconds,
                cost,
                int(escalated),
            ),
        )
        if workload == "chat":
            conn.execute(
                """
                INSERT INTO ai_quota_sessions (session_hash, date, chat_turns, audio_seconds)
                VALUES (?, ?, 1, 0)
                ON CONFLICT(session_hash, date) DO UPDATE SET chat_turns = chat_turns + 1
                """,
                (session_hash, today),
            )
        elif workload == "audio":
            conn.execute(
                """
                INSERT INTO ai_quota_sessions (session_hash, date, chat_turns, audio_seconds)
                VALUES (?, ?, 0, ?)
                ON CONFLICT(session_hash, date) DO UPDATE SET audio_seconds = audio_seconds + ?
                """,
                (session_hash, today, audio_seconds, audio_seconds),
            )
        conn.commit()

    log.info(
        "AI usage: session=%s workload=%s model=%s tokens=%d/%d cost=$%.4f escalated=%s",
        session_hash,
        workload,
        model,
        input_tokens,
        output_tokens,
        cost,
        escalated,
    )
    return cost


# ---------------------------------------------------------------------------
# Budget and quota checks
# ---------------------------------------------------------------------------


def get_monthly_spend() -> float:
    """Return total AI spend in USD for the current calendar month."""
    month = datetime.now(UTC).strftime("%Y-%m")
    try:
        with _db() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0.0) FROM ai_cost_ledger WHERE request_at LIKE ?",
                (f"{month}%",),
            ).fetchone()
            return float(row[0])
    except Exception:
        return 0.0


def is_budget_exhausted() -> bool:
    """Return True if the monthly hard cap has been reached."""
    cfg = get_runtime_config()
    return get_monthly_spend() >= float(cfg["monthly_budget_usd"])


def get_quota_status(session_hash: str) -> dict[str, Any]:
    """Return current quota state for a session (used in UI and admin)."""
    cfg = get_runtime_config()
    monthly_budget = float(cfg["monthly_budget_usd"])
    chat_daily_limit = int(cfg["chat_daily_limit"])
    audio_monthly_min = int(cfg["audio_monthly_min"])
    session_quota_limit = max(0, int(cfg.get("session_quota_per_session", 0) or 0))
    quota_reset_hours = max(1, int(cfg.get("quota_reset_hours", 24) or 24))
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    month = datetime.now(UTC).strftime("%Y-%m")
    monthly_spend = get_monthly_spend()
    now = datetime.now(UTC)
    window_start = now.timestamp() - (quota_reset_hours * 3600)

    try:
        with _db() as conn:
            row = conn.execute(
                "SELECT chat_turns, audio_seconds FROM ai_quota_sessions WHERE session_hash=? AND date=?",
                (session_hash, today),
            ).fetchone()
            chat_today = int(row["chat_turns"]) if row else 0

            audio_row = conn.execute(
                """
                SELECT COALESCE(SUM(audio_seconds), 0) as total
                FROM ai_quota_sessions
                WHERE session_hash=? AND date LIKE ?
                """,
                (session_hash, f"{month}%"),
            ).fetchone()
            audio_month_seconds = int(audio_row["total"]) if audio_row else 0

            if session_quota_limit > 0:
                quota_row = conn.execute(
                    """
                    SELECT COUNT(*) as request_count, MIN(request_at) as oldest_request
                    FROM ai_cost_ledger
                    WHERE session_hash = ? AND request_at >= ?
                    """,
                    (session_hash, datetime.fromtimestamp(window_start, UTC).isoformat()),
                ).fetchone()
                session_requests = int(quota_row["request_count"] or 0) if quota_row else 0
                oldest_request = str(quota_row["oldest_request"] or "") if quota_row else ""
            else:
                session_requests = 0
                oldest_request = ""
    except Exception:
        chat_today = 0
        audio_month_seconds = 0
        session_requests = 0
        oldest_request = ""

    audio_month_minutes = audio_month_seconds // 60
    if session_quota_limit > 0 and oldest_request:
        try:
            oldest_dt = datetime.fromisoformat(oldest_request)
            if oldest_dt.tzinfo is None:
                oldest_dt = oldest_dt.replace(tzinfo=UTC)
            session_reset_seconds = max(0, int(((oldest_dt.timestamp() + (quota_reset_hours * 3600)) - now.timestamp())))
        except ValueError:
            session_reset_seconds = quota_reset_hours * 3600
    else:
        session_reset_seconds = 0

    session_remaining = max(0, session_quota_limit - session_requests) if session_quota_limit > 0 else None
    session_available = monthly_spend < monthly_budget and (session_quota_limit == 0 or session_requests < session_quota_limit)

    return {
        "ai_configured": is_ai_configured(),
        "whisper_configured": is_whisper_configured(),
        "budget_usd": monthly_budget,
        "spent_usd": round(monthly_spend, 4),
        "budget_remaining_usd": round(max(0.0, monthly_budget - monthly_spend), 4),
        "budget_pct": round(min(100.0, monthly_spend / max(monthly_budget, 0.01) * 100), 1),
        "budget_exhausted": monthly_spend >= monthly_budget,
        "chat_turns_today": chat_today,
        "chat_daily_limit": chat_daily_limit,
        "chat_remaining_today": max(0, chat_daily_limit - chat_today),
        "chat_available": chat_today < chat_daily_limit and monthly_spend < monthly_budget,
        "audio_minutes_month": audio_month_minutes,
        "audio_monthly_limit": audio_monthly_min,
        "audio_remaining_min": max(0, audio_monthly_min - audio_month_minutes),
        "audio_available": audio_month_minutes < audio_monthly_min and monthly_spend < monthly_budget,
        "session_quota_enabled": session_quota_limit > 0,
        "session_requests_in_window": session_requests,
        "session_quota_limit": session_quota_limit,
        "session_requests_remaining": session_remaining,
        "session_available": session_available,
        "session_reset_hours": quota_reset_hours,
        "session_reset_seconds": session_reset_seconds,
    }


def enforce_session_quota(session_hash: str) -> None:
    """Raise a runtime error when the configured per-session quota window is exhausted."""
    quota = get_quota_status(session_hash)
    if quota.get("session_available", True):
        return
    reset_seconds = int(quota.get("session_reset_seconds") or 0)
    if reset_seconds > 0:
        raise RuntimeError(
            "This session has reached the current AI request limit. "
            f"Try again in about {max(1, reset_seconds // 60)} minute(s)."
        )
    raise RuntimeError("This session has reached the current AI request limit. Please try again later.")


def make_session_hash(flask_session_id: str) -> str:
    """Create a short stable anonymous hash from the Flask session identifier."""
    return hashlib.sha256(flask_session_id.encode()).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Chat via OpenRouter
# ---------------------------------------------------------------------------


def _detect_uncertainty(text: str) -> bool:
    """Return True if the response appears uncertain (may benefit from escalation)."""
    lowered = text.lower()
    hits = sum(1 for marker in _UNCERTAINTY_MARKERS if marker in lowered)
    return hits >= 2


def _model_list(value: str) -> list[str]:
    """Normalize a comma-separated model config into a non-empty list."""
    return [item.strip() for item in value.split(",") if item.strip()]


def _provider_preferences(*, require_parameters: bool = False) -> dict[str, Any]:
    """Return OpenRouter provider routing preferences for privacy-sensitive workloads."""
    prefs: dict[str, Any] = {
        "dataCollection": "deny",
        "zdr": True,
        "allowFallbacks": True,
        "sort": "latency",
    }
    if require_parameters:
        prefs["requireParameters"] = True
    return prefs


def _ollama_completion(
    model: str,
    messages: list[dict],
    session_hash: str,
    max_tokens: int = 1200,
) -> tuple[str, int, int, str]:
    """Call Ollama Cloud chat API using the user's personal API key.

    Uses the Ollama native /api/chat endpoint (not the OpenAI-compat layer)
    since that is the documented path for cloud key authentication.

    Returns (text, prompt_tokens, completion_tokens, model_name).
    Raises RuntimeError if the key is missing or the request fails.
    """
    api_key = get_user_ollama_key()
    if not api_key:
        raise RuntimeError("No Ollama API key in session.")

    base_url = get_ollama_cloud_url()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }

    def _response_error_message(resp: requests.Response, requested_model: str) -> str:
        try:
            payload = resp.json()
            detail = str(payload.get("error") or "").strip()
        except ValueError:
            detail = (resp.text or "").strip()

        if resp.status_code == 401:
            return (
                "Ollama accepted the account key for model listing, but this account is not authorized "
                "for cloud inference. The key may have been revoked, or your account may not have "
                "inference entitlement."
            )
        if resp.status_code == 403:
            if detail:
                return f"Ollama denied access to model '{requested_model}': {detail}"
            return f"Ollama denied access to model '{requested_model}'. This model may require a paid plan."
        if resp.status_code == 404:
            if detail:
                return f"Ollama model '{requested_model}' is not available on this account: {detail}"
            return f"Ollama model '{requested_model}' is not available on this account. Choose a model from your validated account list."
        if resp.status_code == 429:
            return "Ollama plan limit reached. Check your usage at ollama.com/settings."
        if detail:
            return f"Ollama Cloud request failed: {detail}"
        return f"Ollama Cloud request failed with status {resp.status_code}."

    try:
        resp = requests.post(
            f"{base_url}/chat",
            json=payload,
            headers=headers,
            timeout=_OLLAMA_CHAT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise RuntimeError(_response_error_message(resp, model))
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Ollama Cloud request failed: {exc}") from exc

    data = resp.json()
    # Ollama native response shape: {"message": {"role": "assistant", "content": "..."},
    #   "prompt_eval_count": N, "eval_count": N, "model": "..."}
    text = (data.get("message") or {}).get("content") or ""
    prompt_tokens = int(data.get("prompt_eval_count") or 0)
    completion_tokens = int(data.get("eval_count") or 0)
    resolved_model = data.get("model") or model

    log.info(
        "Ollama usage: session=%s model=%s tokens=%d/%d",
        session_hash[:16],
        resolved_model,
        prompt_tokens,
        completion_tokens,
    )
    return text, prompt_tokens, completion_tokens, resolved_model


def stream_ollama_chat(
    question: str,
    system_prompt: str,
    session_hash: str,
    conversation_history: list[dict] | None = None,
    feature: str = "playground",
    max_tokens: int = 1200,
):
    """Stream Ollama Cloud chat output as incremental token chunks.

    Yields dict events with these shapes:
      {"token": "...", "model": "..."}
      {"done": True, "model": "..."}

    Raises RuntimeError for authentication, quota, or transport failures.
    """
    api_key = get_user_ollama_key()
    if not api_key:
        raise RuntimeError("No Ollama API key in session.")

    if not is_ollama_configured():
        raise RuntimeError("Ollama is not configured for this session.")

    enforce_session_quota(session_hash)

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": question})

    model = get_user_ollama_model_for(feature)
    base_url = get_ollama_cloud_url()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {"num_predict": max_tokens},
    }

    def _stream_error_message(resp: requests.Response, requested_model: str) -> str:
        try:
            payload = resp.json()
            detail = str(payload.get("error") or "").strip()
        except ValueError:
            detail = (resp.text or "").strip()

        if resp.status_code == 401:
            return (
                "Ollama accepted the account key for model listing, but this account is not authorized "
                "for cloud inference. The key may have been revoked, or your account may not have "
                "inference entitlement."
            )
        if resp.status_code == 403:
            if detail:
                return f"Ollama denied access to model '{requested_model}': {detail}"
            return f"Ollama denied access to model '{requested_model}'. This model may require a paid plan."
        if resp.status_code == 404:
            if detail:
                return f"Ollama model '{requested_model}' is not available on this account: {detail}"
            return f"Ollama model '{requested_model}' is not available on this account. Choose a model from your validated account list."
        if resp.status_code == 429:
            return "Ollama plan limit reached. Check your usage at ollama.com/settings."
        if detail:
            return f"Ollama Cloud streaming request failed: {detail}"
        return f"Ollama Cloud streaming request failed with status {resp.status_code}."

    try:
        resp = requests.post(
            f"{base_url}/chat",
            json=payload,
            headers=headers,
            timeout=_OLLAMA_CHAT_TIMEOUT,
            stream=True,
        )
        if resp.status_code >= 400:
            raise RuntimeError(_stream_error_message(resp, model))
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Ollama Cloud streaming request failed: {exc}") from exc

    prompt_tokens = 0
    completion_tokens = 0
    resolved_model = model

    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        try:
            data = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        if data.get("model"):
            resolved_model = str(data.get("model"))

        token = (data.get("message") or {}).get("content") or ""
        if token:
            yield {"token": token, "model": resolved_model}

        if data.get("done"):
            prompt_tokens = int(data.get("prompt_eval_count") or prompt_tokens)
            completion_tokens = int(data.get("eval_count") or completion_tokens)
            break

    _record_usage(session_hash, feature, resolved_model, prompt_tokens, completion_tokens, escalated=False)
    yield {"done": True, "model": resolved_model}


def _openrouter_completion(
    model: str,
    messages: list[dict],
    user_id: str,
    max_tokens: int = 1200,
) -> tuple[str, int, int, str]:
    """Call OpenRouter chat completions.

    Returns (text, input_tokens, output_tokens, resolved_model).
    """
    api_key = get_openrouter_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://letitglow.app",
        "X-Title": "GLOW",
        "Content-Type": "application/json",
    }
    model_candidates = _model_list(model)
    payload: dict[str, Any] = {
        "model": model_candidates[0],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "provider": _provider_preferences(require_parameters=False),
    }
    if len(model_candidates) > 1:
        payload["models"] = model_candidates
    if user_id:
        payload["user"] = user_id[:64]
    data = _openrouter_post_chat(payload, headers)
    text = data["choices"][0]["message"]["content"] or ""
    usage = data.get("usage", {})
    return (
        text,
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
        data.get("model") or model_candidates[0],
    )


def _openrouter_user_completion(
    model: str,
    messages: list[dict],
    user_id: str,
    max_tokens: int = 1200,
) -> tuple[str, int, int, str]:
    api_key = get_user_provider_key("openrouter")
    if not api_key:
        raise RuntimeError("No OpenRouter API key in session.")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://letitglow.app",
        "X-Title": "GLOW",
        "Content-Type": "application/json",
    }
    model_candidates = _model_list(model)
    payload: dict[str, Any] = {
        "model": model_candidates[0],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "provider": _provider_preferences(require_parameters=False),
    }
    if len(model_candidates) > 1:
        payload["models"] = model_candidates
    if user_id:
        payload["user"] = user_id[:64]
    data = _openrouter_post_chat(payload, headers)
    text = data["choices"][0]["message"]["content"] or ""
    usage = data.get("usage", {})
    return (
        text,
        int(usage.get("prompt_tokens", 0) or 0),
        int(usage.get("completion_tokens", 0) or 0),
        data.get("model") or model_candidates[0],
    )


def _openai_completion(
    model: str,
    messages: list[dict],
    user_id: str,
    max_tokens: int = 1200,
) -> tuple[str, int, int, str]:
    api_key = get_user_provider_key("openai")
    if not api_key:
        raise RuntimeError("No OpenAI API key in session.")
    resp = requests.post(
        f"{_OPENAI_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "user": user_id[:64] if user_id else None,
        },
        timeout=_REQUEST_TIMEOUT,
    )
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("error", {}).get("message") or resp.text
        except Exception:
            detail = resp.text
        raise RuntimeError(f"OpenAI request failed: {str(detail).strip()}")
    data = resp.json()
    text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    usage = data.get("usage", {}) or {}
    return (
        text,
        int(usage.get("prompt_tokens", 0) or 0),
        int(usage.get("completion_tokens", 0) or 0),
        str(data.get("model") or model),
    )


def _gemini_messages(messages: list[dict]) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role") or "user")
        text = str(message.get("content") or "")
        if not text:
            continue
        if role == "system":
            system_parts.append(text)
            continue
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}],
            }
        )
    return "\n\n".join(system_parts), contents


def _gemini_completion(
    model: str,
    messages: list[dict],
    user_id: str,
    max_tokens: int = 1200,
) -> tuple[str, int, int, str]:
    api_key = get_user_provider_key("gemini")
    if not api_key:
        raise RuntimeError("No Gemini API key in session.")
    system_instruction, contents = _gemini_messages(messages)
    payload: dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    resp = requests.post(
        f"{_GEMINI_BASE}/models/{model}:generateContent",
        params={"key": api_key},
        json=payload,
        timeout=_REQUEST_TIMEOUT,
    )
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("error", {}).get("message") or resp.text
        except Exception:
            detail = resp.text
        raise RuntimeError(f"Gemini request failed: {str(detail).strip()}")
    data = resp.json()
    candidates = data.get("candidates") or []
    parts = []
    if candidates:
        parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(str(part.get("text") or "") for part in parts).strip()
    usage = data.get("usageMetadata") or {}
    return (
        text,
        int(usage.get("promptTokenCount", 0) or 0),
        int(usage.get("candidatesTokenCount", 0) or 0),
        model,
    )


def _openrouter_post_chat(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """POST OpenRouter chat completion with bounded retries on throttling/server faults."""
    attempts = max(0, _OPENROUTER_MAX_RETRIES)
    last_exc: Exception | None = None

    # Some providers reject advanced routing fields in otherwise valid requests.
    # Keep privacy routing as the default, but retry once with a compatibility
    # payload (no provider/models) when we receive 400/404 errors.
    compat_payload = dict(payload)
    compat_payload.pop("provider", None)
    compat_payload.pop("models", None)
    can_try_compat = compat_payload != payload

    for attempt in range(attempts + 1):
        try:
            resp = requests.post(
                f"{_OPENROUTER_BASE}/chat/completions",
                json=payload,
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            )
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < attempts:
                delay = _OPENROUTER_RETRY_BASE_SECONDS * (2**attempt)
                log.warning(
                    "OpenRouter transient status %s; retrying in %.2fs (attempt %d/%d)",
                    resp.status_code,
                    delay,
                    attempt + 1,
                    attempts,
                )
                time.sleep(delay)
                continue
            if resp.status_code in (400, 404) and can_try_compat:
                log.warning(
                    "OpenRouter returned %s with advanced routing fields; retrying with compatibility payload",
                    resp.status_code,
                )
                compat_resp = requests.post(
                    f"{_OPENROUTER_BASE}/chat/completions",
                    json=compat_payload,
                    headers=headers,
                    timeout=_REQUEST_TIMEOUT,
                )
                if compat_resp.ok:
                    return compat_resp.json()
                # Preserve the most relevant error context if compatibility also fails.
                compat_resp.raise_for_status()
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            delay = _OPENROUTER_RETRY_BASE_SECONDS * (2**attempt)
            log.warning(
                "OpenRouter request failed: %s; retrying in %.2fs (attempt %d/%d)",
                exc,
                delay,
                attempt + 1,
                attempts,
            )
            time.sleep(delay)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("OpenRouter request failed without exception details.")


def chat(
    question: str,
    system_prompt: str,
    session_hash: str,
    document_text: str = "",
    conversation_history: list[dict] | None = None,
    feature: str = "chat",
) -> tuple[str, bool]:
    """Run a chat completion through the AI gateway.

    Routes to Ollama Cloud when the user has provided their own key;
    falls back to OpenRouter when only the server key is configured.

    ``feature`` selects the per-feature model when Ollama is active
    (e.g. 'chat', 'playground', 'heading_fix', 'markitdown').

    Returns:
        (answer_text, was_escalated)

    Raises:
        RuntimeError: if no AI provider is configured or limits are reached.
    """
    if not is_ai_configured():
        raise RuntimeError("AI is not configured on this server.")

    enforce_session_quota(session_hash)

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history)
    if document_text:
        messages.append(
            {"role": "user", "content": f"Document excerpt (first 4000 chars):\n{document_text[:4000]}"}
        )
    messages.append({"role": "user", "content": question})

    provider, model = get_user_ai_provider_and_model_for(feature)

    if provider == "ollama" and is_ollama_configured():
        answer, in_tok, out_tok, resolved = _ollama_completion(model or get_user_ollama_model_for(feature), messages, session_hash)
        _record_usage(session_hash, feature, _model_ref("ollama", resolved), in_tok, out_tok, escalated=False)
        return answer, False

    if provider == "openrouter" and get_user_provider_key("openrouter"):
        answer, in_tok, out_tok, resolved = _openrouter_user_completion(model, messages, session_hash)
        _record_usage(session_hash, feature, _model_ref("openrouter", resolved), in_tok, out_tok, escalated=False)
        return answer, False

    if provider == "openai" and get_user_provider_key("openai"):
        answer, in_tok, out_tok, resolved = _openai_completion(model, messages, session_hash)
        _record_usage(session_hash, feature, _model_ref("openai", resolved), in_tok, out_tok, escalated=False)
        return answer, False

    if provider == "gemini" and get_user_provider_key("gemini"):
        answer, in_tok, out_tok, resolved = _gemini_completion(model, messages, session_hash)
        _record_usage(session_hash, feature, _model_ref("gemini", resolved), in_tok, out_tok, escalated=False)
        return answer, False

    # --- OpenRouter path (server key) ---
    if is_budget_exhausted():
        raise RuntimeError(
            "The monthly AI budget has been reached. AI features will resume next month."
        )

    cfg = get_runtime_config()
    default_model = str(cfg["default_model"])
    fallback_model = str(cfg["fallback_model"])

    or_messages = messages

    # --- Try default (free) model first ---
    try:
        answer, in_tok, out_tok, resolved_model = _openrouter_completion(
            default_model,
            or_messages,
            session_hash,
        )
    except Exception as exc:
        log.warning("Default model failed (%s), escalating: %s", default_model, exc)
        answer, in_tok, out_tok, resolved_model = _openrouter_completion(
            fallback_model,
            or_messages,
            session_hash,
        )
        _record_usage(session_hash, "chat", resolved_model, in_tok, out_tok, escalated=True)
        return answer, True

    # --- Escalate if uncertain ---
    escalated = False
    if _detect_uncertainty(answer):
        try:
            escalated_answer, in_tok2, out_tok2, resolved_fallback_model = _openrouter_completion(
                fallback_model,
                or_messages,
                session_hash,
            )
            _record_usage(
                session_hash, "chat", resolved_model, in_tok, out_tok, escalated=False
            )
            _record_usage(
                session_hash, "chat", resolved_fallback_model, in_tok2, out_tok2, escalated=True
            )
            return escalated_answer, True
        except Exception as exc:
            log.warning("Escalation to %s failed: %s", fallback_model, exc)

    _record_usage(session_hash, "chat", resolved_model, in_tok, out_tok, escalated=False)
    return answer, escalated


def describe_image(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    session_hash: str,
) -> str:
    """Describe image content using a vision-capable active provider/model."""
    if not is_ai_configured():
        raise RuntimeError("AI is not configured on this server.")

    enforce_session_quota(session_hash)

    if is_budget_exhausted():
        raise RuntimeError(
            "The monthly AI budget has been reached. Vision analysis will resume next month."
        )

    provider, selected_model = get_user_ai_provider_and_model_for("alt_text")
    cfg = get_runtime_config()
    vision_model = selected_model or str(cfg.get("vision_model") or _VISION_MODEL)

    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_uri = f"data:{mime_type};base64,{encoded}"

    if provider == "openai" and get_user_provider_key("openai"):
        resp = requests.post(
            f"{_OPENAI_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {get_user_provider_key('openai')}",
                "Content-Type": "application/json",
            },
            json={
                "model": vision_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an accessibility assistant. Describe visible content accurately, "
                            "extract readable text when possible, and call out accessibility-relevant "
                            "elements such as headings, charts, labels, and figure meaning."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    },
                ],
                "max_tokens": 700,
                "temperature": 0.2,
            },
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("error", {}).get("message") or resp.text
            except Exception:
                detail = resp.text
            raise RuntimeError(f"OpenAI vision request failed: {str(detail).strip()}")
        data = resp.json()
        text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
        usage = data.get("usage", {}) or {}
        _record_usage(session_hash, "vision", _model_ref("openai", str(data.get("model") or vision_model)), int(usage.get("prompt_tokens", 0) or 0), int(usage.get("completion_tokens", 0) or 0), escalated=False)
        return text

    if provider == "gemini" and get_user_provider_key("gemini"):
        resp = requests.post(
            f"{_GEMINI_BASE}/models/{vision_model}:generateContent",
            params={"key": get_user_provider_key("gemini")},
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": mime_type, "data": encoded}},
                        ],
                    }
                ],
                "systemInstruction": {
                    "parts": [
                        {
                            "text": "You are an accessibility assistant. Describe visible content accurately, extract readable text when possible, and call out accessibility-relevant elements such as headings, charts, labels, and figure meaning."
                        }
                    ]
                },
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700},
            },
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("error", {}).get("message") or resp.text
            except Exception:
                detail = resp.text
            raise RuntimeError(f"Gemini vision request failed: {str(detail).strip()}")
        data = resp.json()
        parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        text = "".join(str(part.get("text") or "") for part in parts).strip()
        usage = data.get("usageMetadata") or {}
        _record_usage(session_hash, "vision", _model_ref("gemini", vision_model), int(usage.get("promptTokenCount", 0) or 0), int(usage.get("candidatesTokenCount", 0) or 0), escalated=False)
        return text

    api_key = _openrouter_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://letitglow.app",
        "X-Title": "GLOW",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": vision_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an accessibility assistant. Describe visible content accurately, "
                    "extract readable text when possible, and call out accessibility-relevant "
                    "elements such as headings, charts, labels, and figure meaning."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ],
        "max_tokens": 700,
        "temperature": 0.2,
        "provider": _provider_preferences(require_parameters=False),
        "user": session_hash[:64],
    }

    data = _openrouter_post_chat(payload, headers)
    text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
    usage = data.get("usage", {})
    model_used = data.get("model") or vision_model
    _record_usage(
        session_hash,
        "vision",
        _model_ref("openrouter", str(model_used)),
        int(usage.get("prompt_tokens", 0) or 0),
        int(usage.get("completion_tokens", 0) or 0),
        escalated=False,
    )
    return text


# ---------------------------------------------------------------------------
# Audio transcription via OpenAI Whisper API
# ---------------------------------------------------------------------------


def transcribe(
    audio_path: Path,
    language: str | None,
    session_hash: str,
) -> str:
    """Transcribe audio using OpenRouter.

    Primary path: chat/completions with input_audio (openai/gpt-audio-mini).
    This path is resilient and token-cost-tracked.

    Fallback path: /audio/transcriptions (openai/whisper-large-v3).
    Used only when the primary path fails; cost estimated from file size.

    Returns the transcript as plain text.

    Raises:
        RuntimeError: if Whisper is not configured, budget is exhausted,
            a 402 balance error is returned, or both paths fail.
    """
    if not is_whisper_configured():
        raise RuntimeError("Audio transcription is not configured on this server.")

    enforce_session_quota(session_hash)

    if is_budget_exhausted():
        raise RuntimeError(
            "The monthly AI budget has been reached. Audio transcription will resume next month."
        )

    cfg = get_runtime_config()
    whisper_model = str(cfg.get("whisper_model", _WHISPER_MODEL))
    api_key = _openrouter_key()

    transcript: str | None = None
    input_audio_error: str | None = None
    audio_model_used: str = "openai/gpt-audio-mini"
    audio_in_tokens: int = 0
    audio_out_tokens: int = 0
    path_used: str = "input_audio"

    # --- Primary path: chat/completions + input_audio (gpt-audio-mini) ---
    # Preferred because: token-cost-tracked, stable, no upstream 5xx HTML errors.
    try:
        transcript, audio_in_tokens, audio_out_tokens = _transcribe_via_input_audio(
            audio_path=audio_path,
            api_key=api_key,
            language=language,
            session_hash=session_hash,
        )
        path_used = "input_audio"
    except requests.HTTPError as exc:
        resp_obj = exc.response
        input_audio_error = _extract_openrouter_error(resp_obj)
        if resp_obj is not None and resp_obj.status_code == 402:
            raise RuntimeError(
                "OpenRouter audio transcription requires a minimum account balance. "
                "Top up your OpenRouter account (at least $0.50) to enable BITS Whisperer."
            ) from exc
        log.warning(
            "Audio input_audio path failed (HTTP %s): %s -- trying direct endpoint",
            resp_obj.status_code if resp_obj is not None else "n/a",
            input_audio_error,
        )
    except requests.RequestException as exc:
        input_audio_error = str(exc)
        log.warning("Audio input_audio path failed: %s -- trying direct endpoint", exc)

    # --- Fallback path: /audio/transcriptions (whisper-large-v3) ---
    # Used when primary fails due to provider issues (e.g. upstream 5xx).
    if transcript is None:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://letitglow.app",
            "X-Title": "GLOW",
        }
        try:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path.name, f, "audio/mpeg")}
                form_data: dict[str, Any] = {"model": whisper_model, "response_format": "text"}
                if language:
                    form_data["language"] = language
                resp = requests.post(
                    _OPENROUTER_AUDIO_URL,
                    headers=headers,
                    files=files,
                    data=form_data,
                    timeout=300,
                )
            if resp.ok:
                transcript = resp.text.strip()
                audio_model_used = whisper_model
                path_used = "direct"
            else:
                direct_error = _extract_openrouter_error(resp)
                if resp.status_code == 500 and "<!DOCTYPE" in (resp.text or ""):
                    raise RuntimeError(
                        "OpenRouter audio transcription is currently unavailable "
                        "(upstream provider error on direct endpoint, and the "
                        f"primary audio path also failed: {input_audio_error or 'unknown'}). "
                        "Please try again later."
                    )
                raise RuntimeError(
                    f"OpenRouter audio transcription failed. "
                    f"Primary path: {input_audio_error or 'n/a'}. "
                    f"Fallback path: {direct_error}."
                )
        except RuntimeError:
            raise
        except requests.RequestException as exc:
            raise RuntimeError(
                "OpenRouter audio transcription failed on both paths. "
                f"Primary (input_audio) error: {input_audio_error or 'n/a'}. "
                f"Fallback (direct) error: {exc}."
            ) from exc

    # --- Cost and quota tracking ---
    if path_used == "input_audio":
        # Token-based cost (same rate as gpt-4o-mini for now)
        _record_usage(
            session_hash,
            "audio",
            audio_model_used,
            audio_in_tokens,
            audio_out_tokens,
            escalated=False,
        )
        estimated_seconds = max(1, audio_in_tokens // 10)  # rough audio-token-to-seconds
    else:
        # Size-based estimate for direct Whisper endpoint (no token response)
        try:
            size_bytes = audio_path.stat().st_size
            estimated_seconds = max(1, size_bytes // 16_000)
        except Exception:
            estimated_seconds = 60
        cost = (estimated_seconds / 60) * 0.006
        now = datetime.now(UTC).isoformat()
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        try:
            with _db() as conn:
                conn.execute(
                    """
                    INSERT INTO ai_cost_ledger
                        (session_hash, request_at, workload, model, audio_seconds, cost_usd, escalated)
                    VALUES (?, ?, 'audio', ?, ?, ?, 0)
                    """,
                    (session_hash, now, audio_model_used, estimated_seconds, cost),
                )
                conn.execute(
                    """
                    INSERT INTO ai_quota_sessions (session_hash, date, chat_turns, audio_seconds)
                    VALUES (?, ?, 0, ?)
                    ON CONFLICT(session_hash, date) DO UPDATE SET audio_seconds = audio_seconds + ?
                    """,
                    (session_hash, today, estimated_seconds, estimated_seconds),
                )
                conn.commit()
        except Exception as exc:
            log.warning("Failed to record audio usage: %s", exc)

    log.info(
        "Whisper transcription: session=%s path=%s model=%s seconds~=%d",
        session_hash,
        path_used,
        audio_model_used,
        estimated_seconds,
    )
    return transcript


def _extract_openrouter_error(resp: requests.Response | None) -> str:
    """Extract a useful error string from OpenRouter JSON or HTML responses."""
    if resp is None:
        return "No response received"
    try:
        payload = resp.json()
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict) and err.get("message"):
                return str(err["message"])
        return str(payload)
    except Exception:
        body = (resp.text or "").strip().replace("\n", " ")
        return f"HTTP {resp.status_code}: {body[:300]}"


def _transcribe_via_input_audio(
    audio_path: Path,
    api_key: str,
    language: str | None,
    session_hash: str,
) -> tuple[str, int, int]:
    """Primary transcription via chat/completions + input_audio (openai/gpt-audio-mini).

    Documented by OpenRouter's multimodal audio guide:
    https://openrouter.ai/docs/guides/overview/multimodal/audio

    Returns:
        (transcript_text, input_tokens, output_tokens)

    Raises:
        requests.HTTPError: on non-2xx responses (caller inspects status code).
    """
    ext = audio_path.suffix.lower().lstrip(".") or "mp3"
    if ext not in {"mp3", "wav", "m4a", "ogg", "flac", "aac", "opus", "webm", "mp4", "mpeg", "mpga"}:
        ext = "mp3"

    encoded_audio = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    system_prompt = (
        "You are a transcription assistant. Return only the transcript text. "
        "Do not add summaries, speaker labels, or extra commentary."
    )
    user_prompt = "Transcribe this audio to plain text."
    if language:
        user_prompt += f" Language hint: {language}."

    payload: dict[str, Any] = {
        "model": "openai/gpt-audio-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": encoded_audio,
                            "format": ext,
                        },
                    },
                ],
            },
        ],
        "max_tokens": 4000,
        "temperature": 0,
        "user": session_hash[:64],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://letitglow.app",
        "X-OpenRouter-Title": "GLOW",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        _OPENROUTER_CHAT_URL,
        headers=headers,
        json=payload,
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
    usage = data.get("usage", {})
    return text, int(usage.get("prompt_tokens", 0) or 0), int(usage.get("completion_tokens", 0) or 0)


# ---------------------------------------------------------------------------
# Admin telemetry queries
# ---------------------------------------------------------------------------


def get_admin_stats() -> dict[str, Any]:
    """Return aggregated stats for the admin quota dashboard."""
    cfg = get_runtime_config()
    monthly_budget = float(cfg["monthly_budget_usd"])
    month = datetime.now(UTC).strftime("%Y-%m")
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    try:
        with _db() as conn:
            # Monthly totals
            monthly = conn.execute(
                """
                SELECT
                    COUNT(*) as requests,
                    COALESCE(SUM(cost_usd), 0) as spend,
                    COALESCE(SUM(CASE WHEN escalated=1 THEN 1 ELSE 0 END), 0) as escalations,
                    COALESCE(SUM(CASE WHEN workload='chat' THEN 1 ELSE 0 END), 0) as chat_count,
                    COALESCE(SUM(CASE WHEN workload='audio' THEN 1 ELSE 0 END), 0) as audio_count,
                    COALESCE(SUM(audio_seconds), 0) as audio_seconds
                FROM ai_cost_ledger WHERE request_at LIKE ?
                """,
                (f"{month}%",),
            ).fetchone()

            # Daily spend trend (last 14 days)
            daily_rows = conn.execute(
                """
                SELECT
                    substr(request_at, 1, 10) as day,
                    COALESCE(SUM(cost_usd), 0) as spend,
                    COUNT(*) as requests
                FROM ai_cost_ledger
                WHERE request_at >= date('now', '-13 days')
                GROUP BY day ORDER BY day
                """,
            ).fetchall()

            # Today totals
            today_row = conn.execute(
                """
                SELECT COUNT(*) as requests, COALESCE(SUM(cost_usd), 0) as spend
                FROM ai_cost_ledger WHERE request_at LIKE ?
                """,
                (f"{today}%",),
            ).fetchone()

            # Unique sessions this month
            session_count = conn.execute(
                "SELECT COUNT(DISTINCT session_hash) FROM ai_cost_ledger WHERE request_at LIKE ?",
                (f"{month}%",),
            ).fetchone()[0]

    except Exception as exc:
        log.warning("Admin stats query failed: %s", exc)
        return {}

    monthly_spend = float(monthly["spend"])
    return {
        "month": month,
        "today": today,
        "budget_usd": monthly_budget,
        "monthly_spend": round(monthly_spend, 4),
        "budget_remaining": round(max(0.0, monthly_budget - monthly_spend), 4),
        "budget_pct": round(min(100.0, monthly_spend / max(monthly_budget, 0.01) * 100), 1),
        "budget_exhausted": monthly_spend >= monthly_budget,
        "monthly_requests": int(monthly["requests"]),
        "monthly_escalations": int(monthly["escalations"]),
        "monthly_chat": int(monthly["chat_count"]),
        "monthly_audio": int(monthly["audio_count"]),
        "monthly_audio_minutes": int(monthly["audio_seconds"]) // 60,
        "today_requests": int(today_row["requests"]),
        "today_spend": round(float(today_row["spend"]), 4),
        "unique_sessions_month": int(session_count),
        "escalation_rate_pct": round(
            int(monthly["escalations"]) / max(int(monthly["requests"]), 1) * 100, 1
        ),
        "default_model": str(cfg["default_model"]),
        "fallback_model": str(cfg["fallback_model"]),
        "vision_model": str(cfg.get("vision_model", _VISION_MODEL)),
        "chat_daily_limit": int(cfg["chat_daily_limit"]),
        "audio_monthly_limit_min": int(cfg["audio_monthly_min"]),
        "session_quota_per_session": int(cfg.get("session_quota_per_session", 0) or 0),
        "quota_reset_hours": int(cfg.get("quota_reset_hours", 24) or 24),
        "daily_trend": [
            {"day": r["day"], "spend": round(float(r["spend"]), 4), "requests": int(r["requests"])}
            for r in daily_rows
        ],
    }


def get_model_catalog() -> list[dict[str, Any]]:
    """Fetch OpenRouter model catalog with pricing metadata.

    Returns a simplified list suitable for admin dropdowns and cost projection.
    """
    if not is_ai_configured():
        return []
    api_key = get_openrouter_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://letitglow.app",
        "X-Title": "GLOW",
    }
    try:
        resp = requests.get(f"{_OPENROUTER_BASE}/models", headers=headers, timeout=20)
        resp.raise_for_status()
        raw = resp.json().get("data", [])
        out: list[dict[str, Any]] = []
        for m in raw:
            pricing = m.get("pricing", {}) or {}
            in_price = float(pricing.get("prompt", 0) or 0)
            out_price = float(pricing.get("completion", 0) or 0)
            out.append(
                {
                    "id": m.get("id", ""),
                    "name": m.get("name") or m.get("id", ""),
                    "context_length": m.get("context_length", 0),
                    "input_per_million": round(in_price * 1_000_000, 6),
                    "output_per_million": round(out_price * 1_000_000, 6),
                }
            )
        out.sort(key=lambda x: (x["input_per_million"], x["output_per_million"], x["id"]))
        return out
    except Exception as exc:
        log.warning("OpenRouter model catalog fetch failed: %s", exc)
        # Fallback to known baseline entries
        return [
            {
                "id": "meta-llama/llama-3-8b-instruct:free",
                "name": "Llama 3 8B (free)",
                "context_length": 8192,
                "input_per_million": 0.0,
                "output_per_million": 0.0,
            },
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o mini",
                "context_length": 128000,
                "input_per_million": 0.15,
                "output_per_million": 0.60,
            },
        ]


def project_monthly_cost(
    model_id: str,
    monthly_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
) -> float:
    """Project monthly spend from simple traffic assumptions."""
    rates = _COST_TABLE.get(model_id, {"input": 0.15, "output": 0.60})
    total_in = monthly_requests * avg_input_tokens
    total_out = monthly_requests * avg_output_tokens
    return round((total_in * rates["input"] + total_out * rates["output"]) / 1_000_000, 4)
