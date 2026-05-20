from acb_large_print_web.customization_warning import (
    detect_fix_customizations,
    generate_customization_warning,
)


def test_detect_fix_customizations_ignores_default_fix_options():
    has_customizations, reasons = detect_fix_customizations(
        {
            "mode": "full",
            "bound": False,
            "list_indent_in": 0.0,
            "para_indent_in": 0.0,
            "first_line_indent_in": 0.0,
            "preserve_heading_alignment": False,
            "detect_headings": True,
            "heading_accuracy": "balanced",
            "suppress_link_text": False,
            "suppress_missing_alt_text": False,
            "suppress_faux_heading": False,
        }
    )

    assert has_customizations is False
    assert reasons == []


def test_detect_fix_customizations_flags_non_default_list_indent():
    has_customizations, reasons = detect_fix_customizations(
        {
            "mode": "full",
            "list_indent_in": 0.5,
        }
    )

    assert has_customizations is True
    assert reasons == ['Document formatting customizations: List indent changed to 0.5"']


def test_detect_fix_customizations_flags_heading_detection_disabled():
    has_customizations, reasons = detect_fix_customizations(
        {
            "mode": "full",
            "detect_headings": False,
        }
    )

    assert has_customizations is True
    assert reasons == ["Document formatting customizations: Heading detection disabled"]


def test_generate_customization_warning_uses_plain_paragraphs_without_hard_wraps():
    warning = generate_customization_warning(
        ['Document formatting customizations: List indent changed to 0.5"']
    )

    assert "<br" not in warning
    assert "specification). Your customizations may result" in warning
    assert "The ACB Large Print Guidelines define specific requirements for typography" in warning
    assert "• Document formatting customizations: List indent changed to 0.5\"" in warning
