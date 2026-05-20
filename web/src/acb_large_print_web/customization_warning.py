"""Customization warning detection and generation.

When users deviate from ACB Large Print Board of Publications defaults,
this module detects those deviations and provides appropriate messaging.
"""

from acb_large_print import constants as C


def _getlist(form_data, key: str) -> list:
    """Return a list for *key* from a MultiDict or a plain dict."""
    if hasattr(form_data, "getlist"):
        return form_data.getlist(key)
    val = form_data.get(key)
    if val is None:
        return []
    return val if isinstance(val, list) else [val]


def _get_bool(form_data, key: str) -> bool:
    """Return a normalized boolean from form data or normalized options."""
    value = form_data.get(key)
    if isinstance(value, bool):
        return value
    return value == "on"


def _get_float(form_data, keys: tuple[str, ...], default: float) -> float:
    """Read a float from either normalized option keys or raw form keys."""
    for key in keys:
        value = form_data.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (ValueError, TypeError):
            continue
    return default


def detect_audit_customizations(form_data) -> tuple[bool, list[str]]:
    """
    Detect if audit form deviates from ACB defaults.

    Returns (has_customizations, customization_reasons).
    """
    reasons = []

    # Check audit mode (default: full)
    mode = form_data.get("mode", "full")
    if mode != "full":
        if mode == "quick":
            reasons.append(
                "Audit mode set to Quick (Critical/High findings only)"
            )
        elif mode == "custom":
            reasons.append("Custom rule selection enabled")

    # Check standards profile (default: acb_2025)
    standards_profile = form_data.get("standards_profile", "acb_2025")
    if standards_profile != "acb_2025":
        reasons.append(f"Standards profile changed to {standards_profile}")

    # Check categories (default: acb, msac)
    categories = _getlist(form_data, "category") or ["acb", "msac"]
    if set(categories) != {"acb", "msac"}:
        reasons.append(
            f"Audit categories changed to: {', '.join(sorted(categories))}"
        )

    # Check suppressed rules (new generic field + backward-compat legacy keys)
    suppressed_ids: list[str] = []
    if hasattr(form_data, "getlist"):
        suppressed_ids = form_data.getlist("suppress_rule")
    # Backward-compat: legacy boolean checkboxes
    if form_data.get("suppress_link_text") == "on":
        if "ACB-LINK-TEXT" not in suppressed_ids:
            suppressed_ids.append("ACB-LINK-TEXT")
    if form_data.get("suppress_missing_alt_text") == "on":
        if "ACB-MISSING-ALT-TEXT" not in suppressed_ids:
            suppressed_ids.append("ACB-MISSING-ALT-TEXT")
    if form_data.get("suppress_faux_heading") == "on":
        if "ACB-FAUX-HEADING" not in suppressed_ids:
            suppressed_ids.append("ACB-FAUX-HEADING")

    if suppressed_ids:
        reasons.append(
            f"Rule suppressions enabled for: {', '.join(sorted(suppressed_ids))}"
        )

    return len(reasons) > 0, reasons


