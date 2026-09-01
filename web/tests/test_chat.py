"""Tests for document chat/interrogation feature."""

from __future__ import annotations

import pytest
from acb_large_print_web import ai_features

from acb_large_print_web.chat_handler import (
    DocumentContext,
    ToolRegistry,
    ChatSession,
    ConversationTurn,
    CATEGORY_COMPLIANCE,
    CATEGORY_CONTENT,
    CATEGORY_DOCUMENT,
    CATEGORY_REMEDIATION,
    CATEGORY_STRUCTURE,
)


class TestDocumentContext:
    """Test document context extraction."""

    def test_extract_headings(self):
        """Headings are properly extracted."""
        text = """# Title
        
## Section 1
Some text here.

### Subsection 1.1
More text."""
        context = DocumentContext(text, "test.md")
        assert len(context.headings) == 3
        assert context.headings[0]["text"] == "Title"
        assert context.headings[0]["level"] == 1

    def test_compute_stats(self):
        """Document stats are computed correctly."""
        text = "This is a test document. " * 50  # ~300 words
        context = DocumentContext(text, "test.md")
        assert context.stats["words"] > 200
        assert context.stats["filename"] == "test.md"
        assert context.stats["reading_time_minutes"] >= 1

    def test_extract_tables(self):
        """Markdown tables are extracted."""
        text = """| Name | Age |
| --- | --- |
| Alice | 30 |
| Bob | 25 |"""
        context = DocumentContext(text, "test.md")
        assert len(context.tables) == 1


