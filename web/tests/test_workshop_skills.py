"""Unit tests for workshop_skills module.

Tests the skill, README, and prompt generation functions that compile a
participant's Champion Studio workflow into a portable agent skill.
"""

from __future__ import annotations

import io
import zipfile
from textwrap import dedent

import pytest

from acb_large_print_web.workshop_skills import (
    CHAMPION_FIELDS,
    build_copy_prompt,
    build_readme,
    build_skill_markdown,
    build_skill_zip_bytes,
    slugify,
)


class TestSlugify:
    """Test filename- and identifier-safe slug generation."""

    def test_slugify_basic_name(self):
        """Convert a simple workflow name to a slug."""
        assert slugify("Faculty Email Accessibility Coach") == "faculty-email-accessibility-coach"

    def test_slugify_strips_punctuation(self):
        """Remove all non-alphanumeric characters except hyphens."""
        assert slugify('A "quoted": name, with punctuation!') == "a-quoted-name-with-punctuation"

    def test_slugify_collapses_whitespace(self):
        """Multiple spaces become single hyphens."""
        assert slugify("Multi    space    name") == "multi-space-name"

    def test_slugify_collapses_special_chars(self):
        """Multiple special characters collapse to single hyphen."""
        assert slugify("Name---with***many===special") == "name-with-many-special"

    def test_slugify_handles_leading_trailing_whitespace(self):
        """Trim leading and trailing whitespace."""
        assert slugify("  Spaced Name  ") == "spaced-name"

    def test_slugify_handles_leading_trailing_hyphens(self):
        """Strip leading and trailing hyphens."""
        assert slugify("---leading-and-trailing---") == "leading-and-trailing"

    def test_slugify_enforces_length_limit(self):
        """Truncate to max length (60 characters)."""
        long_name = "This is a very long workflow name that exceeds the maximum slug length limit"
        slug = slugify(long_name)
        assert len(slug) <= 60
        assert slug.startswith("this-is-a-very-long-workflow-name")
        assert not slug.endswith("-")

    def test_slugify_handles_empty_string(self):
        """Use fallback for empty input."""
        assert slugify("") == "accessibility-workflow"
        assert slugify("   ") == "accessibility-workflow"

    def test_slugify_custom_fallback(self):
        """Accept custom fallback value."""
        assert slugify("", fallback="custom-default") == "custom-default"
        assert slugify("   ", fallback="another-fallback") == "another-fallback"

    def test_slugify_lowercase_conversion(self):
        """Convert to lowercase."""
        assert slugify("UPPERCASE NAME") == "uppercase-name"
        assert slugify("MiXeD CaSe") == "mixed-case"

    def test_slugify_unicode_handling(self):
        """Handle unicode by removing accents (via character stripping)."""
        # Non-ASCII characters should be stripped by the regex
        result = slugify("Café Résumé")
        assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in result)


