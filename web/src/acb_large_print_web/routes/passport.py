"""Routes for the GLOW passport -- settings that travel, by email link.

Nothing here is required to use GLOW. A visitor who never touches these
routes gets exactly the product they had before: preferences in local
storage, no server-side record, nothing stored about them at all.

The mechanism is the workshop return link, generalised: a single-use token,
hashed at rest, time-boxed, landing only on an allow-listed destination.
"""

from __future__ import annotations

import json

from flask import (
    Blueprint,
    abort,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from ..app import limiter
from ..email import _POSTMARK_STREAM as _postmark_stream
from ..email import _from_address as _postmark_from  # noqa: F401  (documented in the panel)
from ..email import _send as _postmark_send
from ..email import email_configured, render_email
from ..passport_store import (
    COOKIE_NAME,
    RETURN_DESTINATIONS,
    clear_history,
    consume_link,
    create_link,
    create_passport,
    forget_passport,
    get_passport,
    link_ttl_days,
    list_history,
    purge_expired,
    retention_days,
    update_passport,
)

passport_bp = Blueprint("passport", __name__)

COOKIE_MAX_AGE = 60 * 60 * 24 * 90


MESSAGES = {
    "saved": ("Your settings are saved to this browser and to your passport.", False),
    "sent": ("Check your email. Your link is on its way.", False),
    "restored": ("Welcome back. Your settings have been restored.", False),
    "forgotten": ("Your passport and everything in it have been deleted.", False),
    "history-cleared": ("Your history has been deleted.", False),
    "invalid-email": ("Enter an email address in the form name@example.com.", True),
    "email-unavailable": ("Email is not available on this server, so no link can be sent.", True),
    "send-failed": ("We could not send that email. Please try again later.", True),
    "no-passport": ("There is no passport on this browser yet.", True),
}


def _looks_like_email(value: str) -> bool:
    candidate = (value or "").strip()
    if not candidate or len(candidate) > 254 or " " in candidate:
        return False
    local, at, domain = candidate.partition("@")
    return bool(local and at and "." in domain and not domain.startswith(".") and not domain.endswith("."))


def current_passport() -> dict | None:
    """The passport this browser carries, if any. Never creates one."""
    return get_passport((request.cookies.get(COOKIE_NAME) or "").strip())


def _set_cookie(response, passport_id: str):
    response.set_cookie(
        COOKIE_NAME,
        passport_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
    )
    return response


def _message() -> tuple[str, bool]:
    return MESSAGES.get((request.args.get("m") or "").strip(), ("", False))


def _send_passport_link(email: str, link: str, *, restoring: bool) -> tuple[bool, str]:
    """One link, one purpose, in the house layout."""
    intro = (
        "Here is your link back to your GLOW settings. Open it on any device "
        "and your preferences, defaults and choices come with you."
    )
    html_body, text_body = render_email(
        title="Your GLOW settings link",
        intro=intro,
        bullets=(
            f"The link works once and expires in {link_ttl_days()} days.",
            f"Your settings are kept for {retention_days()} days after you last use them.",
            "You can delete everything from the passport page at any time.",
            link,
        ),
        closing=(
            "If you did not ask for this, you can ignore it. Nothing changes "
            "until the link is opened."
        ),
    )
    payload = {
        "From": _postmark_from(),
        "To": email,
        "Subject": "Your GLOW settings link",
        "HtmlBody": html_body + f'<p><a href="{link}">Restore my settings</a></p>',
        "TextBody": text_body,
        "MessageStream": _postmark_stream,
    }
    return _postmark_send(payload, email)


@passport_bp.route("/", methods=["GET"])
def passport_page():
    """What is stored, what it is for, and how to delete it."""
    passport = current_passport()
    message, message_is_error = _message()
    return render_template(
        "passport.html",
        passport=passport,
        settings_count=len(passport.get("settings", {})) if passport else 0,
        history=list_history(passport["passport_id"]) if passport and passport.get("history_enabled") else [],
        email_available=email_configured(),
        retention_days=retention_days(),
        link_ttl_days=link_ttl_days(),
        message=message,
        message_is_error=message_is_error,
        status_prefix=("Not saved" if message_is_error else ("Saved" if message else "")),
    )


@passport_bp.route("/save", methods=["POST"])
@limiter.limit("30 per hour")
def passport_save():
    """Create or update a passport from the settings page.

    The settings blob is posted by the browser, because that is where GLOW's
    preferences already live. The server stores it verbatim and hands it back
    on the way in; it does not interpret it.
    """
    raw_settings = request.form.get("settings_json") or "{}"
    try:
        settings = json.loads(raw_settings)
        if not isinstance(settings, dict):
            settings = {}
    except (TypeError, ValueError):
        settings = {}

    email = (request.form.get("email") or "").strip()
    wants_link = bool(request.form.get("send_link"))
    notify = bool(request.form.get("notify_enabled"))
    # History is opt-in, and saving settings must never turn it on by itself.
    history = bool(request.form.get("history_enabled"))

    if email and not _looks_like_email(email):
        return redirect(url_for("passport.passport_page", m="invalid-email"))

    passport = current_passport()
    if passport is None:
        passport_id = create_passport(
            settings=settings,
            email=email,
            notify_enabled=notify,
            history_enabled=history,
        )
    else:
        passport_id = passport["passport_id"]
        update_passport(
            passport_id,
            settings=settings,
            email=email if email else None,
            notify_enabled=notify,
            history_enabled=history,
        )
        if not history and passport.get("history_enabled"):
            # Turning history off deletes what it collected. Leaving the rows
            # behind would make the switch a lie.
            clear_history(passport_id)

    outcome = "saved"
    if wants_link:
        if not email:
            outcome = "invalid-email"
        elif not email_configured():
            outcome = "email-unavailable"
        else:
            link = url_for("passport.passport_return", token=create_link(passport_id), _external=True)
            sent, _detail = _send_passport_link(email, link, restoring=False)
            outcome = "sent" if sent else "send-failed"

    # Cheap opportunistic tidying: retention is a promise, not a cron job.
    try:
        purge_expired()
    except Exception:  # pragma: no cover - never fail a save over housekeeping
        pass

    response = make_response(redirect(url_for("passport.passport_page", m=outcome)))
    return _set_cookie(response, passport_id)


@passport_bp.route("/return/<token>", methods=["GET"])
def passport_return(token: str):
    """Spend a link and re-attach this browser to its passport."""
    status, passport = consume_link(token)
    if status != "ok" or not passport:
        return render_template("passport_link_invalid.html", status=status), 403

    destination = RETURN_DESTINATIONS.get(
        (request.args.get("next") or "").strip(), RETURN_DESTINATIONS["passport"]
    )
    target = url_for(destination)
    if destination == RETURN_DESTINATIONS["passport"]:
        target = url_for("passport.passport_page", m="restored")
    response = make_response(redirect(target))
    return _set_cookie(response, str(passport["passport_id"]))


@passport_bp.route("/settings.json", methods=["GET"])
def passport_settings():
    """The stored settings blob, for the browser to apply on arrival."""
    passport = current_passport()
    if not passport:
        return {"passport": False, "settings": {}}
    return {"passport": True, "settings": passport.get("settings", {})}


@passport_bp.route("/link", methods=["POST"])
@limiter.limit("5 per hour")
def passport_link():
    """Email myself a link from the passport page."""
    passport = current_passport()
    if not passport:
        return redirect(url_for("passport.passport_page", m="no-passport"))

    email = (request.form.get("email") or "").strip() or str(passport.get("email") or "")
    if not _looks_like_email(email):
        return redirect(url_for("passport.passport_page", m="invalid-email"))
    if not email_configured():
        return redirect(url_for("passport.passport_page", m="email-unavailable"))

    update_passport(passport["passport_id"], email=email)
    link = url_for(
        "passport.passport_return", token=create_link(passport["passport_id"]), _external=True
    )
    sent, _detail = _send_passport_link(email, link, restoring=True)
    return redirect(url_for("passport.passport_page", m="sent" if sent else "send-failed"))


@passport_bp.route("/forget", methods=["POST"])
def passport_forget():
    """Delete everything, and say what was deleted."""
    passport = current_passport()
    if not passport:
        return redirect(url_for("passport.passport_page", m="no-passport"))

    summary = forget_passport(passport["passport_id"])
    response = make_response(
        redirect(
            url_for(
                "passport.passport_page",
                m="forgotten",
                deleted_history=summary["history_entries"],
                deleted_email=int(summary["email"]),
            )
        )
    )
    response.delete_cookie(COOKIE_NAME)
    return response


@passport_bp.route("/history/clear", methods=["POST"])
def passport_history_clear():
    passport = current_passport()
    if not passport:
        return redirect(url_for("passport.passport_page", m="no-passport"))
    clear_history(passport["passport_id"])
    return redirect(url_for("passport.passport_page", m="history-cleared"))


@passport_bp.route("/history", methods=["GET"])
def passport_history():
    """A separate page so the passport page stays short."""
    passport = current_passport()
    if not passport:
        abort(404)
    return render_template(
        "passport_history.html",
        entries=list_history(passport["passport_id"]),
        enabled=bool(passport.get("history_enabled")),
    )