class TestToolRegistry:
    """Test tool calling registry."""

    @pytest.fixture
    def context(self):
        """Sample document context."""
        text = """# Main Title

## Section A
Content for section A goes here.

## Section B
This is section B content.

| Product | Price |
| --- | --- |
| Item 1 | $10 |
| Item 2 | $20 |
"""
        return DocumentContext(text, "sample.md")

    @pytest.fixture
    def tools(self, context):
        """Tool registry instance."""
        return ToolRegistry(context)

    def test_list_headings(self, tools):
        """Tool can list all headings."""
        result = tools.list_headings()
        assert "Main Title" in result
        assert "Section A" in result
        assert "Section B" in result

    def test_find_section(self, tools):
        """Tool can find a section by name."""
        result = tools.find_section("Section A")
        assert "Section A" in result
        assert "Content for section A" in result

    def test_search_text(self, tools):
        """Tool can search for keywords."""
        result = tools.search_text("Price")
        assert "Price" in result

    def test_search_not_found(self, tools):
        """Tool returns message when search fails."""
        result = tools.search_text("nonexistent_keyword_xyz")
        assert "not found" in result.lower() or "no match" in result.lower()

    def test_get_document_stats(self, tools):
        """Tool returns document stats."""
        result = tools.get_document_stats()
        assert "sample.md" in result
        assert "Words:" in result
        assert "Headings:" in result

    def test_extract_table(self, tools):
        """Tool can extract a table."""
        result = tools.extract_table("0")
        assert "Product" in result
        assert "Price" in result

    def test_call_dispatcher_unknown(self, tools):
        """Unknown tool name returns error string."""
        result = tools.call("nonexistent_tool")
        assert "Unknown tool" in result

    def test_get_all_tools_categories(self, tools):
        """All 24 tools are registered with category labels."""
        if not ai_features.ai_chat_enabled():
            pytest.skip("AI chat disabled; skipping tool-registration count check")
        all_tools = tools.get_all_tools()
        assert len(all_tools) >= 24
        categories = {t["category"] for t in all_tools.values()}
        assert CATEGORY_DOCUMENT in categories
        assert CATEGORY_COMPLIANCE in categories
        assert CATEGORY_STRUCTURE in categories
        assert CATEGORY_CONTENT in categories
        assert CATEGORY_REMEDIATION in categories

    # ------------------------------------------------------------------
    # Compliance Agent tools
    # ------------------------------------------------------------------

    def test_run_accessibility_audit_heuristic(self, tools):
        """Heuristic audit runs without a doc_path."""
        result = tools.run_accessibility_audit()
        assert isinstance(result, str)
        assert len(result) > 10

    def test_run_accessibility_audit_italic_detected(self):
        """Heuristic audit flags italic."""
        text = "# Title\n\nThis is _italic text_ which violates ACB.\n"
        ctx = DocumentContext(text, "test.md")
        registry = ToolRegistry(ctx)
        result = registry.run_accessibility_audit()
        assert "italic" in result.lower() or "ACB-NO-ITALIC" in result

    def test_get_compliance_score_triggers_audit(self, tools):
        """get_compliance_score runs audit if cache is empty."""
        result = tools.get_compliance_score()
        assert isinstance(result, str)
        assert len(result) > 5

    def test_get_critical_findings_triggers_audit(self, tools):
        """get_critical_findings runs audit if cache is empty."""
        result = tools.get_critical_findings()
        assert isinstance(result, str)

    def test_get_auto_fixable_findings_triggers_audit(self, tools):
        """get_auto_fixable_findings runs audit if cache is empty."""
        result = tools.get_auto_fixable_findings()
        assert isinstance(result, str)

    def test_compliance_tools_via_call(self, tools):
        """Compliance tools are reachable via call() dispatcher."""
        assert isinstance(tools.call("run_accessibility_audit"), str)
        assert isinstance(tools.call("get_compliance_score"), str)
        assert isinstance(tools.call("get_critical_findings"), str)
        assert isinstance(tools.call("get_auto_fixable_findings"), str)

    # ------------------------------------------------------------------
    # Structure Agent tools
    # ------------------------------------------------------------------

    def test_check_heading_hierarchy_no_skip(self, tools):
        """Valid hierarchy reports no issues."""
        result = tools.check_heading_hierarchy()
        assert "valid" in result.lower() or "no skipped" in result.lower()

    def test_check_heading_hierarchy_skip_detected(self):
        """Skipped heading level is detected."""
        text = "# Title\n\n### Skipped Level 2\n\n## Back To Two\n"
        ctx = DocumentContext(text, "test.md")
        result = ToolRegistry(ctx).check_heading_hierarchy()
        assert "skipped" in result.lower() or "H1" in result

    def test_find_faux_headings_clean(self, tools):
        """No faux headings in clean doc."""
        result = tools.find_faux_headings()
        assert "No obvious" in result or "not found" in result.lower() or "faux" in result.lower()

    def test_find_faux_headings_detected(self):
        """Bold-only short paragraph flagged as faux heading."""
        text = "# Title\n\n**This Is A Faux Heading**\n\nBody text here.\n"
        ctx = DocumentContext(text, "test.md")
        result = ToolRegistry(ctx).find_faux_headings()
        assert "faux" in result.lower() or "bold" in result.lower() or "Faux Heading" in result

    def test_check_list_structure(self, tools):
        """List structure returns summary."""
        result = tools.check_list_structure()
        assert isinstance(result, str)
        assert "bullet" in result.lower() or "list" in result.lower() or "numbered" in result.lower()

    def test_estimate_reading_order(self, tools):
        """Reading order returns risk assessment."""
        result = tools.estimate_reading_order()
        assert "reading order" in result.lower() or "risk" in result.lower()

    def test_structure_tools_via_call(self, tools):
        """Structure tools are reachable via call() dispatcher."""
        assert isinstance(tools.call("check_heading_hierarchy"), str)
        assert isinstance(tools.call("find_faux_headings"), str)
        assert isinstance(tools.call("check_list_structure"), str)
        assert isinstance(tools.call("estimate_reading_order"), str)

    # ------------------------------------------------------------------
    # Content Agent tools
    # ------------------------------------------------------------------

    def test_check_emphasis_patterns_clean(self, tools):
        """No italic in clean doc → OK result."""
        result = tools.check_emphasis_patterns()
        assert "ok" in result.lower() or "no italic" in result.lower()

    def test_check_emphasis_patterns_italic_detected(self):
        """Italic marked up correctly is detected."""
        text = "# Title\n\nThis has _italic_ and also *another* italic.\n"
        ctx = DocumentContext(text, "test.md")
        result = ToolRegistry(ctx).check_emphasis_patterns()
        assert "italic" in result.lower() or "CRITICAL" in result

    def test_check_link_text_clean(self, tools):
        """No bad links in clean doc."""
        result = tools.check_link_text()
        assert "ok" in result.lower() or "no bare" in result.lower()

    def test_check_link_text_bare_url(self):
        """Bare URL is flagged."""
        text = "# Title\n\nSee https://www.example.com/a-very-long-url for more info.\n"
        ctx = DocumentContext(text, "test.md")
        result = ToolRegistry(ctx).check_link_text()
        assert "bare" in result.lower() or "url" in result.lower() or "ACB-LINK-TEXT" in result

    def test_check_link_text_generic(self):
        """Generic link text is flagged."""
        text = "# Title\n\n[click here](https://example.com) to learn more.\n"
        ctx = DocumentContext(text, "test.md")
        result = ToolRegistry(ctx).check_link_text()
        assert "generic" in result.lower() or "click here" in result.lower()

    def test_check_reading_level(self, tools):
        """Reading level returns a summary with average sentence length."""
        result = tools.check_reading_level()
        assert "average sentence" in result.lower() or "reading level" in result.lower()

    def test_check_alignment_hints_clean(self, tools):
        """No alignment overrides in clean Markdown."""
        result = tools.check_alignment_hints()
        assert "no explicit" in result.lower() or "alignment" in result.lower()

    def test_check_alignment_hints_center_detected(self):
        """Center tag is flagged."""
        text = "# Title\n\n<center>Centered text</center>\n"
        ctx = DocumentContext(text, "test.md")
        result = ToolRegistry(ctx).check_alignment_hints()
        assert "center" in result.lower() or "ACB-ALIGNMENT" in result

    def test_content_tools_via_call(self, tools):
        """Content tools are reachable via call() dispatcher."""
        assert isinstance(tools.call("check_emphasis_patterns"), str)
        assert isinstance(tools.call("check_link_text"), str)
        assert isinstance(tools.call("check_reading_level"), str)
        assert isinstance(tools.call("check_alignment_hints"), str)

    # ------------------------------------------------------------------
    # Remediation Agent tools
    # ------------------------------------------------------------------

    def test_explain_rule_known(self, tools):
        """Known rule returns plain-language explanation."""
        result = tools.explain_rule("ACB-NO-ITALIC")
        assert "italic" in result.lower()
        assert "fix" in result.lower() or "Fix" in result

    def test_explain_rule_unknown(self, tools):
        """Unknown rule returns helpful message."""
        result = tools.explain_rule("ACB-MADE-UP")
        assert "not found" in result.lower()

    def test_explain_rule_case_insensitive(self, tools):
        """Rule lookup is case-insensitive."""
        result = tools.explain_rule("acb-no-italic")
        assert "italic" in result.lower()

    def test_suggest_fix_known(self, tools):
        """suggest_fix returns fix instructions for known rule."""
        result = tools.suggest_fix("ACB-ALIGNMENT")
        assert "flush" in result.lower() or "left" in result.lower() or "ACB-ALIGNMENT" in result

    def test_suggest_fix_unknown(self, tools):
        """suggest_fix for unknown rule returns safe fallback."""
        result = tools.suggest_fix("ACB-NONEXISTENT")
        assert "no fix template" in result.lower() or "not found" in result.lower()

    def test_prioritize_findings_heuristic(self, tools):
        """prioritize_findings returns a ranked list even without live audit."""
        result = tools.prioritize_findings()
        assert isinstance(result, str)
        assert "fix" in result.lower() or "priority" in result.lower() or "findings" in result.lower()

    def test_estimate_fix_impact_heuristic(self, tools):
        """estimate_fix_impact returns a summary."""
        result = tools.estimate_fix_impact()
        assert isinstance(result, str)

    def test_check_image_alt_text_none(self, tools):
        """No images → reports none found."""
        result = tools.check_image_alt_text()
        assert "no markdown images" in result.lower() or "no" in result.lower()

    def test_check_image_alt_text_missing(self):
        """Image with empty alt text is flagged."""
        text = "# Title\n\n![](image.png)\n\nAnother image ![ok](other.png)\n"
        ctx = DocumentContext(text, "test.md")
        result = ToolRegistry(ctx).check_image_alt_text()
        assert "empty" in result.lower() or "missing" in result.lower() or "ACB-MISSING-ALT-TEXT" in result

    def test_check_image_alt_text_all_ok(self):
        """Images with alt text pass."""
        text = "# Title\n\n![A photo of a board](image.png)\n"
        ctx = DocumentContext(text, "test.md")
        result = ToolRegistry(ctx).check_image_alt_text()
        assert "ok" in result.lower() or "all" in result.lower()

    def test_remediation_tools_via_call(self, tools):
        """Remediation tools are reachable via call() dispatcher."""
        assert isinstance(tools.call("explain_rule", rule_id="ACB-LINK-TEXT"), str)
        assert isinstance(tools.call("suggest_fix", rule_id="ACB-ALIGNMENT"), str)
        assert isinstance(tools.call("prioritize_findings"), str)
        assert isinstance(tools.call("estimate_fix_impact"), str)
        assert isinstance(tools.call("check_image_alt_text"), str)


