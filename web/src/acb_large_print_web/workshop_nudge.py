"""The 30-day nudge: the loop the workshop is named after, closed.

The W in GLOW is "walk forward". The workshop's whole theory of change is
that people leave and act, and the 30-Day Action Plan is the mechanism -- but
a plan nobody is ever reminded of is a piece of paper in a conference bag.

This is a command rather than a background job on purpose. Sending mail to
thirty people a month after an event is a decision a person should make, at a
time they choose, having looked at what is about to go out. `--dry-run` is the
default posture: see the list first.

    flask --app acb_large_print_web.app:create_app workshop-nudge SESSION --dry-run
    flask --app acb_large_print_web.app:create_app workshop-nudge SESSION --send

Nobody is emailed twice: every send is recorded, and a participant who never
gave an address is never in the list at all.
"""

from __future__ import annotations

import click
from flask import Flask, url_for

from .email import email_configured, send_workshop_nudge_email
from .workshop_store import (
    create_return_link,
    decode_field_values,
    participants_due_for_nudge,
    record_nudge,
)


def _commitment_of(row: dict) -> str:
    values = decode_field_values(row)
    promise = (values.get("workflow_30", "") or "").strip()
    first_step = (values.get("first_step_30", "") or "").strip()
    if promise and first_step:
        return f"{promise} First step: {first_step}"
    return promise or first_step


def register_cli(app: Flask) -> None:
    @app.cli.command("workshop-nudge")
    @click.argument("session_code")
    @click.option("--days", default=30, show_default=True, help="How long since they committed.")
    @click.option("--send/--dry-run", default=False, help="Actually send. Defaults to a dry run.")
    @click.option("--limit", default=0, help="Stop after this many (0 means no limit).")
    def workshop_nudge(session_code: str, days: int, send: bool, limit: int) -> None:
        """Ask participants of SESSION_CODE how their 30-day commitment went."""
        due = participants_due_for_nudge(session_code, days=days)
        if limit > 0:
            due = due[:limit]

        if not due:
            click.echo("Nobody is due a nudge for this session.")
            return

        click.echo(f"{len(due)} participant(s) due, {days} days on:")
        for row in due:
            commitment = _commitment_of(row)
            click.echo(f"  - {row.get('display_name', 'Participant')}: {commitment[:70]}")

        if not send:
            click.echo("Dry run. Re-run with --send to actually email these people.")
            return

        if not email_configured():
            raise click.ClickException(
                "POSTMARK_SERVER_TOKEN is not set, so nothing can be sent."
            )

        sent = 0
        for row in due:
            key = str(row.get("participant_key", ""))
            token = create_return_link(session_code, key)
            # Land them on the follow-through log, which is where the answer
            # to "how did it go" belongs.
            link = url_for(
                "workshop.workshop_return", token=token, next="follow-through", _external=True
            )
            ok, detail = send_workshop_nudge_email(
                str(row.get("login_email", "")),
                participant_name=str(row.get("display_name", "")),
                commitment=_commitment_of(row),
                return_link=link,
                days=days,
            )
            if ok:
                record_nudge(session_code, key)
                sent += 1
            else:
                click.echo(f"  ! {row.get('display_name', 'Participant')}: {detail}")

        click.echo(f"Sent {sent} of {len(due)}.")
