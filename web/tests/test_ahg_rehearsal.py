"""Source coverage and non-destructive output for the numbered AHG rehearsal."""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import build_ahg_rehearsal as R  # noqa: E402


def test_case_inventory_does_not_import_historical_results():
    cases = R.cases_from_plan((REPO / "ahg.md").read_text(encoding="utf-8"))
    assert next(case for case in cases if case.id == "Design-06").paths == R.PATHS
    assert next(case for case in cases if case.id == "SetupD-01").paths == ("Desktop",)
    assert next(case for case in cases if case.id == "AA-10").paths == ("Desktop", "Web")
    assert all("Pass, Claude" not in case.expected for case in cases)


def test_block_instructions_include_full_actions_without_another_page():
    source = REPO / "docs" / "ahg-2026" / "kit" / "step-cards" / "2-design-your-agent.md"
    text = R.block_instructions(source.read_text(encoding="utf-8"))
    assert "### Step card 2: Design your agent" in text
    assert "##### In a browser" in text
    assert 'paste it into "Your agent to save"' in text
    assert 'press "Download this version"' in text
    assert "Type /design-my-agent and press Enter." in text
    assert "After blocks 3, 4 and 5" in text
    assert "title:" not in text


@pytest.fixture(scope="module")
def rehearsal(tmp_path_factory):
    out = tmp_path_factory.mktemp("rehearsal")
    R.build(out)
    return out


def test_generated_sequence_has_every_case_path_slide_and_source_link(rehearsal):
    R.verify(rehearsal)
    import json

    manifest = json.loads((rehearsal / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["slides"] == 35
    assert all(f"--from-{Path(step['source']).name}" in step["file"] for step in manifest["steps"])
    assert len([step for step in manifest["steps"] if step["title"].startswith("Closing demo:")]) == 3


def test_rebuild_refuses_to_overwrite_results(rehearsal):
    before = (rehearsal / "results.csv").read_bytes()
    with pytest.raises(ValueError, match="not empty"):
        R.build(rehearsal)
    assert (rehearsal / "results.csv").read_bytes() == before


def test_checker_detects_missing_source_and_broken_navigation(rehearsal, tmp_path):
    import shutil

    out = tmp_path / "copy"
    shutil.copytree(rehearsal, out)
    page = out / "000-start-here.html"
    page.write_text(page.read_text(encoding="utf-8").replace("results.csv", "missing.csv"), encoding="utf-8")
    with pytest.raises(ValueError, match="broken local link"):
        R.verify(out)