class TestBuildSkillMarkdown:
    """Test SKILL.md frontmatter and body generation."""

    @pytest.fixture
    def basic_values(self):
        """Standard Champion Studio answers."""
        return {
            "workflow_name": "Faculty Email Accessibility Coach",
            "partner_group": "Faculty who send course announcements to large classes",
            "responsibility": "Write meaningful link text\nUse headings instead of bold text",
            "ai_support": "Find unclear links and missing structure\nSuggest a clearer rewrite",
            "final_output": "A revised email and a checklist for next time",
            "human_safeguard": "A person checks the accommodation contact details are current",
        }

    def test_skill_markdown_structure(self, basic_values):
        """Generated SKILL.md has required frontmatter and sections."""
        skill = build_skill_markdown(basic_values)

        # Must start and end with frontmatter markers
        assert skill.startswith("---\n")
        parts = skill.split("---\n")
        assert len(parts) == 3
        assert parts[0] == ""
        assert parts[2].strip()  # Body is not empty

    def test_skill_markdown_frontmatter_keys(self, basic_values):
        """Frontmatter contains required YAML keys."""
        skill = build_skill_markdown(basic_values)
        _, frontmatter, _ = skill.split("---\n", 2)

        assert "name:" in frontmatter
        assert "description:" in frontmatter
        assert "metadata:" in frontmatter
        assert "author:" in frontmatter
        assert "source:" in frontmatter
        assert 'version: "1.0.0"' in frontmatter

    def test_skill_markdown_name_is_slugified(self, basic_values):
        """The name field in frontmatter is slugified."""
        skill = build_skill_markdown(basic_values)
        _, frontmatter, _ = skill.split("---\n", 2)

        assert "name: faculty-email-accessibility-coach" in frontmatter

    def test_skill_markdown_description_from_partner_group(self, basic_values):
        """Description includes partner group if provided."""
        skill = build_skill_markdown(basic_values)

        assert "Faculty who send course announcements to large classes" in skill

    def test_skill_markdown_description_generated_if_empty(self, basic_values):
        """Description is auto-generated if partner_group is empty."""
        basic_values["partner_group"] = ""
        skill = build_skill_markdown(basic_values)

        assert "Supports accessibility work for Faculty Email Accessibility Coach" in skill

    def test_skill_markdown_body_includes_title(self, basic_values):
        """Body starts with workflow name as heading."""
        skill = build_skill_markdown(basic_values)
        _, _, body = skill.split("---\n", 2)

        assert "# Faculty Email Accessibility Coach" in body

    def test_skill_markdown_who_this_helps_section(self, basic_values):
        """Includes 'Who this helps' section with partner group."""
        skill = build_skill_markdown(basic_values)

        assert "## Who this helps" in skill
        assert "Faculty who send course announcements to large classes" in skill

    def test_skill_markdown_omits_who_section_if_empty(self, basic_values):
        """Omits section if partner_group is empty."""
        basic_values["partner_group"] = ""
        skill = build_skill_markdown(basic_values)

        assert "## Who this helps" not in skill

    def test_skill_markdown_what_teaches_section(self, basic_values):
        """Includes 'What this teaches' section with responsibilities."""
        skill = build_skill_markdown(basic_values)

        assert "## What this teaches" in skill
        assert "- Write meaningful link text" in skill
        assert "- Use headings instead of bold text" in skill

    def test_skill_markdown_workflow_section(self, basic_values):
        """Includes 'Workflow' section with AI support steps."""
        skill = build_skill_markdown(basic_values)

        assert "## Workflow" in skill
        assert "1. Find unclear links and missing structure" in skill
        assert "2. Suggest a clearer rewrite" in skill

    def test_skill_markdown_trusted_guidance_section(self, basic_values):
        """Includes 'Trusted guidance' section if provided."""
        skill = build_skill_markdown(
            basic_values,
            trusted_guidance="WCAG 2.2 AA\nUniversity accessibility policy"
        )

        assert "## Trusted guidance" in skill
        assert "- WCAG 2.2 AA" in skill
        assert "- University accessibility policy" in skill

    def test_skill_markdown_omits_guidance_if_empty(self, basic_values):
        """Omits guidance section if not provided."""
        skill = build_skill_markdown(basic_values, trusted_guidance="")

        assert "## Trusted guidance" not in skill

    def test_skill_markdown_output_section(self, basic_values):
        """Includes 'Output' section with final output description."""
        skill = build_skill_markdown(basic_values)

        assert "## Output" in skill
        assert "A revised email and a checklist for next time" in skill

    def test_skill_markdown_omits_output_if_empty(self, basic_values):
        """Omits output section if final_output is empty."""
        basic_values["final_output"] = ""
        skill = build_skill_markdown(basic_values)

        assert "## Output" not in skill

    def test_skill_markdown_verification_truth_section(self, basic_values):
        """Includes 'Verification truth' with human-review checklist."""
        skill = build_skill_markdown(basic_values)

        assert "## Verification truth" in skill
        assert "A human must verify the following before this work is considered done:" in skill
        assert "- A person checks the accommodation contact details are current" in skill

    def test_skill_markdown_verification_default_message(self, basic_values):
        """Verification section includes safety guidance."""
        skill = build_skill_markdown(basic_values)

        assert "Never describe content as accessible on the basis of an automated result alone." in skill
        assert "If any of the above has not happened, say so in the response" in skill

    def test_skill_markdown_do_not_activate_section(self, basic_values):
        """Includes 'Do not activate for' boundaries section."""
        skill = build_skill_markdown(basic_values)

        assert "## Do not activate for" in skill
        assert "Requests outside this workflow's purpose" in skill

    def test_skill_markdown_custom_author(self, basic_values):
        """Author can be customized."""
        skill = build_skill_markdown(basic_values, author="Alice Smith")

        assert "author: Alice Smith" in skill

    def test_skill_markdown_event_name_in_source(self, basic_values):
        """Event name appears in source metadata."""
        skill = build_skill_markdown(basic_values, event_name="CSUN 2026")

        assert "source: GLOW workshop at CSUN 2026" in skill

    def test_skill_markdown_event_name_defaults(self, basic_values):
        """Source defaults to 'GLOW workshop' if no event."""
        skill = build_skill_markdown(basic_values, event_name="")

        assert "source: GLOW workshop" in skill

    def test_skill_markdown_multiline_handling(self, basic_values):
        """Multiline answers split into numbered or bulleted lists."""
        skill = build_skill_markdown(basic_values)

        # Workflow should be numbered
        assert "1. Find unclear links and missing structure" in skill
        assert "2. Suggest a clearer rewrite" in skill

        # Responsibility should be bulleted
        assert "- Write meaningful link text" in skill

    def test_skill_markdown_ends_with_newline(self, basic_values):
        """Generated markdown ends with a single newline."""
        skill = build_skill_markdown(basic_values)

        assert skill.endswith("\n")
        assert not skill.endswith("\n\n")

    def test_skill_markdown_frontmatter_is_yaml_safe(self, basic_values):
        """Frontmatter uses block scalars to avoid YAML parsing issues."""
        basic_values["partner_group"] = 'Faculty with "quotes" and: colons'
        skill = build_skill_markdown(basic_values)

        # Should use block scalar syntax
        assert "|-\n" in skill or '|-' in skill


