"""Celery application factory.

Celery is OPTIONAL infrastructure.  When ``CELERY_BROKER_URL`` is not set in
the environment the queue operates in "eager" (synchronous) mode -- tasks run
inline in the web process and the caller receives an immediate result.  This
lets the app run correctly on a single container without Redis.

To enable the full async queue:
  1. Start Redis: ``docker run -d -p 6379:6379 redis:7-alpine``
  2. Set env var: ``CELERY_BROKER_URL=redis://localhost:6379/0``
  3. Start a worker: ``celery -A acb_large_print_web.tasks worker --loglevel=INFO``

The ``make_celery(app)`` factory is called from ``create_app`` so tasks run
inside the Flask application context with access to config, DB, etc.
"""

from __future__ import annotations

import os

from celery import Celery

# ---------------------------------------------------------------------------
# Celery singleton (configured lazily; bound to Flask app in create_app)
# ---------------------------------------------------------------------------

_broker = os.environ.get("CELERY_BROKER_URL", "")
_backend = os.environ.get("CELERY_RESULT_BACKEND", _broker or "")

# Use in-memory eager mode when no broker is configured.
_eager = not bool(_broker)

celery_app = Celery(
    "glow",
    broker=_broker or "memory://localhost/",
    backend=_backend or "cache+memory://",
    include=["acb_large_print_web.tasks.convert_tasks"],
)

celery_app.conf.update(
    task_always_eager=_eager,
    task_eager_propagates=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Soft time limit: 20 min; hard: 25 min
    task_soft_time_limit=1200,
    task_time_limit=1500,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # results kept in Redis for 1 hour
)


def make_celery(flask_app) -> Celery:
    """Bind the Celery app to a Flask application context.

    Call this from ``create_app`` after the Flask app is fully configured.
    """
    class ContextTask(celery_app.Task):  # type: ignore[misc]
        abstract = True

        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask  # type: ignore[assignment]
    celery_app.config_from_object(flask_app.config, namespace="CELERY")
    return celery_app


# When launched as a standalone worker (`celery -A acb_large_print_web.tasks worker`),
# create_app() is never called, so ContextTask is never installed and any task that
# touches current_app crashes with "Working outside of application context".
# Bind a Flask app at worker startup so the ContextTask wrapper is in place before
# the prefork pool forks child consumers.
from celery.signals import celeryd_init  # noqa: E402


@celeryd_init.connect
def _bind_flask_app_to_worker(**_kwargs):  # pragma: no cover - exercised in container
    try:
        from acb_large_print_web.app import create_app
    except Exception:
        import logging
        logging.getLogger(__name__).exception("celeryd_init: failed to import create_app")
        return
    try:
        create_app()  # side effect: invokes make_celery() and installs ContextTask
    except Exception:
        import logging
        logging.getLogger(__name__).exception("celeryd_init: create_app() failed")
