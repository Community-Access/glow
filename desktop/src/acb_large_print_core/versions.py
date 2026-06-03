"""Component version manifest for support and diagnostics."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def _pkg_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def _module_version(module_name: str) -> str:
    try:
        module = __import__(module_name)
    except Exception:
        return "not-installed"
    return str(getattr(module, "__version__", "unknown"))


def get_component_versions() -> dict[str, str]:
    """Return a normalized component version map used by desktop/web surfaces."""
    try:
        from acb_large_print.version import get_version as _get_release_version

        release_version = _get_release_version()
    except Exception:
        release_version = _pkg_version("acb-large-print")

    return {
        "release_version": release_version,
        "desktop_package": _pkg_version("acb-large-print"),
        "web_package": _pkg_version("acb-large-print-web"),
        "markitdown": _pkg_version("markitdown"),
        "pymupdf": _module_version("fitz"),
        "python_docx": _pkg_version("python-docx"),
        "mammoth": _pkg_version("mammoth"),
        "requests": _pkg_version("requests"),
    }