class TestBuildReadme:
    """Test README.md generation for colleagues."""

    @pytest.fixture
    def basic_values(self):
        return {
            "workflow_name": "Email Accessibility Coach",
            "partner_group": "Faculty who write course emails",
            "responsibility": "Use headings\nWrite clear links",
            "ai_support": "Review for clarity",
            "final_output": "Revised email",
            "human_safeguard": "Check contact details",
        }

    def test_readme_structure(self, basic_values):
        """README has expected sections."""
        readme = build_readme(basic_values)

        assert "# Email Accessibility Coach" in readme
        assert "## What this is" in readme
        assert "## How to use it" in readme
        assert "## What must stay true" in readme

    def test_readme_describes_skill_concept(self, basic_values):
        """README explains what an agent skill is."""
        readme = build_readme(basic_values)

        assert "agent skill" in readme.lower()
        assert "no code" in readme.lower() or "no code" in readme
        assert "plain-language" in readme or "plain language" in readme

    def test_readme_includes_partner_group(self, basic_values):
        """README mentions who it helps."""
        readme = build_readme(basic_values)

        assert "Faculty who write course emails" in readme
        assert "## Who it is for" in readme

    def test_readme_omits_who_section_if_empty(self, basic_values):
        """Omits 'Who it is for' if partner_group is empty."""
        basic_values["partner_group"] = ""
        readme = build_readme(basic_values)

        assert "## Who it is for" not in readme

    def test_readme_usage_instructions(self, basic_values):
        """README includes instructions for different use cases."""
        readme = build_readme(basic_values)

        assert "use an AI assistant in a browser" in readme
        assert "Agent Plugins" in readme
        assert "do not use AI at all" in readme

    def test_readme_human_review_is_required(self, basic_values):
        """README emphasizes human review requirement."""
        readme = build_readme(basic_values)

        assert "human review" in readme.lower()
        assert "Check contact details" in readme
        assert "Verification truth" in readme

    def test_readme_automated_pass_not_proof(self, basic_values):
        """README warns against automated results as proof."""
        readme = build_readme(basic_values)

        assert "automated pass is evidence, not proof" in readme.lower()
        assert "screen reader" in readme
        assert "keyboard" in readme

    def test_readme_custom_author(self, basic_values):
        """Author can be customized."""
        readme = build_readme(basic_values, author="Bob Jones")

        assert "Bob Jones" in readme

    def test_readme_event_name(self, basic_values):
        """Event name can be included."""
        readme = build_readme(basic_values, event_name="CSUN 2026")

        assert "CSUN 2026" in readme

    def test_readme_ends_with_newline(self, basic_values):
        """Generated markdown ends with a single newline."""
        readme = build_readme(basic_values)

        assert readme.endswith("\n")
        assert not readme.endswith("\n\n")