def detect_fix_customizations(form_data) -> tuple[bool, list[str]]:
    """
    Detect if fix form deviates from ACB defaults.

    Returns (has_customizations, customization_reasons).
    """
    reasons = []

    # Check fix mode (default: full)
    mode = form_data.get("mode", "full")
    if mode != "full":
        if mode == "essentials":
            reasons.append("Fix mode set to Essentials (Critical/High only)")
        elif mode == "custom":
            reasons.append("Custom rule selection enabled")

    # Check standards profile (default: acb_2025)
    standards_profile = form_data.get("standards_profile", "acb_2025")
    if standards_profile != "acb_2025":
        reasons.append(f"Standards profile changed to {standards_profile}")

    # Check categories (default: acb, msac)
    categories = _getlist(form_data, "category") or ["acb", "msac"]
    if set(categories) != {"acb", "msac"}:
        reasons.append(
            f"Audit categories changed to: {', '.join(sorted(categories))}"
        )

    # Check typography customizations
    customizations = []

    try:
        bound = _get_bool(form_data, "bound")
        if bound:
            customizations.append("Bound document mode")
    except (ValueError, TypeError):
        pass

    try:
        list_indent = _get_float(
            form_data,
            ("list_indent_in", "list_indent"),
            C.LIST_INDENT_IN,
        )
        if list_indent != C.LIST_INDENT_IN:
            customizations.append(f"List indent changed to {list_indent}\"")
    except (ValueError, TypeError):
        pass

    try:
        para_indent = _get_float(
            form_data,
            ("para_indent_in", "para_indent"),
            C.PARA_INDENT_IN,
        )
        if para_indent != C.PARA_INDENT_IN:
            customizations.append(
                f"Paragraph indent changed to {para_indent}\""
            )
    except (ValueError, TypeError):
        pass

    try:
        first_line_indent = _get_float(
            form_data,
            ("first_line_indent_in", "first_line_indent"),
            C.FIRST_LINE_INDENT_IN,
        )
        if first_line_indent != C.FIRST_LINE_INDENT_IN:
            customizations.append(
                f"First-line indent changed to {first_line_indent}\""
            )
    except (ValueError, TypeError):
        pass

    if _get_bool(form_data, "preserve_heading_alignment"):
        customizations.append("Heading alignment preservation enabled")

    detect_headings = (
        _get_bool(form_data, "detect_headings")
        if "detect_headings" in form_data
        else True
    )
    if not detect_headings:
        customizations.append("Heading detection disabled")
    else:
        heading_accuracy = form_data.get("heading_accuracy", "balanced")
        if heading_accuracy != "balanced":
            customizations.append(
                f"Heading detection enabled ({heading_accuracy} accuracy)"
            )

    # Check suppressed rules via the rule_policy if available
    suppressed_ids: list[str] = []
    if "rule_policy" in form_data and form_data["rule_policy"] is not None:
        suppressed_ids = sorted(form_data["rule_policy"].suppressed)
    else:
        # Backward-compat: legacy boolean keys in opts dict
        if _get_bool(form_data, "suppress_link_text"):
            suppressed_ids.append("ACB-LINK-TEXT")
        if _get_bool(form_data, "suppress_missing_alt_text"):
            suppressed_ids.append("ACB-MISSING-ALT-TEXT")
        if _get_bool(form_data, "suppress_faux_heading"):
            suppressed_ids.append("ACB-FAUX-HEADING")

    if suppressed_ids:
        customizations.append(
            f"Rule suppressions for: {', '.join(suppressed_ids)}"
        )

    if customizations:
        reasons.append(
            "Document formatting customizations: " + "; ".join(customizations)
        )

    return len(reasons) > 0, reasons


def generate_customization_warning(customization_reasons: list[str]) -> str:
    """Generate a warning message from customization reasons."""
    if not customization_reasons:
        return ""

    items = "\n".join(f"• {reason}" for reason in customization_reasons)

    return "\n".join(
        [
            "For Your Information: Custom Settings Applied",
            "",
            (
                "This audit or fix was run with settings that differ from the "
                "American Council of the Blind Large Print Guidelines "
                "(Board of Publications specification). Your customizations "
                "may result in output that does not fully align with the "
                "standard ACB compliance "
                "criteria:"
            ),
            "",
            items,
            "",
            (
                "The ACB Large Print Guidelines define specific requirements "
                "for typography, spacing, emphasis styles, heading hierarchy, "
                "and other accessibility features optimized for individuals "
                "with low vision. When these defaults are modified, the "
                "resulting document may not conform to the ACB specification. "
                "This does not invalidate the fixes applied - only that the "
                "output may appear or behave differently from the standard "
                "ACB recommendation."
            ),
            "",
            (
                "For more information about how your custom settings affect "
                "ACB conformance, visit the Guidelines section of this site."
            ),
        ]
    )
