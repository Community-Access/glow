"""Template route -- generate an ACB-compliant Word template (.dotx)."""

import os
import uuid

from flask import Blueprint, current_app, redirect, render_template, request, send_file, url_for

from acb_large_print.template import create_template

from ..tasks.convert_tasks import create_job, run_template_job
from ..upload import UPLOAD_TEMP_BASE, cleanup_tempdir

template_bp = Blueprint("template", __name__)
_ASYNC_HEAVY_ENABLED = os.environ.get("GLOW_CONVERT_ASYNC", "1") == "1"


@template_bp.route("/", methods=["GET"])
def template_form():
    return render_template("template_form.html")


@template_bp.route("/", methods=["POST"])
def template_submit():
    temp_dir = None
    try:
        from ..tool_usage import record as _record_usage
        _record_usage("template")
        title = request.form.get("title", "").strip() or "ACB Large Print Document"
        bound = request.form.get("bound") == "on"
        include_sample = request.form.get("include_sample") == "on"
        standards_profile = request.form.get("standards_profile", "acb_2025")
        raw_allowed_levels = request.form.getlist("allowed_heading_levels")
        allowed_heading_levels: list[int] = []
        for raw in raw_allowed_levels:
            try:
                level = int(raw)
            except (TypeError, ValueError):
                continue
            if 1 <= level <= 6:
                allowed_heading_levels.append(level)
        if not allowed_heading_levels:
            allowed_heading_levels = [1, 2, 3]
        allowed_heading_levels = sorted(set(allowed_heading_levels))

        # Optional per-style font-size overrides (empty fields fall back to ACB defaults)
        from acb_large_print import constants as _C
        style_size_overrides: dict[str, float] = {}
        _size_field_map = {
            "body_size_pt": "Normal",
            "h1_size_pt": "Heading 1",
            "h2_size_pt": "Heading 2",
            "h3_size_pt": "Heading 3",
            "h4_size_pt": "Heading 4",
            "h5_size_pt": "Heading 5",
            "h6_size_pt": "Heading 6",
        }
        for field, style_name in _size_field_map.items():
            raw = (request.form.get(field) or "").strip()
            if not raw:
                continue
            try:
                pt = float(raw)
            except (TypeError, ValueError):
                continue
            if pt <= 0:
                continue
            style_size_overrides[style_name] = max(
                _C.MIN_USER_FONT_PT, min(_C.MAX_USER_FONT_PT, pt)
            )

        # Create a temp dir for the output
        token = str(uuid.uuid4())
        temp_dir = UPLOAD_TEMP_BASE / token
        temp_dir.mkdir(parents=True, exist_ok=True)

        if _ASYNC_HEAVY_ENABLED and not current_app.config.get("TESTING", False):
            job_id = str(uuid.uuid4())
            create_job(
                job_id,
                "template",
                f"{title}.dotx",
                meta={
                    "op": "template",
                    "upload_token": token,
                    "input_filename": f"{title}.dotx",
                    "options": {
                        "title": title,
                        "bound": bound,
                        "include_sample": include_sample,
                        "standards_profile": standards_profile,
                        "allowed_heading_levels": allowed_heading_levels,
                        "style_size_overrides": style_size_overrides or None,
                    },
                },
            )
            run_template_job.delay(
                job_id,
                token,
                {
                    "title": title,
                    "bound": bound,
                    "include_sample": include_sample,
                    "standards_profile": standards_profile,
                    "allowed_heading_levels": allowed_heading_levels,
                    "style_size_overrides": style_size_overrides or None,
                },
            )
            return redirect(url_for("jobs.job_progress", job_id=job_id))

        output_path = temp_dir / "ACB-Large-Print-Template.dotx"

        create_template(
            output_path,
            bound=bound,
            include_sample=include_sample,
            title=title,
            standards_profile=standards_profile,
            allowed_heading_levels=allowed_heading_levels,
            style_size_overrides=style_size_overrides or None,
        )

        response = send_file(
            str(output_path),
            as_attachment=True,
            download_name="ACB-Large-Print-Template.dotx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.template",
        )

        @response.call_on_close
        def _cleanup():
            cleanup_tempdir(temp_dir)

        return response

    except Exception as exc:
        import logging

        logging.getLogger("acb_large_print").exception(
            "Template creation failed: %s", exc
        )
        if temp_dir:
            cleanup_tempdir(temp_dir)
        return (
            render_template(
                "template_form.html",
                error=str(exc) or "An error occurred while creating the template. Please try again.",
            ),
            500,
        )
