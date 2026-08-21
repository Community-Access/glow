"""Short URLs for workshop rooms.

A URL that has to be read aloud, printed on a table card, or typed on a phone
by someone at the back of a room cannot be
``/workshop/session/ahg2026/activity/lab_accessible_communication``. The
packet requires short URLs, and makes them mandatory rather than an optional
companion to a QR code -- a QR code is useless to a participant using a screen
reader on the device they are holding.

So: ``letitglow.app/w/<code>`` joins a session, and ``/w/<code>/7`` opens the
seventh activity. Numbers rather than slugs because those are what a
facilitator says out loud: "everyone go to slash w slash A H G slash seven".

These are redirects into the real routes, so there is one implementation of
the workshop and one of its access control; this module only shortens the
way in.
"""

from __future__ import annotations

from flask import Blueprint, abort, redirect, request, url_for

from ..workshop_store import normalize_session_code

short_bp = Blueprint("shortlinks", __name__)


def _activity_order() -> list[str]:
    # Imported lazily: routes.workshop imports plenty, and this module is
    # registered early in app setup.
    from .workshop import ACTIVITY_ORDER

    return list(ACTIVITY_ORDER)


@short_bp.route("/w", methods=["GET"])
def short_workshop_home():
    return redirect(url_for("workshop.workshop_home"))


@short_bp.route("/w/<session_code>", methods=["GET"])
def short_session(session_code: str):
    """Join, or return to, a session by its code alone."""
    try:
        code = normalize_session_code(session_code)
    except ValueError:
        abort(404)
    return redirect(url_for("workshop.workshop_home", code=code))


@short_bp.route("/w/<session_code>/<int:number>", methods=["GET"])
def short_activity(session_code: str, number: int):
    """Open activity *number*, counting from one as a facilitator would."""
    try:
        code = normalize_session_code(session_code)
    except ValueError:
        abort(404)
    order = _activity_order()
    if number < 1 or number > len(order):
        abort(404)
    return redirect(
        url_for(
            "workshop.workshop_activity",
            session_code=code,
            activity_key=order[number - 1],
            **({"scenario": "surprise"} if request.args.get("surprise") else {}),
        )
    )
