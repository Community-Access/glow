"""ACB Large Print Tool -- audit, fix, and convert accessible documents."""

from __future__ import annotations

__app_name__ = "ACB Large Print Tool"
__author__ = "BITS (Blind Information Technology Solutions)"

try:
    from .version import get_version as _get_version

    __version__ = _get_version()
except Exception:
    __version__ = "unknown"
