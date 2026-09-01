"""File upload validation and temporary directory management."""

from __future__ import annotations

import re
import shutil
import tempfile
import uuid
import os
from datetime import datetime
from pathlib import Path

from acb_large_print.converter import (
    CONVERTIBLE_EXTENSIONS as MARKITDOWN_CONVERTIBLE_EXTENSIONS,
    MARKITDOWN_AUDIO_EXTENSIONS,
)

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".md", ".pdf", ".epub"}

IMAGE_FILE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".tiff",
}

# Audio extensions accepted by the BITS Whisperer route (/whisperer)
# Includes Whisper API direct formats and formats that are normalized server-side.
AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".flac",
    ".aac",
    ".opus",
    ".webm",
    ".mp4",
    ".mpeg",
    ".mpga",
}

# Additional extensions accepted by the convert route (Pandoc + MarkItDown).
# MarkItDown audio is limited to short mp3/wav conversions; broader audio support
# remains on the dedicated /whisperer route.
CONVERT_EXTENSIONS = (ALLOWED_EXTENSIONS | {
    ".rst",
    ".odt",
    ".fodt",  # Flat OpenDocument Text
    ".rtf",  # Pandoc inputs
    ".ods",  # LibreOffice Calc
    ".fods",  # Flat ODF Spreadsheet
    ".odp",  # LibreOffice Impress
    ".fodp",  # Flat ODF Presentation
} | MARKITDOWN_CONVERTIBLE_EXTENSIONS)

# Uploads that the AI alt-text helper can inspect directly because the file is
# itself an image, embeds images, or can be rendered into visual pages.
ALT_TEXT_SOURCE_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".pdf", ".epub"} | IMAGE_FILE_EXTENSIONS

# Human-readable format labels for error messages
_FORMAT_LABELS = {
    ".docx": "Word document",
    ".xlsx": "Excel workbook",
    ".pptx": "PowerPoint presentation",
    ".md": "Markdown file",
    ".pdf": "PDF document",
    ".epub": "ePub e-book",
}
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

# Base temp directory for all uploads. In production this is set via
# GLOW_UPLOAD_TEMP_BASE so web + worker share the same writable path.
_UPLOAD_TEMP_BASE_OVERRIDE = (os.environ.get("GLOW_UPLOAD_TEMP_BASE") or "").strip()
UPLOAD_TEMP_BASE = Path(_UPLOAD_TEMP_BASE_OVERRIDE) if _UPLOAD_TEMP_BASE_OVERRIDE else Path(tempfile.gettempdir()) / "acb_lp_web"


class UploadError(Exception):
    """Raised when an uploaded file fails validation."""


