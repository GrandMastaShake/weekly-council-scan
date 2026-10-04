"""Dad's Claude kit must stay uploadable and ASCII.

The kit's skills are uploaded to claude.ai by hand, as zips. The upload
form rejects a skill whose folder is not the zip root, whose folder name
differs from its `name`, or whose description runs over 200 characters --
and it says so only after someone has walked a non-technical user through
the upload. These checks move that failure to CI, where it is cheap.

ASCII because the owner works on Windows and the kit's text is pasted into
settings boxes and opened in Notepad; a smart quote that survives the round
trip as mojibake is a bug a reader sees.
"""
from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "dad-kit"


def _load_build_kit():
    spec = importlib.util.spec_from_file_location("build_kit", KIT / "build_kit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_kit = _load_build_kit()
SKILLS = build_kit.skill_dirs()


def test_there_are_skills_to_check():
    assert {d.name for d in SKILLS} >= {"stock-research", "golf-course-ops"}


@pytest.mark.parametrize("skill_dir", SKILLS, ids=lambda d: d.name)
def test_skill_passes_upload_rules(skill_dir):
    assert build_kit.check_skill(skill_dir) == []


@pytest.mark.parametrize("skill_dir", SKILLS, ids=lambda d: d.name)
def test_zip_has_the_skill_folder_as_its_root(skill_dir, tmp_path):
    archive = build_kit.zip_skill(skill_dir, tmp_path)
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    assert f"{skill_dir.name}/SKILL.md" in names
    assert all(n.startswith(f"{skill_dir.name}/") for n in names), names
    assert not any("\\" in n for n in names), "backslash paths break on non-Windows unzip"


def test_zip_is_reproducible(tmp_path):
    skill_dir = SKILLS[0]
    first = build_kit.zip_skill(skill_dir, tmp_path / "a").read_bytes()
    second = build_kit.zip_skill(skill_dir, tmp_path / "b").read_bytes()
    assert first == second


def test_checker_catches_a_mismatched_name(tmp_path):
    bad = tmp_path / "golf-course-ops"
    bad.mkdir()
    (bad / "SKILL.md").write_text(
        "---\nname: golf-ops\ndescription: x\n---\n\nSee `references/missing.md`.\n",
        encoding="utf-8",
    )
    problems = build_kit.check_skill(bad)
    assert any("does not match its folder" in p for p in problems)
    assert any("references/missing.md" in p for p in problems)


def test_checker_catches_a_long_description(tmp_path):
    bad = tmp_path / "long-one"
    bad.mkdir()
    (bad / "SKILL.md").write_text(
        "---\nname: long-one\ndescription: " + "x" * 201 + "\n---\n", encoding="utf-8"
    )
    assert any("limit 200" in p for p in build_kit.check_skill(bad))


def _kit_text_files():
    return sorted(
        p for p in KIT.rglob("*")
        if p.is_file() and "dist" not in p.relative_to(KIT).parts and p.suffix in {".md", ".txt", ".py"}
    )


def test_kit_has_text_files():
    assert len(_kit_text_files()) >= 10


@pytest.mark.parametrize("path", _kit_text_files(), ids=lambda p: p.relative_to(KIT).as_posix())
def test_kit_file_is_ascii(path):
    data = path.read_bytes()
    bad = [(i, b) for i, b in enumerate(data) if b > 127]
    assert not bad, f"non-ASCII byte at offset {bad[0][0]}: {data[max(0, bad[0][0] - 30):bad[0][0] + 10]!r}"


def test_workbooks_build_with_their_formulas(tmp_path):
    """The standings add themselves up from Weekly Scores; if a formula
    goes missing, the sheet still opens and silently shows blanks."""
    openpyxl = pytest.importorskip("openpyxl")
    paths = {p.name: p for p in build_kit.build_workbooks(tmp_path)}
    assert set(paths) == {"Investing Journal.xlsx", "League Manager.xlsx", "Golf Course Organizer.xlsx"}

    league = openpyxl.load_workbook(paths["League Manager.xlsx"])
    assert league.sheetnames == ["How To Use", *build_kit.LEAGUE_SHEETS]
    assert league["Weekly Scores"]["G2"].value.startswith("=IF(AND(E2")
    assert "SUMIF('Weekly Scores'!$C:$C,A2,'Weekly Scores'!$H:$H)" in league["Standings"]["C2"].value
    assert "SUMIF('Weekly Scores'!$D:$D,A2" in league["Team Standings"]["B2"].value
    assert league["Money"]["F2"].value.startswith("=IF(AND(D2")

    journal = openpyxl.load_workbook(paths["Investing Journal.xlsx"])
    assert journal["Holdings"]["M2"].value.startswith("=IF(AND(J2")
