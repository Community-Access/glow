"""Deployment branding profiles for template rendering."""

from __future__ import annotations

import os


def get_branding_context() -> dict[str, str | bool]:
    """Return template-safe branding values based on deployment profile.

    Set `GLOW_BRAND_PROFILE=uarizona` for the University of Arizona deployment.
    Any other value uses the default Community Access presentation.
    """

    profile = os.environ.get("GLOW_BRAND_PROFILE", "communityaccess").strip().lower()
    is_uarizona = profile in {"uarizona", "ua", "uofa", "university-of-arizona"}

    if is_uarizona:
        return {
            "brand_profile": "uarizona",
            "brand_is_uarizona": True,
            "brand_title_suffix": "GLOW",
            "brand_nav_label": "GLOW Accessibility",
            "brand_heading_label": "GLOW",
            "brand_whisperer_label": "Audio Whisperer",
            "brand_guidelines_name": "large-print accessibility guidelines",
            "brand_guidelines_summary": "large-print, WCAG, and APH guidance",
            "brand_about_heading": "About Large Print and Accessibility Guidelines",
            "brand_about_intro": "GLOW applies large-print formatting and digital accessibility standards that support people with low vision and screen reader users.",
            "brand_footer_org_line": "A service provided by the University of Arizona Digital Accessibility team.",
            "brand_footer_story_line": "GLOW = Guided Layout & Output Workflow. Practical guidance for real-world accessibility work.",
            "brand_logo_file": "logo-uarizona.svg",
            "brand_logo_alt": "The University of Arizona",
            "brand_logo_height": "36",
            "brand_theme_class": "theme-uarizona",
            "brand_favicon": "favicon-uarizona.svg",
        }

    # Legacy aliases ("bits", "acb") intentionally resolve to the neutral
    # Community Access profile during the migration.
    return {
        "brand_profile": "communityaccess",
        "brand_is_uarizona": False,
        "brand_title_suffix": "GLOW (Guided Layout & Output Workflow)",
        "brand_nav_label": "GLOW Accessibility",
        "brand_heading_label": "GLOW",
        "brand_whisperer_label": "Audio Whisperer",
        "brand_guidelines_name": "Large Print Accessibility Guidelines",
        "brand_guidelines_summary": "large-print, WCAG, and APH guidance",
        "brand_about_heading": "About Large Print Accessibility Guidelines",
        "brand_about_intro": "GLOW applies large-print formatting and digital accessibility standards that support people with low vision and screen reader users.",
        "brand_footer_org_line": "A Community Access open source project.",
        "brand_footer_story_line": "GLOW = Guided Layout & Output Workflow. Practical guidance for real-world accessibility work.",
        "brand_logo_file": "logo-community-access.png",
        "brand_logo_alt": "Community Access",
        "brand_logo_height": "40",
        "brand_theme_class": "theme-communityaccess",
        "brand_favicon": "favicon.svg",
    }