def validate_upload(
    file: FileStorage,
    allowed_extensions: set[str] | None = None,
) -> tuple[str, Path]:
    """Validate and save an uploaded file to a temporary directory.

    Args:
        file: Flask FileStorage object from request.files.
        allowed_extensions: Set of allowed file extensions (with leading dot).
            Defaults to ALLOWED_EXTENSIONS if not specified.

    Returns:
        Tuple of (token, saved_file_path). The token is a UUID string
        used to identify the temp directory for later download/cleanup.

    Raises:
        UploadError: If the file is missing, has a disallowed extension,
                     or has no filename.
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS

    if file is None or file.filename == "":
        raise UploadError("No file selected. Please choose a document to upload.")

    filename = secure_filename(file.filename)
    if not filename:
        raise UploadError("Invalid filename.")

    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        allowed_list = ", ".join(sorted(allowed_extensions))
        raise UploadError(
            f"File type '{ext}' is not supported. " f"Accepted: {allowed_list}."
        )

    token = str(uuid.uuid4())
    temp_dir = UPLOAD_TEMP_BASE / token
    temp_dir.mkdir(parents=True, exist_ok=True)
    saved_path = temp_dir / filename

    file.save(str(saved_path))

    # Validate file content based on format
    with open(saved_path, "rb") as f:
        header = f.read(8)

    if ext in {".docx", ".xlsx", ".pptx", ".epub"}:
        # Office Open XML and ePub files are ZIP archives starting with PK
        if header[:2] != b"PK":
            fmt_label = _FORMAT_LABELS.get(ext, "Office document")
            cleanup_token(token)
            raise UploadError(
                f"The uploaded file does not appear to be a valid {fmt_label}. "
                "It may be corrupted or in a different format."
            )
    elif ext == ".pdf":
        if header[:5] != b"%PDF-":
            cleanup_token(token)
            raise UploadError(
                "The uploaded file does not appear to be a valid PDF. "
                "It may be corrupted or in a different format."
            )
    # .md files are plain text -- no magic byte check needed

    return token, saved_path


def get_temp_dir(token: str) -> Path | None:
    """Resolve a token to its temp directory path, validating the token format."""
    if not token or not _UUID_RE.match(token):
        return None
    temp_dir = UPLOAD_TEMP_BASE / token
    if not temp_dir.exists() or not temp_dir.is_dir():
        return None
    # Ensure resolved path is still under UPLOAD_TEMP_BASE (prevent traversal)
    try:
        temp_dir.resolve().relative_to(UPLOAD_TEMP_BASE.resolve())
    except ValueError:
        return None
    return temp_dir


def cleanup_token(token: str) -> None:
    """Remove the temporary directory for a given token."""
    temp_dir = get_temp_dir(token)
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)


def cleanup_tempdir(temp_dir: Path) -> None:
    """Remove a temporary directory and all its contents."""
    if temp_dir and temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


def get_upload_expiry(token: str, max_age_hours: int = 1) -> "datetime | None":
    """Return the datetime when the upload directory expires, or None if not found.

    Args:
        token: Upload token (UUID string).
        max_age_hours: Retention window in hours (must match the cleanup setting).

    Returns:
        A timezone-aware UTC datetime, or None if the token directory is missing.
    """
    from datetime import timezone, timedelta

    temp_dir = get_temp_dir(token)
    if temp_dir is None:
        return None
    try:
        mtime = temp_dir.stat().st_mtime
        created = datetime.fromtimestamp(mtime, tz=timezone.utc)
        return created + timedelta(hours=max_age_hours)
    except OSError:
        return None


def extend_upload_session(token: str) -> bool:
    """Touch the upload directory so its mtime resets to "now".

    Combined with the time-based cleanup logic this effectively extends the
    session for another ``max_age_hours`` window. Returns ``True`` on success.
    """
    import os as _os
    import time as _time

    temp_dir = get_temp_dir(token)
    if temp_dir is None:
        return False
    try:
        now = _time.time()
        _os.utime(temp_dir, (now, now))
        # Also touch contained files so per-file mtime checks (if any) align.
        for child in temp_dir.iterdir():
            try:
                _os.utime(child, (now, now))
            except OSError:
                continue
        return True
    except OSError:
        return False


def cleanup_stale_uploads(max_age_hours: int = 1) -> int:
    """Clean up old temporary upload directories.
    
    Args:
        max_age_hours: Maximum age in hours for temp directories before cleanup.
                      Default 1 hour.
    
    Returns:
        Number of directories cleaned up.
    """
    import time
    
    if not UPLOAD_TEMP_BASE.exists():
        return 0
    
    cleaned = 0
    cutoff = time.time() - (max_age_hours * 3600)
    
    # Long-lived subdirectories that live under UPLOAD_TEMP_BASE but have their
    # own, longer retention (e.g. report_cache shares, TTL up to 4h). The 1h
    # upload sweep must not delete them or outstanding share links 404 early.
    _PRESERVED_SUBDIRS = {"shares"}

    try:
        for item in UPLOAD_TEMP_BASE.iterdir():
            if item.is_dir():
                if item.name in _PRESERVED_SUBDIRS:
                    continue
                # Check modification time
                mtime = item.stat().st_mtime
                if mtime < cutoff:
                    cleanup_tempdir(item)
                    cleaned += 1
    except (OSError, PermissionError):
        pass  # Ignore errors during cleanup
    
    return cleaned
