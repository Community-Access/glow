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


# ---------------------------------------------------------------------------
# Accessing Higher Ground 2026: one address for everything
# ---------------------------------------------------------------------------
#
# letitglow.app/ahg is the address on the program, the slides and the table
# cards. It is the landing page itself, not a redirect, so it is the page a
# person bookmarks. The variations people will type all arrive there too.
# www.letitglow.app and lp.csedesigns.com redirect to letitglow.app with the
# path kept, in the Caddyfile, so they reach this route unchanged.


@short_bp.route("/ahg", methods=["GET"], strict_slashes=False)
def ahg_landing():
    from .workshop import render_ahg_landing

    return render_ahg_landing()


@short_bp.route("/AHG", methods=["GET"], strict_slashes=False)
@short_bp.route("/Ahg", methods=["GET"], strict_slashes=False)
@short_bp.route("/ahg2026", methods=["GET"], strict_slashes=False)
@short_bp.route("/ahg-2026", methods=["GET"], strict_slashes=False)
@short_bp.route("/AHG2026", methods=["GET"], strict_slashes=False)
def ahg_landing_alias():
    return redirect(url_for("shortlinks.ahg_landing"), code=301)


@short_bp.route("/ahg/share", methods=["GET"], strict_slashes=False)
def ahg_share_short():
    query = request.query_string.decode("utf-8")
    target = url_for("workshop.ahg_share")
    return redirect(f"{target}?{query}" if query else target)


@short_bp.route("/ahg/kit", methods=["GET"], strict_slashes=False)
def ahg_kit_short():
    # The kit, online: every file readable without unzipping anything.
    from .workshop import render_ahg_kit_index

    return render_ahg_kit_index()


@short_bp.route("/ahg/kit.zip", methods=["GET"])
def ahg_kit_zip_short():
    return redirect(url_for("workshop.ahg_kit_zip"))


@short_bp.route("/ahg/kit/raw/<path:rel>", methods=["GET"])
def ahg_kit_raw(rel: str):
    from .workshop import send_ahg_kit_raw

    return send_ahg_kit_raw(rel)


@short_bp.route("/ahg/kit/<path:rel>", methods=["GET"])
def ahg_kit_file(rel: str):
    from .workshop import render_ahg_kit_file

    return render_ahg_kit_file(rel)


@short_bp.route("/ahg/slides", methods=["GET"], strict_slashes=False)
def ahg_slides_short():
    return redirect(url_for("workshop.workshop_deck"))


@short_bp.route("/ahg/site", methods=["GET"], strict_slashes=False)
def ahg_site():
    from .workshop import render_ahg_site

    return render_ahg_site()


@short_bp.route("/ahg/site/<path:name>", methods=["GET"])
def ahg_site_file(name: str):
    from .workshop import send_ahg_site_file

    return send_ahg_site_file(name)