class TestConversationTurn:
    """Test conversation turn management."""

    def test_create_turn(self):
        """Can create a new turn."""
        turn = ConversationTurn(1, "What is the main topic?")
        assert turn.turn_number == 1
        assert turn.question == "What is the main topic?"
        assert turn.answer is None

    def test_turn_to_dict(self):
        """Turn can be serialized."""
        turn = ConversationTurn(1, "Question?")
        turn.answer = "Answer!"
        turn.tool_calls = [{"name": "search_text", "params": "keyword"}]
        
        data = turn.to_dict()
        assert data["turn_number"] == 1
        assert data["question"] == "Question?"
        assert data["answer"] == "Answer!"
        assert len(data["tool_calls"]) == 1

    def test_turn_from_dict(self):
        """Turn can be deserialized."""
        original = {
            "turn_number": 1,
            "question": "Question?",
            "answer": "Answer!",
            "tool_calls": [{"name": "search", "params": "x"}],
            "tool_results": {},
        }
        turn = ConversationTurn.from_dict(original)
        assert turn.turn_number == 1
        assert turn.question == "Question?"


class TestChatSession:
    """Test chat session management."""

    def test_create_session(self):
        """Can create a chat session."""
        session = ChatSession("token123", "document.md")
        assert session.token == "token123"
        assert session.filename == "document.md"
        assert len(session.turns) == 0

    def test_add_turn(self):
        """Can add turns to session."""
        session = ChatSession("token123", "doc.md")
        turn1 = session.add_turn("First question?")
        turn2 = session.add_turn("Second question?")
        
        assert len(session.turns) == 2
        assert turn1.turn_number == 1
        assert turn2.turn_number == 2

    def test_session_to_dict(self):
        """Session can be serialized."""
        session = ChatSession("token123", "doc.md")
        turn = session.add_turn("Question?")
        turn.answer = "Answer!"
        
        data = session.to_dict()
        assert data["token"] == "token123"
        assert data["filename"] == "doc.md"
        assert len(data["turns"]) == 1

    def test_session_from_dict(self):
        """Session can be deserialized."""
        original = {
            "token": "token123",
            "filename": "doc.md",
            "created_at": "2026-04-17T12:00:00",
            "turns": [
                {
                    "turn_number": 1,
                    "question": "Q?",
                    "answer": "A!",
                    "tool_calls": [],
                    "tool_results": {},
                }
            ],
        }
        session = ChatSession.from_dict(original)
        assert session.token == "token123"
        assert len(session.turns) == 1

    def test_export_markdown(self):
        """Session exports to markdown."""
        session = ChatSession("token123", "doc.md")
        turn = session.add_turn("What is the topic?")
        turn.answer = "The topic is accessibility."
        
        markdown = session.export_markdown()
        assert "# Chat Session" in markdown
        assert "doc.md" in markdown
        assert "Turn 1" in markdown
        assert "What is the topic?" in markdown
        assert "accessibility" in markdown




