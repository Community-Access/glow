"""Secure credential loading helpers for the web app.

Lookup order for secrets:
1) Environment variable (preferred for production)
2) Local server.credentials file (developer convenience)

The file path defaults to repository root server.credentials and can be overridden
with SERVER_CREDENTIALS_PATH. This module never logs secret values.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from datetime import UTC, datetime, timedelta


def _credentials_path() -> Path:
    raw = os.environ.get("SERVER_CREDENTIALS_PATH", "").strip()
    if raw:
        return Path(raw)
    # repo root from web/src/acb_large_print_web -> ../../../.. /server.credentials
    return Path(__file__).resolve().parents[3] / "server.credentials"


@lru_cache(maxsize=1)
def _load_file_map() -> dict[str, str]:
    path = _credentials_path()
    out: dict[str, str] = {}
    if not path.exists():
        return out

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped and not stripped.startswith("http"):
            k, v = stripped.split("=", 1)
            out[k.strip().lower()] = v.strip()
            continue
        if ":" in stripped:
            k, v = stripped.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def secret(name: str, env_name: str | None = None) -> str:
    """Resolve a secret from env first, then server.credentials."""
    if env_name:
        v = os.environ.get(env_name, "").strip()
        if v:
            return v

    data = _load_file_map()
    aliases: dict[str, tuple[str, ...]] = {
        "openrouter_api_key": (
            "openrouter_api_key",
            "openrouter",
            "openrouter api key",
        ),
        "ssh_password": (
            "ssh_password",
            "password",
        ),
    }
    keys = aliases.get(name, (name,))
    for key in keys:
        v = data.get(key.lower(), "").strip()
        if v:
            return v
    return ""


def get_openrouter_api_key() -> str:
    return secret("openrouter_api_key", "OPENROUTER_API_KEY")


# ---------------------------------------------------------------------------
# User-supplied Ollama Cloud key (session-scoped, never logged or persisted)
# ---------------------------------------------------------------------------

_OLLAMA_CLOUD_URL = "https://ollama.com"
_OLLAMA_CLOUD_API = f"{_OLLAMA_CLOUD_URL}/api"
_OLLAMA_SESSION_EXPIRY_KEY = "ollama_key_expires_at"
_OLLAMA_SESSION_MINUTES = int(
    os.environ.get("OLLAMA_KEY_SESSION_MINUTES", os.environ.get("SESSION_TIMEOUT_MINUTES", "240"))
)

#: Models recommended per GLOW feature, shown in the setup UI.
#: ``plan``  -- Ollama plan required: "free", "pro", or "max".
#: ``speed`` -- subjective speed tier: "fast", "moderate", or "slow".
#: Pricing info is maintained here manually; Ollama has no public pricing API.
#: Reference: https://ollama.com/pricing
OLLAMA_MODEL_RECOMMENDATIONS: list[dict] = [
    {
        "id": "gemma3:4b",
        "label": "Gemma 3 (4B)",
        "recommended": True,
        "plan": "free",
        "speed": "fast",
        "features": ["heading_fix", "markitdown", "chat", "playground"],
        "note": "Reliable free Ollama Cloud model for playground and document workflows.",
    },
    {
        "id": "gemma3:12b",
        "label": "Gemma 3 (12B)",
        "recommended": False,
        "plan": "free",
        "speed": "moderate",
        "features": ["chat", "playground", "markitdown"],
        "note": "Stronger free model when available on your account.",
    },
    {
        "id": "llama3.2",
        "label": "Llama 3.2 (3B)",
        "recommended": False,
        "plan": "free",
        "speed": "fast",
        "features": ["heading_fix", "markitdown", "chat", "playground"],
        "note": "Legacy recommendation. May not be available on every Ollama Cloud account.",
    },
    {
        "id": "llama3.3",
        "label": "Llama 3.3 (70B)",
        "recommended": False,
        "plan": "pro",
        "speed": "slow",
        "features": ["chat"],
        "note": "Best accuracy for Document Chat. Requires a paid Pro or Max plan.",
    },
    {
        "id": "mistral",
        "label": "Mistral (7B)",
        "recommended": False,
        "plan": "free",
        "speed": "moderate",
        "features": ["heading_fix", "markitdown", "chat"],
        "note": "Balanced quality and speed.",
    },
    {
        "id": "qwen3:8b",
        "label": "Qwen3 (8B)",
        "recommended": False,
        "plan": "free",
        "speed": "moderate",
        "features": ["heading_fix", "markitdown", "chat"],
        "note": "Strong reasoning. Good alternative to Llama.",
    },
    {
        "id": "phi4-mini",
        "label": "Phi-4 Mini (3.8B)",
        "recommended": False,
        "plan": "free",
        "speed": "fast",
        "features": ["heading_fix", "markitdown"],
        "note": "Microsoft small model. Very fast, lower accuracy than Llama.",
    },
]


#: Which Ollama features are on by default when a user first activates a key.
#: Chat is intentionally OFF until we have sufficient testing coverage.
OLLAMA_FEATURE_DEFAULTS: dict[str, bool] = {
    "heading_fix": True,
    "markitdown": True,
    "chat": False,
    "playground": True,  # Beta: open-ended chat playground, no document required
}

#: Human-readable labels for each toggleable Ollama feature.
OLLAMA_FEATURE_LABELS: dict[str, str] = {
    "heading_fix": "AI Heading Detection (Fix workflow)",
    "markitdown": "AI Document Formatting (MarkItDown)",
    "chat": "Document Chat",
    "playground": "AI Playground (Beta)",
}

#: Default model to use for each feature. Falls back to the session global model.
#: heading_fix and markitdown work best with fast small models.
#: chat and playground benefit from slightly larger models when available.
OLLAMA_FEATURE_MODEL_DEFAULTS: dict[str, str] = {
    "heading_fix": "gemma3:4b",
    "markitdown": "gemma3:4b",
    "chat": "gemma3:4b",
    "playground": "gemma3:4b",
}


def get_user_ollama_features() -> dict[str, bool]:
    """Return the per-feature Ollama enable flags from the current session.

    Falls back to OLLAMA_FEATURE_DEFAULTS for any key not yet stored.
    """
    try:
        from flask import session
        stored: dict = session.get("ollama_features", {})
        return {k: bool(stored.get(k, default)) for k, default in OLLAMA_FEATURE_DEFAULTS.items()}
    except RuntimeError:
        return dict(OLLAMA_FEATURE_DEFAULTS)


def get_ollama_session_duration_minutes() -> int:
    """Return the configured Ollama key lease duration in minutes."""
    return max(15, _OLLAMA_SESSION_MINUTES)


def get_user_ollama_expiry() -> datetime | None:
    """Return the expiration timestamp for the current session-scoped Ollama key."""
    try:
        from flask import session

        raw = str(session.get(_OLLAMA_SESSION_EXPIRY_KEY, "") or "").strip()
    except RuntimeError:
        return None

    if not raw:
        return None
    try:
        expires_at = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if expires_at.tzinfo is None:
        return expires_at.replace(tzinfo=UTC)
    return expires_at.astimezone(UTC)


def get_user_ollama_seconds_remaining() -> int:
    """Return seconds until the Ollama key lease expires for this session."""
    expires_at = get_user_ollama_expiry()
    if not expires_at:
        return 0
    return max(0, int((expires_at - datetime.now(UTC)).total_seconds()))


def set_user_ollama_expiry(expires_at: datetime) -> datetime | None:
    """Persist the Ollama key expiration timestamp in the Flask session."""
    try:
        from flask import session
    except RuntimeError:
        return None

    normalized = expires_at.astimezone(UTC) if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
    session[_OLLAMA_SESSION_EXPIRY_KEY] = normalized.isoformat()
    session.modified = True
    return normalized


def refresh_user_ollama_expiry() -> datetime | None:
    """Reset the Ollama key lease to a fresh full-duration window from now."""
    return set_user_ollama_expiry(
        datetime.now(UTC) + timedelta(minutes=get_ollama_session_duration_minutes())
    )


def extend_user_ollama_expiry() -> datetime | None:
    """Extend the Ollama key lease by another full-duration window."""
    current = get_user_ollama_expiry()
    base = current if current and current > datetime.now(UTC) else datetime.now(UTC)
    return set_user_ollama_expiry(
        base + timedelta(minutes=get_ollama_session_duration_minutes())
    )


def clear_user_ollama_session() -> None:
    """Remove the session-scoped Ollama key, metadata, and feature choices."""
    try:
        from flask import session
    except RuntimeError:
        return

    for key in (
        "ollama_api_key",
        "ollama_model",
        "ollama_features",
        "ollama_feature_models",
        "ollama_validated",
        "ollama_validated_key_hash",
        _OLLAMA_SESSION_EXPIRY_KEY,
    ):
        session.pop(key, None)
    session.modified = True


def is_ollama_feature_enabled(feature: str) -> bool:
    """Return True if the named Ollama feature is active for this session.

    ``feature`` must be one of the keys in OLLAMA_FEATURE_DEFAULTS.
    Returns the default value when Ollama is not configured.
    """
    if not is_ollama_configured():
        return False
    return get_user_ollama_features().get(feature, OLLAMA_FEATURE_DEFAULTS.get(feature, False))


def get_user_ollama_key() -> str:
    """Return the user-supplied Ollama Cloud API key from the Flask session.

    The key is stored only in the server-side session -- never logged, never
    written to disk, never sent to the client. Cleared when the session ends
    or when the user clicks 'Forget my key'.
    """
    try:
        from flask import session
        return session.get("ollama_api_key", "")
    except RuntimeError:
        return ""


def get_user_ollama_model() -> str:
    """Return the Ollama model the user has chosen, defaulting to gemma3:4b."""
    try:
        from flask import session
        return session.get("ollama_model", "gemma3:4b")
    except RuntimeError:
        return "gemma3:4b"


def get_user_ollama_model_for(feature: str) -> str:
    """Return the model the user has chosen for a specific feature.

    Falls back to OLLAMA_FEATURE_MODEL_DEFAULTS, then to the session global model.
    """
    try:
        from flask import session
        feature_models: dict = session.get("ollama_feature_models", {})
        if feature in feature_models and feature_models[feature]:
            return feature_models[feature]
    except RuntimeError:
        pass
    return OLLAMA_FEATURE_MODEL_DEFAULTS.get(feature, get_user_ollama_model())


def is_ollama_configured() -> bool:
    """Return True if the user has provided an Ollama Cloud API key this session."""
    key = get_user_ollama_key()
    if not key:
        return False

    expires_at = get_user_ollama_expiry()
    if not expires_at:
        refresh_user_ollama_expiry()
        return True

    if get_user_ollama_seconds_remaining() <= 0:
        clear_user_ollama_session()
        return False
    return True


def get_ollama_cloud_url() -> str:
    return _OLLAMA_CLOUD_API


def get_bootstrap_admin_email() -> str:
    return os.environ.get("ADMIN_LOCAL_EMAIL", "jeffbis@arizona.edu").strip().lower()


def get_bootstrap_admin_password() -> str:
    # Support multiple env var names for a local bootstrap/admin password.
    # Priority: ADMIN_PASSWORD -> ADMIN_LOCAL_PASSWORD -> server.credentials ssh_password
    return (
        os.environ.get("ADMIN_PASSWORD", "").strip()
        or os.environ.get("ADMIN_LOCAL_PASSWORD", "").strip()
        or secret("ssh_password")
    )
