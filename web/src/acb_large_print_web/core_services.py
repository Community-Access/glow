"""Compatibility bridge for shared core audit/fix/convert services.

Prefers `quill_glow_core` when available, with per-symbol fallback to
`acb_large_print_core` during the shared-core transition.
"""

from __future__ import annotations

from typing import Any, Callable

_q_audit = None
_q_fix = None
_q_convert = None

try:
    from quill_glow_core import audit_by_extension as _q_audit  # type: ignore[assignment]
except ImportError:
    _q_audit = None

try:
    from quill_glow_core import fix_by_extension as _q_fix  # type: ignore[assignment]
except ImportError:
    _q_fix = None

try:
    from quill_glow_core import convert_to_markdown as _q_convert  # type: ignore[assignment]
except ImportError:
    _q_convert = None

_c_audit = None
_c_fix = None
_c_convert = None

try:
    from acb_large_print_core import audit_by_extension as _c_audit  # type: ignore[assignment]
except ImportError:
    _c_audit = None

try:
    from acb_large_print_core import fix_by_extension as _c_fix  # type: ignore[assignment]
except ImportError:
    _c_fix = None

try:
    from acb_large_print_core import convert_to_markdown as _c_convert  # type: ignore[assignment]
except ImportError:
    _c_convert = None


def _require(name: str, fn: Callable[..., Any] | None) -> Callable[..., Any]:
    if fn is None:
        raise RuntimeError(
            f"Shared core service '{name}' is unavailable. "
            "Install quill_glow_core or acb_large_print_core."
        )
    return fn


audit_by_extension = _require("audit_by_extension", _q_audit or _c_audit)
fix_by_extension = _require("fix_by_extension", _q_fix or _c_fix)
convert_to_markdown = _require("convert_to_markdown", _q_convert or _c_convert)

__all__ = [
    "audit_by_extension",
    "fix_by_extension",
    "convert_to_markdown",
]
