"""Settings route -- user preference controls with opt-in persistence."""

from __future__ import annotations

import hashlib
import logging

import requests
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from acb_large_print_web.rules import get_all_rule_ids
from acb_large_print_web.ai_gateway import fetch_user_provider_models
from acb_large_print_web.user_ai import (
    USER_AI_FEATURE_DEFAULTS,
    USER_AI_FEATURE_LABELS,
    USER_AI_PROVIDER_DEFINITIONS,
    all_provider_metadata,
    clear_validated_key_hash,
    extend_provider_expiry,
    feature_model_options_for,
    get_user_active_providers,
    get_user_ai_feature_flags,
    get_user_ai_feature_models,
    get_user_ai_prompt_settings,
    get_user_ai_provider_and_model_for,
    get_user_ai_runtime_settings,
    get_validated_key_hash,
    is_user_provider_configured,
    parse_model_ref,
    primary_active_provider,
    provider_model_supports_feature,
    provider_metadata,
    provider_session_payload,
    remove_user_provider,
    save_user_ai_feature_flags,
    save_user_ai_feature_models,
    save_user_ai_prompt_settings,
    save_user_ai_runtime_settings,
    save_user_provider,
    set_validated_key_hash,
    user_ai_session_minutes,
)

log = logging.getLogger(__name__)
settings_bp = Blueprint("settings", __name__)
ai_bp = Blueprint("ai", __name__)

_OLLAMA_PREFERRED_MODELS = [
    "gemma3:4b",
    "gemma3:12b",
    "gpt-oss:120b",
    "mistral",
    "qwen3:8b",
    "llama3.2",
]


def _trim_text(value: object, limit: int = 300) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit - 1]}..."


def _requested_provider() -> str:
    provider = (
        request.values.get("provider")
        or (request.get_json(silent=True) or {}).get("provider")
        or "ollama"
    )
    provider = str(provider or "ollama").strip().lower()
    if provider not in USER_AI_PROVIDER_DEFINITIONS:
        return "ollama"
    return provider


def _provider_key_field(provider: str) -> str:
    if provider == "ollama":
        return "ollama_api_key"
    return f"{provider}_api_key"


def _provider_api_key(provider: str) -> str:
    key = (
        request.values.get("api_key")
        or request.values.get(_provider_key_field(provider))
        or (request.get_json(silent=True) or {}).get("api_key")
        or ""
    )
    return str(key).strip()


def _provider_default_model(provider: str) -> str:
    value = (
        request.values.get("default_model")
        or request.values.get("ollama_model")
        or (request.get_json(silent=True) or {}).get("default_model")
        or str(provider_metadata(provider).get("default_model") or "")
    )
    return str(value).strip()


def _suggested_model(provider: str, models: list[dict[str, object]]) -> str:
    default_model = str(provider_metadata(provider).get("default_model") or "")
    available = [str(model.get("id") or "") for model in models if model.get("id")]
    if provider == "ollama":
        for candidate in _OLLAMA_PREFERRED_MODELS:
            if candidate in available:
                return candidate
    if default_model and default_model in available:
        return default_model
    return available[0] if available else default_model


