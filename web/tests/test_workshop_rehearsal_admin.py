from __future__ import annotations

import pytest

from acb_large_print_web.app import create_app
from acb_large_print_web import workshop_store
from acb_large_print_web.workshop_rehearsal_admin import cleanup, provision


@pytest.fixture
def rehearsal_app(tmp_path):
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    app.instance_path = str(tmp_path)
    workshop_store.reset_schema_cache()
    with app.app_context():
        yield app
    workshop_store.reset_schema_cache()


def test_cleanup_removes_only_the_matching_rehearsal_session(rehearsal_app):
    code = "ahg-load-test-123456-1"
    run_id, attempt = "123456", "1"

    with rehearsal_app.app_context():
        provision(code, run_id, attempt)
        conn = workshop_store._conn()
        conn.execute(
            "INSERT INTO workshop_participants "
            "(participant_key, session_code, display_name, created_at_utc, updated_at_utc, last_seen_at_utc) "
            "VALUES (?, ?, ?, 'now', 'now', 'now')",
            ("test-participant", code, "Rehearsal participant"),
        )
        conn.execute(
            "INSERT INTO workshop_submissions "
            "(session_code, activity_key, display_name, content_text, created_at_utc, updated_at_utc) "
            "VALUES (?, 'journey_check_in', 'Rehearsal participant', 'test', 'now', 'now')",
            (code,),
        )
        conn.commit()
        conn.close()

        result = cleanup(code, run_id, attempt)
        assert result["action"] == "cleaned"
        assert result["remaining"]
        assert set(result["remaining"].values()) == {0}


def test_cleanup_refuses_unexpected_related_records_without_deleting(rehearsal_app):
    code = "ahg-load-test-123456-2"
    run_id, attempt = "123456", "2"

    with rehearsal_app.app_context():
        provision(code, run_id, attempt)
        conn = workshop_store._conn()
        conn.execute(
            "INSERT INTO workshop_feedback "
            "(session_code, submission_id, reviewer_display_name, strength, risk_or_gap, "
            "recommended_safeguard, reuse_suggestion, created_at_utc) "
            "VALUES (?, 1, 'reviewer', 'strength', 'risk', 'safeguard', 'reuse', 'now')",
            (code,),
        )
        conn.commit()
        conn.close()

        with pytest.raises(ValueError, match="operator review required"):
            cleanup(code, run_id, attempt)

        assert workshop_store.get_session(code) is not None


@pytest.mark.parametrize(
    ("code", "run_id", "attempt"),
    [
        ("ahg-2026", "123456", "1"),
        ("ahg-load-test-123456-1", "123456", "2"),
        ("ahg-load-test-123456-x", "123456", "x"),
    ],
)
def test_provision_requires_exact_generated_test_identity(rehearsal_app, code, run_id, attempt):
    with rehearsal_app.app_context(), pytest.raises(ValueError):
        provision(code, run_id, attempt)
