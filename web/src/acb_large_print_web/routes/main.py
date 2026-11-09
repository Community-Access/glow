"""Landing page and anthem download routes."""

from pathlib import Path

from flask import Blueprint, current_app, redirect, render_template, send_file, url_for

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/aa", methods=["GET"])
def accessibility_agents_shortlink():
    """Send the short public URL to the Accessibility Agents landing page."""
    return redirect(url_for("accessibility_agents.accessibility_agents_page"), code=301)


@main_bp.route("/anthem/download")
def anthem_download():
    """Download the Let it GLOW anthem and record usage analytics."""
    from ..tool_usage import record as _record_usage

    anthem_path = Path(current_app.static_folder) / "let-it-glow.mp3"
    if not anthem_path.exists():
        # Let Flask return a clear 404 if asset is missing.
        return ("Anthem file not found.", 404)

    _record_usage("anthem_download")
    return send_file(
        str(anthem_path),
        mimetype="audio/mpeg",
        as_attachment=True,
        download_name="let-it-glow-theme.mp3",
    )
