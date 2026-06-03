from __future__ import annotations

import csv
import difflib
import io
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import current_app

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional at runtime
    fitz = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> Path:
    p = Path(current_app.instance_path)
    p.mkdir(parents=True, exist_ok=True)
    return p / "magic_features.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables() -> None:
    conn = _conn()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS pronunciation_dict ("
        " term TEXT PRIMARY KEY,"
        " replacement TEXT NOT NULL,"
        " notes TEXT,"
        " updated_at TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS rule_proposals ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " title TEXT NOT NULL,"
        " rationale TEXT NOT NULL,"
        " suggested_rule_id TEXT,"
        " severity TEXT NOT NULL,"
        " submitted_by TEXT,"
        " status TEXT NOT NULL DEFAULT 'pending',"
        " created_at TEXT NOT NULL"
        ")"
    )
    conn.commit()
    conn.close()


def list_pronunciations() -> list[dict[str, str]]:
    ensure_tables()
    conn = _conn()
    rows = conn.execute(
        "SELECT term, replacement, COALESCE(notes, '') AS notes, updated_at "
        "FROM pronunciation_dict ORDER BY term COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_pronunciation(term: str, replacement: str, notes: str = "") -> None:
    ensure_tables()
    term = term.strip()
    replacement = replacement.strip()
    if not term or not replacement:
        raise ValueError("term and replacement are required")
    conn = _conn()
    conn.execute(
        "INSERT INTO pronunciation_dict (term, replacement, notes, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(term) DO UPDATE SET replacement=excluded.replacement, notes=excluded.notes, updated_at=excluded.updated_at",
        (term, replacement, notes.strip(), _now_iso()),
    )
    conn.commit()
    conn.close()


def delete_pronunciation(term: str) -> None:
    ensure_tables()
    conn = _conn()
    conn.execute("DELETE FROM pronunciation_dict WHERE term = ?", (term.strip(),))
    conn.commit()
    conn.close()


def pronunciations_to_csv() -> str:
    rows = list_pronunciations()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["term", "replacement", "notes", "updated_at"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def import_pronunciations_csv(text: str) -> int:
    ensure_tables()
    reader = csv.DictReader(io.StringIO(text))
    count = 0
    for row in reader:
        term = (row.get("term") or "").strip()
        repl = (row.get("replacement") or "").strip()
        notes = (row.get("notes") or "").strip()
        if not term or not repl:
            continue
        upsert_pronunciation(term, repl, notes)
        count += 1
    return count


def apply_pronunciation_dictionary(text: str) -> str:
    rows = list_pronunciations()
    out = text
    # Replace longer terms first to avoid partial replacement collisions.
    rows.sort(key=lambda r: len(r["term"]), reverse=True)
    for row in rows:
        term = re.escape(row["term"])
        out = re.sub(rf"\b{term}\b", row["replacement"], out, flags=re.IGNORECASE)
    return out


@dataclass
class TableAdvisory:
    severity: str
    code: str
    message: str


def _markdown_table_findings(text: str) -> list[TableAdvisory]:
    findings: list[TableAdvisory] = []
    lines = text.splitlines()
    for i in range(len(lines) - 1):
        a = lines[i].strip()
        b = lines[i + 1].strip()
        if "|" in a and re.search(r"\|?\s*:?-{3,}:?\s*\|", b):
            # Simple markdown table detected
            cols = [c for c in a.split("|") if c.strip()]
            if len(cols) < 2:
                findings.append(
                    TableAdvisory(
                        severity="high",
                        code="TABLE-TOO-FEW-COLS",
                        message=f"Table near line {i + 1} appears to have fewer than 2 meaningful columns.",
                    )
                )
            if not any(c.strip() for c in cols):
                findings.append(
                    TableAdvisory(
                        severity="high",
                        code="TABLE-MISSING-HEADERS",
                        message=f"Table near line {i + 1} appears to have blank header cells.",
                    )
                )
    return findings


def _html_table_findings(text: str) -> list[TableAdvisory]:
    findings: list[TableAdvisory] = []
    try:
        from lxml import html
    except Exception:
        return findings

    try:
        root = html.fromstring(text)
    except Exception:
        return findings

    tables = root.xpath("//table")
    for idx, table in enumerate(tables, start=1):
        ths = table.xpath(".//th")
        tds = table.xpath(".//td")
        if tds and not ths:
            findings.append(
                TableAdvisory(
                    severity="high",
                    code="TABLE-NO-TH",
                    message=f"HTML table #{idx} has data cells but no header cells (<th>).",
                )
            )
        merged = table.xpath(".//*[@rowspan or @colspan]")
        if merged:
            findings.append(
                TableAdvisory(
                    severity="medium",
                    code="TABLE-MERGED-CELLS",
                    message=f"HTML table #{idx} uses merged cells ({len(merged)}). Screen reader navigation may be ambiguous.",
                )
            )
        nested = table.xpath(".//table")
        if len(nested) > 1:
            findings.append(
                TableAdvisory(
                    severity="high",
                    code="TABLE-NESTED",
                    message=f"HTML table #{idx} contains nested tables. Consider flattening structure.",
                )
            )
    return findings


def analyze_tables(text: str) -> dict[str, Any]:
    findings = _markdown_table_findings(text) + _html_table_findings(text)
    return {
        "status": "ok",
        "finding_count": len(findings),
        "findings": [f.__dict__ for f in findings],
    }


def detect_reading_order_pdf(path: Path, max_pages: int = 5) -> dict[str, Any]:
    if fitz is None:
        return {"status": "unavailable", "detail": "PyMuPDF is not installed."}

    doc = fitz.open(path)
    findings: list[dict[str, Any]] = []

    pages_scanned = min(max_pages, len(doc))
    for page_idx in range(pages_scanned):
        page = doc[page_idx]
        blocks = page.get_text("blocks")  # x0, y0, x1, y1, text, block_no, block_type
        text_blocks = [b for b in blocks if str(b[4]).strip()]
        if len(text_blocks) < 3:
            continue

        original_order = [(b[0], b[1]) for b in text_blocks]
        sorted_order = [(b[0], b[1]) for b in sorted(text_blocks, key=lambda b: (round(b[1] / 8), b[0]))]

        if original_order != sorted_order:
            findings.append(
                {
                    "severity": "medium",
                    "code": "READING-ORDER-SUSPECT",
                    "message": f"Page {page_idx + 1} block order differs from top-to-bottom/left-to-right order.",
                }
            )

        xs = sorted(b[0] for b in text_blocks)
        if xs and (max(xs) - min(xs)) > 180:
            findings.append(
                {
                    "severity": "low",
                    "code": "READING-ORDER-MULTI-COLUMN",
                    "message": f"Page {page_idx + 1} appears multi-column; verify reading sequence.",
                }
            )

    doc.close()
    return {
        "status": "ok",
        "pages_scanned": pages_scanned,
        "finding_count": len(findings),
        "findings": findings,
    }


def ocr_pdf(path: Path, max_pages: int = 3) -> dict[str, Any]:
    if fitz is None:
        return {"status": "unavailable", "detail": "PyMuPDF is not installed."}
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return {
            "status": "unavailable",
            "detail": "pytesseract and/or Pillow are not installed on this server.",
        }

    doc = fitz.open(path)
    texts: list[str] = []
    conf_values: list[float] = []

    pages_scanned = min(max_pages, len(doc))
    for page_idx in range(pages_scanned):
        page = doc[page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        txt = pytesseract.image_to_string(img)
        if txt.strip():
            texts.append(txt.strip())
        try:
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            for c in data.get("conf", []):
                try:
                    v = float(c)
                except Exception:
                    continue
                if v >= 0:
                    conf_values.append(v)
        except Exception:
            pass

    doc.close()
    combined = "\n\n".join(texts).strip()
    return {
        "status": "ok",
        "pages_scanned": pages_scanned,
        "char_count": len(combined),
        "avg_confidence": round(sum(conf_values) / len(conf_values), 2) if conf_values else None,
        "text": combined,
    }


def extract_text_for_compare(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".rst", ".csv", ".json", ".xml", ".html", ".htm"}:
        return path.read_text(encoding="utf-8", errors="replace")

    # Use existing MarkItDown extractor for binary docs.
    from .core_services import convert_to_markdown

    out_path = path.with_suffix(path.suffix + ".cmp.md")
    md_path, _ = convert_to_markdown(path, output_path=out_path)
    text = md_path.read_text(encoding="utf-8", errors="replace")
    try:
        md_path.unlink(missing_ok=True)
    except Exception:
        pass
    return text


def compare_documents(path_a: Path, path_b: Path) -> dict[str, Any]:
    text_a = extract_text_for_compare(path_a)
    text_b = extract_text_for_compare(path_b)

    ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    diff_lines = list(
        difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile=path_a.name,
            tofile=path_b.name,
            lineterm="",
            n=2,
        )
    )

    added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

    return {
        "status": "ok",
        "similarity": round(ratio * 100, 2),
        "added_lines": added,
        "removed_lines": removed,
        "diff_preview": "\n".join(diff_lines[:200]),
    }


def submit_rule_proposal(
    *,
    title: str,
    rationale: str,
    severity: str,
    suggested_rule_id: str = "",
    submitted_by: str = "",
) -> int:
    ensure_tables()
    title = title.strip()
    rationale = rationale.strip()
    severity = severity.strip().lower() or "medium"
    if severity not in {"critical", "high", "medium", "low"}:
        severity = "medium"
    if not title or not rationale:
        raise ValueError("title and rationale are required")

    conn = _conn()
    cur = conn.execute(
        "INSERT INTO rule_proposals (title, rationale, suggested_rule_id, severity, submitted_by, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (title, rationale, suggested_rule_id.strip(), severity, submitted_by.strip(), _now_iso()),
    )
    conn.commit()
    proposal_id = int(cur.lastrowid)
    conn.close()
    return proposal_id


def list_rule_proposals(limit: int = 100) -> list[dict[str, Any]]:
    ensure_tables()
    conn = _conn()
    rows = conn.execute(
        "SELECT id, title, rationale, suggested_rule_id, severity, submitted_by, status, created_at "
        "FROM rule_proposals ORDER BY id DESC LIMIT ?",
        (int(limit),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
