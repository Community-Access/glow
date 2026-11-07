"""Alt text for every image in a document, with the visitor's own AI key.

Three steps, and GLOW keeps nothing between them:

    list_images      the uploaded file's images (and charts), each with a key
                     saying where it is, its current alt text and its context.
                     The file is deleted as soon as they are read.
    describe         one image (or chart summary) to the visitor's AI, as the
                     alt-text-headings specialist; returns alt text, a long
                     description when one is needed, any text in the image,
                     and whether it looks decorative.
    write_alt_text   the visitor sends the file again with the alt text they
                     accepted; the alt text goes into each picture's
                     description (docPr/cNvPr descr) and the fixed file comes
                     straight back. Word and PowerPoint only: alt text in a PDF
                     needs a tagged structure most files do not have.
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from typing import Any

from . import aa_ask
from .visual_items import extract_visual_items

#: Files whose images can be listed.
IMAGE_SOURCE_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".pdf", ".epub"}
#: Files alt text can be written back into.
WRITABLE_EXTENSIONS = {".docx", ".pptx"}
MAX_IMAGES = 24
MAX_ALT_CHARS = 1000

_KEY_RE = re.compile(r"^(docx:\d{1,5}|pptx:\d{1,4}:\d{1,4})$")

DESCRIBE_FORMAT = (
    "\n\nAnswer in exactly this form, one field per line, plain text, nothing "
    "before or after:\n"
    "Alt text: <one line, at most 150 characters, what the image means here; "
    "do not start with 'image of'>\n"
    "Decorative: <yes or no>\n"
    "Long description: <only for a chart, diagram, map, infographic or "
    "screenshot: every number, label and relationship, in one paragraph; "
    "otherwise none>\n"
    "Text in image: <the exact words in the image, or none>"
)


def list_images(path: Path) -> list[dict[str, Any]]:
    """The images and charts in a document, ready for the page."""
    out: list[dict[str, Any]] = []
    for item in extract_visual_items(path, max_items=MAX_IMAGES):
        mime = item.get("mime_type") or ""
        data = item.get("image_bytes") or b""
        entry: dict[str, Any] = {
            "index": len(out),
            "key": item.get("key", ""),
            "label": item.get("label", ""),
            "location": item.get("location", ""),
            "current_alt": item.get("current_alt_text", ""),
            "context": [line for line in item.get("context_lines") or [] if line][:6],
            "image": "",
            "text_only": bool(item.get("text_only")),
            "describable": True,
        }
        if not entry["text_only"]:
            if mime in aa_ask.IMAGE_TYPES and 0 < len(data) <= aa_ask.MAX_IMAGE_BYTES:
                entry["image"] = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
            else:
                # EMF, WMF, TIFF and very large pictures: no provider takes them.
                entry["describable"] = False
        out.append(entry)
    return out


def _field(text: str, name: str) -> str:
    found = re.search(rf"^\s*\**{name}\**\s*:\s*(.*)$", text, re.IGNORECASE | re.MULTILINE)
    value = (found.group(1) if found else "").strip().strip("*").strip()
    return "" if value.lower() in {"none", "n/a", "no text", "-"} else value


def describe(provider_id: str, key: str, model: str, *, image: str = "",
             label: str = "", location: str = "", current_alt: str = "",
             context: list[str] | None = None) -> dict[str, Any]:
    """Draft alt text for one image or chart with the visitor's own AI."""
    lines = [f"Write alt text for {label or 'this image'}" + (f", at {location}" if location else "") + "."]
    if current_alt:
        lines.append(f"Its current alt text is: {current_alt[:300]}. Improve it if it falls short.")
    if context:
        lines.append("Where it appears:\n" + "\n".join(str(c)[:500] for c in context[:6]))
    if not image:
        lines.append("There is no picture to look at: this is a chart, so work from the "
                     "chart's details above.")
    result = aa_ask.ask(
        provider_id=provider_id, key=key, model=model,
        question="\n\n".join(lines) + DESCRIBE_FORMAT,
        image=image, specialist="alt-text-headings", use_tools=False,
        answer_format=DESCRIBE_FORMAT,
    )
    text = result["answer"]
    alt = _field(text, "Alt text") or text.strip().splitlines()[0][:150]
    return {
        "alt": alt[:MAX_ALT_CHARS],
        "decorative": _field(text, "Decorative").lower().startswith("y"),
        "long": _field(text, "Long description"),
        "text_in_image": _field(text, "Text in image"),
        "model": result["model"],
        "provider": result["provider"],
    }


def _clean_alts(alts: dict[str, Any]) -> dict[str, str]:
    clean: dict[str, str] = {}
    for k, v in (alts or {}).items():
        if _KEY_RE.match(str(k)) and isinstance(v, str):
            text = " ".join(v.split())[:MAX_ALT_CHARS]
            if text:
                clean[str(k)] = text
    return clean


def write_alt_text(path: Path, alts: dict[str, Any]) -> tuple[bytes, int]:
    """Put alt text into a Word or PowerPoint file. Returns (file bytes, count written)."""
    ext = path.suffix.lower()
    clean = _clean_alts(alts)
    if ext not in WRITABLE_EXTENSIONS:
        raise aa_ask.AskError("Alt text can be written into Word and PowerPoint files only.")
    if not clean:
        raise aa_ask.AskError("There is no alt text to write.")
    written = 0
    buf = io.BytesIO()
    if ext == ".docx":
        import docx
        from docx.oxml.ns import qn

        doc = docx.Document(str(path))
        # The same order visual_items reads them in: every w:drawing in document.xml.
        drawings = doc.element.findall(".//" + qn("w:drawing"))
        for idx, drawing in enumerate(drawings, start=1):
            text = clean.get(f"docx:{idx}")
            if not text:
                continue
            doc_pr = drawing.find(".//" + qn("wp:docPr"))
            if doc_pr is not None:
                doc_pr.set("descr", text)
                written += 1
        doc.save(buf)
    else:
        from pptx import Presentation

        prs = Presentation(str(path))
        for slide_index, slide in enumerate(prs.slides, start=1):
            for shape_counter, shape in enumerate(slide.shapes, start=1):
                text = clean.get(f"pptx:{slide_index}:{shape_counter}")
                if not text:
                    continue
                c_nv_pr = shape._element.xpath("./*[1]/p:cNvPr")
                if c_nv_pr:
                    c_nv_pr[0].set("descr", text)
                    written += 1
        prs.save(buf)
    return buf.getvalue(), written