class TestBuildCopyPrompt:
    """Test Tier 2 prompt for pasting into any assistant."""

    @pytest.fixture
    def basic_values(self):
        return {
            "workflow_name": "Email Coach",
            "partner_group": "Faculty",
            "responsibility": "Use headings\nWrite clear links",
            "ai_support": "Review structure\nSuggest rewrites",
            "final_output": "Revised email",
            "human_safeguard": "Check contact details",
        }

    def test_copy_prompt_has_no_frontmatter(self, basic_values):
        """No YAML frontmatter or file markers."""
        prompt = build_copy_prompt(basic_values)

        assert "---" not in prompt
        assert "SKILL.md" not in prompt
        assert ".md" not in prompt

    def test_copy_prompt_has_no_install_language(self, basic_values):
        """Does not mention installation or configuration."""
        prompt = build_copy_prompt(basic_values)

        assert "install" not in prompt.lower()
        assert "terminal" not in prompt.lower()
        assert "import" not in prompt.lower()

    def test_copy_prompt_opens_with_role_context(self, basic_values):
        """Starts by establishing the assistant's role."""
        prompt = build_copy_prompt(basic_values)

        assert "You are an accessibility assistant" in prompt
        assert "Email Coach" in prompt

    def test_copy_prompt_includes_partner_group(self, basic_values):
        """Mentions who is being helped."""
        prompt = build_copy_prompt(basic_values)

        assert "Faculty" in prompt

    def test_copy_prompt_task_section(self, basic_values):
        """Includes 'Your task:' with workflow steps."""
        prompt = build_copy_prompt(basic_values)

        assert "Your task:" in prompt
        assert "- Review structure" in prompt
        assert "- Suggest rewrites" in prompt

    def test_copy_prompt_no_guidance_section_if_empty(self, basic_values):
        """Omits guidance section if not provided."""
        prompt = build_copy_prompt(basic_values, trusted_guidance="")

        assert "Follow this guidance" not in prompt

    def test_copy_prompt_with_guidance(self, basic_values):
        """Includes guidance if provided."""
        prompt = build_copy_prompt(
            basic_values,
            trusted_guidance="WCAG 2.2 AA\nUniversity policy"
        )

        assert "Follow this guidance" in prompt
        assert "WCAG 2.2 AA" in prompt

    def test_copy_prompt_teach_as_you_go(self, basic_values):
        """Includes instruction to teach responsibility items."""
        prompt = build_copy_prompt(basic_values)

        assert "Teach as you go" in prompt
        assert "- Use headings" in prompt
        assert "- Write clear links" in prompt

    def test_copy_prompt_output_section(self, basic_values):
        """Specifies desired output format."""
        prompt = build_copy_prompt(basic_values)

        assert "Give me back:" in prompt
        assert "Revised email" in prompt

    def test_copy_prompt_verification_instructions(self, basic_values):
        """Includes verification truth section."""
        prompt = build_copy_prompt(basic_values)

        assert "Before you finish, do these things:" in prompt
        assert "Say exactly what you checked" in prompt
        assert "Do not call anything accessible based only on an automated result" in prompt

    def test_copy_prompt_human_safeguard_items(self, basic_values):
        """Lists human-review items from safeguard field."""
        prompt = build_copy_prompt(basic_values)

        assert "Check contact details" in prompt

    def test_copy_prompt_honesty_about_uncertainty(self, basic_values):
        """Includes instruction to state uncertainty."""
        prompt = build_copy_prompt(basic_values)

        assert "unsure" in prompt.lower()
        assert "say so plainly" in prompt

    def test_copy_prompt_ends_with_newline(self, basic_values):
        """Generated prompt ends with a single newline."""
        prompt = build_copy_prompt(basic_values)

        assert prompt.endswith("\n")
        assert not prompt.endswith("\n\n")

    def test_copy_prompt_is_pasteable(self, basic_values):
        """Can be pasted directly into a chat without issues."""
        prompt = build_copy_prompt(basic_values)

        # Should have no internal inconsistencies or dangling markers
        assert prompt.count("---") == 0
        # Should not have unmatched quotes or brackets
        assert prompt.count('"""') == 0


