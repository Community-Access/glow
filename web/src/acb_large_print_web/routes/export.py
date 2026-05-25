"""Export route -- convert a .docx to ACB-compliant HTML."""

import os
import uuid

import zipfile

from flask import Blueprint, abort, current_app, redirect, render_template, request, send_file, url_for

from acb_large_print.exporter import export_cms_fragment, export_standalone_html

from ..feature_flags import get_flag
from ..tasks.convert_tasks import create_job, run_export_job
from ..upload import UploadError, cleanup_token, get_temp_dir, validate_upload

export_bp = Blueprint("export", __name__)
_ASYNC_HEAVY_ENABLED = os.environ.get("GLOW_CONVERT_ASYNC", "1") == "1"


@export_bp.route("/", methods=["GET"])
def export_form():
    if not get_flag("GLOW_ENABLE_EXPORT_HTML", True):
        abort(404)
    return redirect(url_for("convert.convert_form"), 301)


@export_bp.route("/", methods=["POST"])
def export_submit():
    if not get_flag("GLOW_ENABLE_EXPORT_HTML", True):
        abort(404)
    token = None
    try:
        token, saved_path = validate_upload(request.files.get("document"))

        title = request.form.get("title", "").strip()
        mode = request.form.get("mode", "standalone")

        if _ASYNC_HEAVY_ENABLED and not current_app.config.get("TESTING", False):
            job_id = str(uuid.uuid4())
            create_job(
                job_id,
                "export",
                saved_path.name,
                meta={
                    "op": "export",
                    "upload_token": token,
                    "input_filename": saved_path.name,
                    "options": {
                        "title": title,
                        "mode": mode,
                    },
                },
            )
            run_export_job.delay(job_id, token, {"title": title, "mode": mode})
            return redirect(url_for("jobs.job_progress", job_id=job_id))

        temp_dir = get_temp_dir(token)

        if mode == "cms":
            output_path = temp_dir / "output.html"
            export_cms_fragment(saved_path, output_path, title=title)

            response = send_file(
                str(output_path),
                as_attachment=True,
                download_name=(saved_path.stem + "-cms.html"),
                mimetype="text/html",
            )
        else:
            # Standalone: HTML + CSS, bundled as a ZIP
            html_path = temp_dir / "output.html"
            export_standalone_html(saved_path, html_path, title=title)
            css_path = temp_dir / "acb-large-print.css"

            zip_path = temp_dir / "export.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                html_name = saved_path.stem + ".html"
                zf.write(html_path, html_name)
                if css_path.exists():
                    zf.write(css_path, "acb-large-print.css")

            response = send_file(
                str(zip_path),
                as_attachment=True,
                download_name=(saved_path.stem + "-acb-html.zip"),
                mimetype="application/zip",
            )

        @response.call_on_close
        def _cleanup():
            cleanup_token(token)

        return response

    except UploadError as e:
        if token:
            cleanup_token(token)
        return render_template("export_form.html", error=str(e)), 400
    except Exception as exc:
        if token:
            cleanup_token(token)
        return (
            render_template(
                "export_form.html",
                error=str(exc) or "An error occurred while exporting the document. "
                "Please ensure it is a valid .docx file and try again.",
            ),
            500,
        )