class _StubFinding:
    """Minimal stand-in for auditor.Finding (real Capitalized Severity enum)."""

    def __init__(self, rule_id, severity, message, auto_fixable):
        self.rule_id = rule_id
        self.severity = severity
        self.message = message
        self.auto_fixable = auto_fixable


class _StubAuditResult:
    def __init__(self, findings, score):
        self.findings = findings
        self.score = score


class TestLiveAuditCache:
    """Regression tests for the Compliance Agent live-audit path.

    Guards two historical bugs:
      1. The cache builder read f.description (Finding has .message), so every
         live audit raised AttributeError and silently fell back to heuristics.
      2. Severity was compared against lowercase ("critical") while the enum
         value is Capitalized ("Critical"), so counts were always zero and
         get_critical_findings wrongly reported "good shape".
    """

    @pytest.fixture
    def stubbed_tools(self, monkeypatch):
        from pathlib import Path
        from acb_large_print.constants import Severity
        from acb_large_print_web import core_services

        findings = [
            _StubFinding("ACB-NO-ITALIC", Severity.CRITICAL, "Italic text found", True),
            _StubFinding("ACB-FONT-SIZE-BODY", Severity.CRITICAL, "Body text too small", True),
            _StubFinding("ACB-HEADING-HIERARCHY", Severity.HIGH, "Skipped heading level", False),
            _StubFinding("ACB-MARGINS", Severity.MEDIUM, "Margin is 0.5in", True),
        ]
        monkeypatch.setattr(
            core_services,
            "audit_by_extension",
            lambda _p: _StubAuditResult(findings, 40),
        )
        ctx = DocumentContext("# Doc\n\nbody", "known_violations.docx", doc_path=Path("known_violations.docx"))
        return ToolRegistry(ctx)

    def test_audit_cache_populated(self, stubbed_tools):
        """Finding 1: live audit populates a non-empty findings cache."""
        summary = stubbed_tools.run_accessibility_audit()
        cache = stubbed_tools.context._audit_cache
        assert cache is not None
        assert len(cache["findings"]) == 4
        # Severity is normalized to lowercase in the cache.
        assert cache["findings"][0]["severity"] == "critical"
        # Uses .message, not .description.
        assert cache["findings"][0]["message"] == "Italic text found"
        # And it is the live audit, not the heuristic fallback.
        assert "Audit complete" in summary
        assert "Critical: 2" in summary

    def test_get_critical_findings_reports_violations(self, stubbed_tools):
        """Finding 2: critical/high findings are counted, not reported as clean."""
        result = stubbed_tools.get_critical_findings()
        assert "good shape" not in result
        assert "ACB-NO-ITALIC" in result
        assert "3 total" in result  # 2 critical + 1 high

    def test_get_compliance_score_severity_counts(self, stubbed_tools):
        """Finding 2: score summary reflects real severity distribution."""
        result = stubbed_tools.get_compliance_score()
        assert "Critical: 2" in result
        assert "High: 1" in result
        assert "Medium: 1" in result

    def test_auto_fixable_findings(self, stubbed_tools):
        """Auto-fixable findings are listed with their message text."""
        result = stubbed_tools.get_auto_fixable_findings()
        assert "ACB-NO-ITALIC" in result
        assert "Body text too small" in result
        assert "ACB-HEADING-HIERARCHY" not in result  # not auto-fixable


class TestExportPdfFailure:
    """Finding 3 & 4: export_pdf must raise (not silently emit a 0-byte PDF)
    and must pass a timeout to the pandoc subprocess.
    """

    def test_export_pdf_raises_when_pandoc_missing(self, tmp_path, monkeypatch):
        import subprocess

        calls = {}

        def fake_run(*args, **kwargs):
            calls["timeout"] = kwargs.get("timeout")
            raise FileNotFoundError("pandoc not found")

        monkeypatch.setattr(subprocess, "run", fake_run)

        session = ChatSession("tok", "doc.md")
        turn = session.add_turn("Q?")
        turn.answer = "A"
        out = tmp_path / "out.pdf"

        with pytest.raises(Exception):
            session.export_pdf(out)

        # Finding 4: a timeout was supplied to the subprocess.
        assert calls.get("timeout") == 60
        # Temp siblings are cleaned up in finally.
        assert not (tmp_path / "out.md").exists()
        assert not (tmp_path / "out.html").exists()


class TestChatRoutes:
    """Integration tests for chat routes (requires Flask context).

    Note: Route tests are covered by smoke tests in test_app.py.
    Unit tests above verify the core chat_handler module independently.
    """

    pass