class TestBuildSkillZipBytes:
    """Test complete downloadable package generation."""

    @pytest.fixture
    def basic_values(self):
        return {
            "workflow_name": "Email Coach",
            "partner_group": "Faculty",
            "responsibility": "Use headings",
            "ai_support": "Review structure",
            "final_output": "Revised email",
            "human_safeguard": "Check contact details",
        }

    def test_zip_returns_filename_and_bytes(self, basic_values):
        """Returns tuple of (filename, bytes)."""
        result = build_skill_zip_bytes(basic_values)

        assert isinstance(result, tuple)
        assert len(result) == 2
        filename, content = result
        assert isinstance(filename, str)
        assert isinstance(content, bytes)

    def test_zip_filename_is_slugified(self, basic_values):
        """Filename matches slugified workflow name."""
        filename, _ = build_skill_zip_bytes(basic_values)

        assert filename == "email-coach.zip"

    def test_zip_contains_expected_files(self, basic_values):
        """Package includes SKILL.md, README.md, and copy-ready prompt."""
        _, content = build_skill_zip_bytes(basic_values)

        archive = zipfile.ZipFile(io.BytesIO(content))
        names = archive.namelist()

        assert "email-coach/SKILL.md" in names
        assert "email-coach/README.md" in names
        assert "email-coach/copy-into-any-assistant.txt" in names

    def test_zip_skill_md_content(self, basic_values):
        """SKILL.md inside zip is valid."""
        _, content = build_skill_zip_bytes(basic_values)

        archive = zipfile.ZipFile(io.BytesIO(content))
        skill = archive.read("email-coach/SKILL.md").decode("utf-8")

        assert skill.startswith("---\n")
        assert "name: email-coach" in skill
        assert "## Verification truth" in skill

    def test_zip_readme_content(self, basic_values):
        """README.md inside zip is valid."""
        _, content = build_skill_zip_bytes(basic_values)

        archive = zipfile.ZipFile(io.BytesIO(content))
        readme = archive.read("email-coach/README.md").decode("utf-8")

        assert "# Email Coach" in readme
        assert "## How to use it" in readme

    def test_zip_copy_prompt_content(self, basic_values):
        """copy-into-any-assistant.txt inside zip is valid."""
        _, content = build_skill_zip_bytes(basic_values)

        archive = zipfile.ZipFile(io.BytesIO(content))
        prompt = archive.read("email-coach/copy-into-any-assistant.txt").decode("utf-8")

        assert "You are an accessibility assistant" in prompt
        assert "---" not in prompt

    def test_zip_is_valid_archive(self, basic_values):
        """Generated bytes are a valid, readable zip file."""
        _, content = build_skill_zip_bytes(basic_values)

        # Should not raise
        archive = zipfile.ZipFile(io.BytesIO(content))
        assert len(archive.namelist()) == 3

    def test_zip_with_custom_author(self, basic_values):
        """Author parameter flows through to generated files."""
        _, content = build_skill_zip_bytes(basic_values, author="Dr. Smith")

        archive = zipfile.ZipFile(io.BytesIO(content))
        skill = archive.read("email-coach/SKILL.md").decode("utf-8")
        readme = archive.read("email-coach/README.md").decode("utf-8")

        assert "Dr. Smith" in skill
        assert "Dr. Smith" in readme

    def test_zip_with_event_name(self, basic_values):
        """Event name parameter flows through to generated files."""
        _, content = build_skill_zip_bytes(basic_values, event_name="CSUN 2026")

        archive = zipfile.ZipFile(io.BytesIO(content))
        skill = archive.read("email-coach/SKILL.md").decode("utf-8")
        readme = archive.read("email-coach/README.md").decode("utf-8")

        assert "CSUN 2026" in skill
        assert "CSUN 2026" in readme

    def test_zip_with_trusted_guidance(self, basic_values):
        """Trusted guidance is included in SKILL.md."""
        _, content = build_skill_zip_bytes(
            basic_values,
            trusted_guidance="WCAG 2.2 AA"
        )

        archive = zipfile.ZipFile(io.BytesIO(content))
        skill = archive.read("email-coach/SKILL.md").decode("utf-8")

        assert "## Trusted guidance" in skill
        assert "WCAG 2.2 AA" in skill


