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

from celery import Celery, Task

# ---------------------------------------------------------------------------
# Celery singleton (configured lazily; bound to Flask app in create_app)
# ---------------------------------------------------------------------------

_broker = os.environ.get("CELERY_BROKER_URL", "")
_backend = os.environ.get("CELERY_RESULT_BACKEND", _broker or "")

# Use in-memory eager mode when no broker is configured.
_eager = not bool(_broker)

# Module-level Flask app reference. Populated by make_celery() (web side) or by
# the celeryd_init signal handler (worker side). ContextTask uses it to push an
# app context around every task invocation. Tasks decorated with
# @celery_app.task pick up ContextTask via the task_cls argument below, so the
# binding is honored regardless of import order.
_flask_app = None


class ContextTask(Task):
    """Base Task that runs every invocation inside a Flask application context.

    Tasks are registered at import time, before any signal handlers fire, so the
    base class must exist before the @celery_app.task decorators run. The Flask
    app itself is resolved lazily on first call (workers) or set eagerly by
    make_celery() (web process).
    """

    abstract = True

    def __call__(self, *args, **kwargs):
        global _flask_app
        if _flask_app is None:
            # Lazy bootstrap for standalone worker processes that never ran
            # create_app() during import.
            from acb_large_print_web.app import create_app
            _flask_app = create_app()
        with _flask_app.app_context():
            return self.run(*args, **kwargs)


celery_app = Celery(
    "glow",
    broker=_broker or "memory://localhost/",
    backend=_backend or "cache+memory://",
    include=["acb_large_print_web.tasks.convert_tasks"],
    task_cls=ContextTask,
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

    Called from ``create_app`` after the Flask app is fully configured. Sets
    the module-level Flask app reference so ContextTask can push an app
    context around each task invocation. Also copies any ``CELERY_*`` keys
    from Flask config into the Celery app config.
    """
    global _flask_app
    _flask_app = flask_app
    celery_app.config_from_object(flask_app.config, namespace="CELERY")
    return celery_app


# When launched as a standalone worker (`celery -A acb_large_print_web.tasks worker`),
# create_app() is never called from anywhere else, so trigger it via celeryd_init so
# Flask config/extensions are applied to the worker process. ContextTask still works
# without this (lazy bootstrap on first task call) but eager init produces clearer
# startup logs and surfaces config errors immediately.
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
        create_app()  # side effect: invokes make_celery() and sets _flask_app
    except Exception:
        import logging
        logging.getLogger(__name__).exception("celeryd_init: create_app() failed")
