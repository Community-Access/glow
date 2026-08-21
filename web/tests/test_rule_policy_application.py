"""Applying a rule policy to an audit result, whichever result shape arrives.

The audit routes used to filter findings in place. That worked against the
legacy audit result and raised on the post-split shared-core `AuditResult`,
which is a frozen, slotted dataclass -- so every audit returned HTTP 500 in
deployment while passing every test in a source checkout, because the shared
core is installed in one and absent from the other.

These tests use stand-ins for both shapes so the guard holds whether or not
quill-glow-core is installed in the environment running them.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from acb_large_print_web.rules import apply_rule_policy, filter_findings, with_findings


@dataclass(frozen=True)
class _Finding:
    rule_id: str


@dataclass(frozen=True, slots=True)
class _ContractResult:
    """The same shape as quill_glow_core.models.AuditResult."""

    file_path: str
    score: int
    grade: str
    findings: list


class _LegacyResult:
    """The pre-split result: an ordinary mutable object."""

    def __init__(self, findings: list) -> None:
        self.findings = findings
        self.score = 95
        self.grade = "A"


class _Policy:
    def __init__(self, selected: set[str], suppressed: set[str]) -> None:
        self.selected = frozenset(selected)
        self.suppressed = frozenset(suppressed)


FINDINGS = [_Finding("ACB-LINK-TEXT"), _Finding("ACB-MISSING-ALT-TEXT"), _Finding("ACB-FAUX-HEADING")]


def test_a_frozen_result_is_filtered_rather_than_mutated():
    original = _ContractResult("doc.docx", 95, "A", list(FINDINGS))

    filtered = with_findings(original, [FINDINGS[0]])

    assert [f.rule_id for f in filtered.findings] == ["ACB-LINK-TEXT"]
    # The original is untouched, which is what frozen is for.
    assert len(original.findings) == 3
    assert filtered.score == 95
    assert filtered.grade == "A"
    assert filtered.file_path == "doc.docx"


def test_a_legacy_result_still_works():
    original = _LegacyResult(list(FINDINGS))

    filtered = with_findings(original, [FINDINGS[1]])

    assert [f.rule_id for f in filtered.findings] == ["ACB-MISSING-ALT-TEXT"]


def test_applying_a_policy_drops_suppressed_rules_on_a_frozen_result():
    result = _ContractResult("doc.docx", 88, "B", list(FINDINGS))
    policy = _Policy(
        selected={"ACB-LINK-TEXT", "ACB-MISSING-ALT-TEXT", "ACB-FAUX-HEADING"},
        suppressed={"ACB-FAUX-HEADING"},
    )

    applied = apply_rule_policy(result, policy)

    assert {f.rule_id for f in applied.findings} == {"ACB-LINK-TEXT", "ACB-MISSING-ALT-TEXT"}


def test_applying_a_policy_never_raises_on_an_awkward_result():
    """A request that shows too many findings is wrong. A 500 is worse."""

    class _Stubborn:
        findings = FINDINGS  # class attribute, and the instance rejects writes

        def __setattr__(self, name, value):
            raise AttributeError(name)

    applied = apply_rule_policy(_Stubborn(), _Policy(selected={"ACB-LINK-TEXT"}, suppressed=set()))

    assert applied is not None
    assert hasattr(applied, "findings")


@pytest.mark.parametrize(
    ("selected", "suppressed", "expected"),
    [
        ({"ACB-LINK-TEXT"}, set(), {"ACB-LINK-TEXT"}),
        ({"ACB-LINK-TEXT"}, {"ACB-LINK-TEXT"}, set()),
        (set(), set(), set()),
    ],
)
def test_the_filter_itself_is_unchanged(selected, suppressed, expected):
    assert {f.rule_id for f in filter_findings(FINDINGS, selected - suppressed)} == expected