def _serialize_provider_catalog(provider: str, models: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for model in models:
        caps = model.get("capabilities") or {}
        out.append(
            {
                "id": str(model.get("id") or ""),
                "name": str(model.get("name") or model.get("id") or ""),
                "provider": provider,
                "input_per_million": model.get("input_per_million"),
                "output_per_million": model.get("output_per_million"),
                "context_length": model.get("context_length"),
                "note": model.get("note") or "",
                "capabilities": {
                    "text": bool(caps.get("text", False)),
                    "vision": bool(caps.get("vision", False)),
                    "audio_transcription": bool(caps.get("audio_transcription", False)),
                    "long_context": bool(caps.get("long_context", False)),
                    "reasoning": bool(caps.get("reasoning", False)),
                    "streaming": bool(caps.get("streaming", False)),
                },
            }
        )
    return out


def _render_ai_settings_page():
    providers = get_user_active_providers()
    features = get_user_ai_feature_flags()
    feature_models = get_user_ai_feature_models()
    feature_binding_defaults = {
        feature: get_user_ai_provider_and_model_for(feature)
        for feature in USER_AI_FEATURE_DEFAULTS
    }
    feature_options = {
        feature: feature_model_options_for(feature)
        for feature in USER_AI_FEATURE_DEFAULTS
    }
    primary_provider = primary_active_provider()
    runtime_settings = get_user_ai_runtime_settings()
    prompt_settings = get_user_ai_prompt_settings()
    return render_template(
        "settings_ai.html",
        ollama_active=is_user_provider_configured("ollama"),
        active_providers=providers,
        ai_provider_options=all_provider_metadata(),
        ai_primary_provider=primary_provider,
        ai_primary_provider_id=str(primary_provider.get("id") or "") if primary_provider else "",
        ai_primary_model=str(primary_provider.get("default_model") or "") if primary_provider else "",
        ai_feature_flags=features,
        ai_feature_labels=USER_AI_FEATURE_LABELS,
        ai_feature_defaults=USER_AI_FEATURE_DEFAULTS,
        ai_feature_models=feature_models,
        ai_feature_binding_defaults=feature_binding_defaults,
        ai_feature_model_options=feature_options,
        ai_runtime_settings=runtime_settings,
        ai_prompt_settings=prompt_settings,
        ai_session_duration_minutes=user_ai_session_minutes(),
    )


def _ai_session_payload() -> dict[str, object]:
    provider = request.args.get("provider") or _requested_provider()
    return provider_session_payload(provider)


@settings_bp.route("/", methods=["GET"])
def settings_page():
    # The passport is optional: None here simply means this browser has not
    # asked for one, and every control on the page still works.
    from ..passport_store import retention_days
    from .passport import current_passport

    return render_template(
        "settings.html",
        total_rules=len(get_all_rule_ids()),
        passport=current_passport(),
        passport_retention_days=retention_days(),
    )


@settings_bp.route("/ai", methods=["GET"])
def settings_ai_redirect():
    """Legacy AI settings path kept for existing links and cached pages."""
    return redirect(url_for("ai.settings_ai_page"), code=302)


@ai_bp.route("/", methods=["GET"])
def settings_ai_page():
    """Dedicated page for personal AI provider setup, model selection, and feature toggles."""
    return _render_ai_settings_page()


@settings_bp.route("/ai/key", methods=["POST"])
@ai_bp.route("/key", methods=["POST"])
def save_ollama_key():
    """Save a validated user-managed AI provider key and default model to the session."""
    provider = _requested_provider()
    api_key = _provider_api_key(provider)
    model = _provider_default_model(provider)

    if not api_key:
        return jsonify({"ok": False, "error": "API key is required."}), 400

    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    validated_hash = get_validated_key_hash(provider)
    if validated_hash != key_hash:
        return jsonify({
            "ok": False,
            "error": "Please check your key first, then save.",
        }), 400

    models = request.get_json(silent=True)
    if not isinstance(models, dict):
        models = {}
    known_models = models.get("models")
    if not isinstance(known_models, list):
        try:
            known_models = fetch_user_provider_models(provider, api_key)
        except Exception:
            known_models = []

    save_user_provider(provider, api_key, model, known_models)
    if "user_ai_features" not in session and "ollama_features" not in session:
        save_user_ai_feature_flags(dict(USER_AI_FEATURE_DEFAULTS))
    session.modified = True

    return jsonify({"ok": True, "provider": provider, "model": model})


@settings_bp.route("/ai/key", methods=["DELETE"])
@ai_bp.route("/key", methods=["DELETE"])
def forget_ollama_key():
    """Remove a user-managed provider key from the session."""
    provider = request.args.get("provider") or _requested_provider()
    remove_user_provider(provider)
    return jsonify({"ok": True, "provider": provider})


@settings_bp.route("/ai/features", methods=["POST"])
@ai_bp.route("/features", methods=["POST"])
def save_ollama_features():
    """Persist per-feature AI enable flags and provider/model bindings."""
    if not get_user_active_providers():
        return jsonify({"ok": False, "error": "No personal AI provider is active."}), 400

    updated: dict[str, bool] = {}
    feature_models: dict[str, str] = {}
    for feature in USER_AI_FEATURE_DEFAULTS:
        updated[feature] = request.form.get(f"feature_{feature}") == "1"
        chosen = str(request.form.get(f"model_{feature}") or "").strip()
        if chosen:
            provider, model = parse_model_ref(chosen)
            if provider and model and provider_model_supports_feature(provider, model, feature):
                feature_models[feature] = chosen

    save_user_ai_feature_flags(updated)
    save_user_ai_feature_models(feature_models)
    enabled = [USER_AI_FEATURE_LABELS.get(k, k) for k, v in updated.items() if v]
    return jsonify({"ok": True, "enabled": enabled})


@settings_bp.route("/ai/preferences", methods=["POST"])
@ai_bp.route("/preferences", methods=["POST"])
def save_ai_preferences():
    """Persist AI session-duration controls and prompt customizations."""
    runtime = save_user_ai_runtime_settings(
        request.form.get("session_minutes"),
        request.form.get("extend_minutes"),
    )
    prompts = save_user_ai_prompt_settings(
        {
            "alt_text_prompt": request.form.get("alt_text_prompt"),
            "markitdown_image_prompt": request.form.get("markitdown_image_prompt"),
        }
    )
    return jsonify(
        {
            "ok": True,
            "runtime": runtime,
            "prompts": prompts,
        }
    )


@settings_bp.route("/ai/validate", methods=["POST"])
@ai_bp.route("/validate", methods=["POST"])
def validate_ollama_key():
    """Validate a user-supplied provider key and return a normalized model catalog."""
    provider = _requested_provider()
    api_key = _provider_api_key(provider)
    if not api_key:
        return jsonify({"ok": False, "error": "No key supplied."}), 400

    try:
        models = fetch_user_provider_models(provider, api_key)
        set_validated_key_hash(provider, hashlib.sha256(api_key.encode("utf-8")).hexdigest())
        return jsonify({
            "ok": True,
            "provider": provider,
            "models": _serialize_provider_catalog(provider, models)[:80],
            "suggested_model": _suggested_model(provider, models),
        })
    except requests.HTTPError as exc:
        clear_validated_key_hash(provider)
        if exc.response is not None and exc.response.status_code == 401:
            return jsonify({"ok": False, "error": "Key rejected -- check it and try again."}), 200
        if exc.response is not None and exc.response.status_code == 429:
            return jsonify({"ok": False, "error": "Rate limited. Wait a moment and try again."}), 200
        return jsonify({"ok": False, "error": f"Could not validate {provider_metadata(provider).get('label', provider)}: {exc}"}), 200
    except requests.RequestException as exc:
        clear_validated_key_hash(provider)
        return jsonify({"ok": False, "error": f"Could not reach {provider_metadata(provider).get('label', provider)}: {exc}"}), 200


@settings_bp.route("/ai/session", methods=["GET"])
@ai_bp.route("/session", methods=["GET"])
def ollama_session_status():
    """Return the current active-provider key lease status for the session."""
    return jsonify(_ai_session_payload())


@settings_bp.route("/ai/session/extend", methods=["POST"])
@ai_bp.route("/session/extend", methods=["POST"])
def extend_ollama_session():
    """Extend the selected provider key lease by one full duration window."""
    provider = request.args.get("provider") or _requested_provider()
    if not is_user_provider_configured(provider):
        return jsonify({"ok": False, "error": "Your AI key session has expired. Re-enter your key to continue."}), 400
    extend_provider_expiry(provider)
    session.permanent = True
    session.modified = True
    return jsonify(provider_session_payload(provider))


@ai_bp.route("/client-log", methods=["POST"])
def client_log():
    """Accept structured browser-side diagnostics for AI page failures."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "JSON object required."}), 400

    entry = {
        "kind": _trim_text(payload.get("kind") or "client-error", 80),
        "message": _trim_text(payload.get("message") or "Unknown browser error", 600),
        "page": _trim_text(payload.get("page") or request.headers.get("Referer") or "", 200),
        "request_id": _trim_text(payload.get("request_id") or payload.get("requestId"), 80),
        "server_request_id": _trim_text(request.headers.get("X-Request-ID"), 80),
        "source": _trim_text(payload.get("source"), 120),
        "action": _trim_text(payload.get("action"), 120),
        "status": _trim_text(payload.get("status"), 40),
        "url": _trim_text(payload.get("url"), 200),
        "line": _trim_text(payload.get("line"), 20),
        "column": _trim_text(payload.get("column"), 20),
        "detail": _trim_text(payload.get("detail"), 1200),
        "stack": _trim_text(payload.get("stack"), 1500),
        "user_agent": _trim_text(request.user_agent.string, 200),
    }

    log.warning(
        "CLIENT_ERROR req=%s srv_req=%s kind=%s action=%s status=%s page=%s source=%s url=%s message=%s detail=%s stack=%s ua=%s",
        entry["request_id"],
        entry["server_request_id"],
        entry["kind"],
        entry["action"],
        entry["status"],
        entry["page"],
        entry["source"],
        entry["url"],
        entry["message"],
        entry["detail"],
        entry["stack"],
        entry["user_agent"],
    )
    return jsonify({"ok": True})