class TestChampionFieldsConstant:
    """Test the CHAMPION_FIELDS constant."""

    def test_champion_fields_is_tuple(self):
        """CHAMPION_FIELDS is a tuple."""
        assert isinstance(CHAMPION_FIELDS, tuple)

    def test_champion_fields_contains_expected_keys(self):
        """CHAMPION_FIELDS lists all six formula fields."""
        expected = {
            "workflow_name",
            "partner_group",
            "responsibility",
            "ai_support",
            "final_output",
            "human_safeguard",
        }
        assert set(CHAMPION_FIELDS) == expected

    def test_champion_fields_count(self):
        """CHAMPION_FIELDS has exactly six items."""
        assert len(CHAMPION_FIELDS) == 6


class TestEdgeCases:
    """Test boundary conditions and unusual inputs."""

    def test_empty_workflow_name(self):
        """Workflow name defaults if empty."""
        values = {
            "workflow_name": "",
            "partner_group": "Someone",
            "responsibility": "Learn",
            "ai_support": "Help",
            "final_output": "Output",
            "human_safeguard": "Review",
        }
        skill = build_skill_markdown(values)

        assert "# Accessibility workflow" in skill

    def test_all_empty_values(self):
        """All empty fields still generate valid output."""
        values = {
            "workflow_name": "",
            "partner_group": "",
            "responsibility": "",
            "ai_support": "",
            "final_output": "",
            "human_safeguard": "",
        }
        skill = build_skill_markdown(values)

        # Should be valid but with placeholder text
        assert "---\n" in skill
        assert "# Accessibility workflow" in skill

    def test_whitespace_only_values(self):
        """Whitespace-only values treated as empty."""
        values = {
            "workflow_name": "   ",
            "partner_group": "   ",
            "responsibility": "   ",
            "ai_support": "   ",
            "final_output": "   ",
            "human_safeguard": "   ",
        }
        skill = build_skill_markdown(values)

        assert "# Accessibility workflow" in skill

    def test_very_long_values(self):
        """Long text values don't break generation."""
        long_text = "a " * 500 + "very long text"
        values = {
            "workflow_name": "Normal",
            "partner_group": long_text,
            "responsibility": long_text,
            "ai_support": long_text,
            "final_output": long_text,
            "human_safeguard": long_text,
        }
        skill = build_skill_markdown(values)

        # Should still be valid
        assert skill.startswith("---\n")
        assert "# Normal" in skill

    def test_special_yaml_characters_in_description(self):
        """Special YAML characters don't break frontmatter."""
        values = {
            "workflow_name": "Test",
            "partner_group": 'People with "quotes", colons: and @ symbols',
            "responsibility": "Learn",
            "ai_support": "Help",
            "final_output": "Output",
            "human_safeguard": "Review",
        }
        skill = build_skill_markdown(values)

        # Should still parse as valid YAML
        _, frontmatter, _ = skill.split("---\n", 2)
        try:
            import yaml
            parsed = yaml.safe_load(frontmatter)
            assert parsed is not None
        except ImportError:
            pytest.skip("PyYAML not installed")

    def test_newline_variations(self):
        """Handle different newline patterns in multiline fields."""
        values = {
            "workflow_name": "Test",
            "partner_group": "Group",
            "responsibility": "Step 1\nStep 2\r\nStep 3",
            "ai_support": "Task\n\n  - Indented\n  - Another",
            "final_output": "Output",
            "human_safeguard": "Check",
        }
        skill = build_skill_markdown(values)

        assert "Step 1" in skill
        assert "Step 2" in skill
        assert "Step 3" in skill

    def test_missing_values_in_dict(self):
        """Missing keys are handled gracefully."""
        values = {
            "workflow_name": "Test",
            # Missing other keys
        }
        # Should not raise
        skill = build_skill_markdown(values)
        assert "# Test" in skill
