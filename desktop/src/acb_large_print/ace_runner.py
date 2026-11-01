"""Run DAISY Ace (Accessibility Checker for EPUB) and parse results.

Wraps the ``@daisy/ace`` Node.js CLI to perform comprehensive EPUB
accessibility checking -- 100+ axe-core HTML rules plus EPUB-specific
metadata, navigation, and page-list checks.

Ace is a required dependency for ePub auditing.  The web application
Docker image ships with Node.js and ``@daisy/ace`` pre-installed.
For the desktop application, Node.js and Ace must be installed by the
user (``npm install -g @daisy/ace``).

Ace is an open source project by the DAISY Consortium, licensed MIT:
https://github.com/daisy/ace
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from .auditor import AuditResult, Finding
from . import constants as C

log = logging.getLogger("acb_large_print")

# Ace severity labels -> our Severity enum
_ACE_SEVERITY_MAP: dict[str, C.Severity] = {
    "critical": C.Severity.CRITICAL,
    "serious": C.Severity.HIGH,
    "moderate": C.Severity.MEDIUM,
    "minor": C.Severity.LOW,
}

# Ace rule IDs we map to our EPUB-* rules (for deduplication)
_ACE_TO_OUR_RULE: dict[str, str] = {
    "epub-title": "EPUB-TITLE",
    "epub-lang": "EPUB-LANGUAGE",
    "metadata-accessmode": "EPUB-ACCESSIBILITY-METADATA",
    "metadata-accessibilityfeature": "EPUB-ACCESSIBILITY-METADATA",
    "metadata-accessibilityhazard": "EPUB-ACCESSIBILITY-METADATA",
    "metadata-accessibilitysummary": "EPUB-ACCESSIBILITY-METADATA",
    "metadata-accessmodesufficient": "EPUB-ACCESSIBILITY-METADATA",
    "image-alt": "EPUB-MISSING-ALT-TEXT",
    "role-img-alt": "EPUB-MISSING-ALT-TEXT",
    "link-name": "EPUB-LINK-TEXT",
    "th-has-data-cells": "EPUB-TABLE-HEADERS",
    "td-has-header": "EPUB-TABLE-HEADERS",
}


def ace_available() -> bool:
    """Return True if the Ace CLI is installed and reachable."""
    return shutil.which("ace") is not None


def ace_version() -> str | None:
    """Return the Ace version string, or None if not installed."""
    exe = shutil.which("ace")
    if not exe:
        return None
    try:
        result = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = result.stdout.strip()
        return version if version else None
    except (subprocess.SubprocessError, IndexError):
        return None


def run_ace(file_path: str | Path, *, timeout: int = 120) -> dict | None:
    """Run Ace on an EPUB file and return the parsed JSON report.

    Args:
        file_path: Path to the .epub file.
        timeout: Maximum seconds to wait for Ace to complete.

    Returns:
        Parsed JSON report dict, or None if Ace is unavailable or fails.
    """
    exe = shutil.which("ace")
    if not exe:
        return None

    file_path = Path(file_path)
    if not file_path.exists():
        return None

    tmp_dir = Path(tempfile.mkdtemp(prefix="ace_report_"))
    try:
        cmd = [
            exe,
            "--json",
            "--outdir",
            str(tmp_dir),
            str(file_path),
        ]

        log.info("Running Ace: %s", " ".join(cmd))
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Ace writes report.json to the output directory
        report_file = tmp_dir / "report.json"
        if not report_file.exists():
            log.warning("Ace did not produce report.json (exit %d)", proc.returncode)
            return None

        with open(report_file, "r", encoding="utf-8") as f:
            return json.load(f)

    except subprocess.TimeoutExpired:
        log.warning("Ace timed out after %d seconds", timeout)
        return None
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        log.warning("Ace run failed: %s", exc)
        return None
    finally:
        # Clean up temp directory
        shutil.rmtree(tmp_dir, ignore_errors=True)


def ace_report_to_findings(report: dict) -> list[Finding]:
    """Convert an Ace JSON report into a list of Finding objects.

    Maps Ace's axe-core violations and EPUB-specific assertions to our
    finding model. Deduplicates where Ace rules overlap with our existing
    EPUB-* rule IDs.

    Args:
        report: Parsed Ace JSON report (from :func:`run_ace`).

    Returns:
        List of Finding objects ready to merge into an AuditResult.
    """
    findings: list[Finding] = []
    seen_rules: set[str] = set()

    # Process assertions (EPUB-level checks: metadata, title, lang, etc.)
    # Ace 1.4 writes "assertions" as a list, one entry per content document;
    # an older shape wrapped them in a dict. Read whichever is there, once.
    top = report.get("assertions", [])
    if isinstance(top, dict):
        for assertion in top.get("assertions", []):
            _process_ace_assertion(assertion, findings, seen_rules)
    elif isinstance(top, list):
        for doc in top:
            if isinstance(doc, dict):
                for assertion in doc.get("assertions", []):
                    _process_ace_assertion(assertion, findings, seen_rules)

    # Earl assertions at top level
    for earl in (
        report.get("earl:result", [])
        if isinstance(report.get("earl:result"), list)
        else []
    ):
        _process_earl_result(earl, findings, seen_rules)

    return findings


def _process_ace_assertion(
    assertion: dict, findings: list[Finding], seen: set[str]
) -> None:
    """Process a single Ace assertion into findings."""
    rule_id = assertion.get("@testSubject", {}).get("url", "") or assertion.get(
        "earl:test", {}
    ).get("dct:title", "")

    # axe-core violations come in a different structure
    if "axe:violations" in assertion or "violations" in assertion:
        violations = assertion.get("axe:violations") or assertion.get("violations", [])
        if isinstance(violations, list):
            for violation in violations:
                _process_axe_violation(violation, findings, seen)
        return

    # EPUB-level assertion
    ace_rule = assertion.get("earl:test", {}).get("dct:title", "")
    if not ace_rule:
        ace_rule = assertion.get("testCase", "")

    outcome = assertion.get("earl:result", {}).get("earl:outcome", "")
    if "fail" not in str(outcome).lower():
        return

    impact = assertion.get("earl:result", {}).get("dct:description", "")
    message = assertion.get("earl:result", {}).get("dct:description", ace_rule)

    our_rule = _ACE_TO_OUR_RULE.get(ace_rule)

    if our_rule:
        if our_rule in seen:
            return
        seen.add(our_rule)
        if our_rule in C.AUDIT_RULES:
            rule_def = C.AUDIT_RULES[our_rule]
            findings.append(
                Finding(
                    rule_id=our_rule,
                    severity=rule_def.severity,
                    message=f"[Ace] {message}" if message else rule_def.description,
                    location="EPUB package",
                    auto_fixable=rule_def.auto_fixable,
                )
            )
    else:
        # Ace-specific finding not in our rules -- add as informational
        key = f"ACE:{ace_rule}"
        if key in seen:
            return
        seen.add(key)
        severity = _ACE_SEVERITY_MAP.get(
            impact.lower() if isinstance(impact, str) else "moderate",
            C.Severity.MEDIUM,
        )
        findings.append(
            Finding(
                rule_id="ACE-EPUB-CHECK",
                severity=severity,
                message=f"[Ace: {ace_rule}] {message}",
                location="EPUB package",
                auto_fixable=False,
            )
        )


def _process_axe_violation(
    violation: dict, findings: list[Finding], seen: set[str]
) -> None:
    """Process a single axe-core violation."""
    axe_id = violation.get("id", "")
    impact = violation.get("impact", "moderate")
    description = violation.get("description", "")
    help_text = violation.get("help", description)

    # Count affected nodes
    nodes = violation.get("nodes", [])
    node_count = len(nodes)

    our_rule = _ACE_TO_OUR_RULE.get(axe_id)

    if our_rule:
        if our_rule in seen:
            return
        seen.add(our_rule)
        if our_rule in C.AUDIT_RULES:
            rule_def = C.AUDIT_RULES[our_rule]
            msg = f"[Ace/axe] {help_text}"
            if node_count > 1:
                msg += f" ({node_count} instances)"
            findings.append(
                Finding(
                    rule_id=our_rule,
                    severity=rule_def.severity,
                    message=msg,
                    location=_node_location(nodes),
                    auto_fixable=rule_def.auto_fixable,
                )
            )
    else:
        key = f"AXE:{axe_id}"
        if key in seen:
            return
        seen.add(key)
        severity = _ACE_SEVERITY_MAP.get(impact, C.Severity.MEDIUM)
        msg = f"[Ace/axe: {axe_id}] {help_text}"
        if node_count > 1:
            msg += f" ({node_count} instances)"
        findings.append(
            Finding(
                rule_id="ACE-AXE-CHECK",
                severity=severity,
                message=msg,
                location=_node_location(nodes),
                auto_fixable=False,
            )
        )


def _process_earl_result(earl: dict, findings: list[Finding], seen: set[str]) -> None:
    """Process a top-level EARL result."""
    outcome = earl.get("earl:outcome", "")
    if "fail" not in str(outcome).lower():
        return
    title = earl.get("earl:test", {}).get("dct:title", "unknown")
    desc = earl.get("dct:description", title)
    key = f"EARL:{title}"
    if key in seen:
        return
    seen.add(key)
    our_rule = _ACE_TO_OUR_RULE.get(title)
    if our_rule and our_rule in C.AUDIT_RULES:
        rule_def = C.AUDIT_RULES[our_rule]
        findings.append(
            Finding(
                rule_id=our_rule,
                severity=rule_def.severity,
                message=f"[Ace] {desc}",
                location="EPUB package",
                auto_fixable=rule_def.auto_fixable,
            )
        )


def _node_location(nodes: list[dict]) -> str:
    """Extract a readable location from axe node list."""
    if not nodes:
        return ""
    first = nodes[0]
    target = first.get("target", [])
    if target and isinstance(target, list):
        return str(target[0]) if target else ""
    html_snippet = first.get("html", "")
    if html_snippet:
        return html_snippet[:120]
    return ""


def _extract_ace_conformance(report: dict) -> str | None:
    """Extract the EPUB accessibility conformance level from an Ace report.

    Ace embeds the conformance declaration (e.g. EPUB Accessibility 1.0 AA) in
    ``earl:result.earl:outcome`` or ``metadata.conformance``.  Returns a short
    human-readable string, or None when not found.
    """
    # Prefer metadata.conformance (Ace >= 1.3)
    meta = report.get("metadata") or {}
    conformance = meta.get("conformance") or meta.get("conformsTo") or ""
    if conformance:
        return str(conformance)[:200]

    # Fall back to top-level earl:result
    earl_result = report.get("earl:result")
    if isinstance(earl_result, dict):
        outcome = earl_result.get("earl:outcome", "")
        if outcome:
            return str(outcome)[:200]
    if isinstance(earl_result, list) and earl_result:
        outcome = earl_result[0].get("earl:outcome", "") if isinstance(earl_result[0], dict) else ""
        if outcome:
            return str(outcome)[:200]

    return None


def audit_epub_with_ace(file_path: str | Path) -> AuditResult | None:
    """Run a full Ace audit on an EPUB file.

    Returns an AuditResult populated with Ace findings, or None if
    Ace is not available.  The result object also gains an
    ``ace_conformance`` attribute (str or None) holding the declared
    conformance level from the Ace report.
    """
    file_path = Path(file_path)
    report = run_ace(file_path)
    if report is None:
        return None

    result = AuditResult(file_path=str(file_path))
    ace_findings = ace_report_to_findings(report)
    result.findings.extend(ace_findings)
    # Attach conformance level as a dynamic attribute
    result.ace_conformance = _extract_ace_conformance(report)  # type: ignore[attr-defined]
    return result
