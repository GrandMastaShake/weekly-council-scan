"""The cash floor (2026-08-09) and the two ways it went quiet.

facts.json records the Fed's last move ("Hold", "Hike", "Cut"), and the floor
only knew stance words, so the first hike since 2023 read as nothing. And the
Monday pipeline read a copy of the table that nothing refreshed after 09-14,
so it saw July's "Hold" on both 09-21 and 09-28 while the truth gate passed a
fresh copy elsewhere. Found by the Council itself in the 2026-09-28 report.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scan_pipeline import run_scan as rs  # noqa: E402


def facts(stance, generated="2026-09-25"):
    return {"schema": "macro-facts/v1", "generated": generated,
            "policy": {"fed_stance": {"value": stance, "as_of": "2026-09-16"}},
            "rates": {"ust_10y": {"value": 5.184}}}


@pytest.mark.parametrize("word", ["Hike", "hike", "Hawkish", "Tightening. +25bp on 09-16"])
def test_a_hike_or_a_hawkish_word_fires_the_floor(word):
    assert rs.macro_floor_trigger(facts(word), {}) is not None


@pytest.mark.parametrize("word", ["Hold", "Cut", "Dovish", "Easing", "Neutral"])
def test_a_hold_or_a_cut_does_not(word):
    assert rs.macro_floor_trigger(facts(word), {}) is None


def test_the_reason_names_the_word_and_the_stance_it_implies():
    assert rs.macro_floor_trigger(facts("Hike"), {}) == \
        "fed stance 'hike' = tightening (facts.json policy.fed_stance)"


def test_facts_json_outranks_the_command_line_stance():
    assert rs.macro_floor_trigger(facts("Hold"), {"fed_stance": "Tightening."}) is None
    assert rs.macro_floor_trigger({}, {"fed_stance": "Tightening. Rates 3.75-4.00%."}) is not None


def test_a_hike_scales_the_book_by_the_floor():
    r = {"portfolio": {"A": 0.40, "B": 0.30, "C": 0.30}}
    note = rs.apply_cash_floor(r, facts("Hike"), {})
    assert sum(r["portfolio"].values()) == pytest.approx(1 - rs.CASH_FLOOR_DEFAULT)
    assert "hike" in note and "cash floor 15% applied" in note


def write(root: Path, rel: str, doc: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_the_newer_table_wins_and_a_stale_one_says_so(tmp_path, capsys):
    """The 09-28 layout: the pipeline's copy from 09-12, the repo's from 09-25."""
    write(tmp_path, "truth_gate/macro/facts.json", facts("Hold", "2026-09-12"))
    write(tmp_path, "macro/facts.json", facts("Hike", "2026-09-25"))
    got = rs.load_macro_facts("2026-09-28", root=str(tmp_path))
    assert got["generated"] == "2026-09-25"
    out = capsys.readouterr().out
    assert "read macro/facts.json, generated 2026-09-25, 3 days before the scan" in out
    assert "WARNING" not in out

    (tmp_path / "macro" / "facts.json").unlink()
    got = rs.load_macro_facts("2026-09-28", root=str(tmp_path))
    assert got["generated"] == "2026-09-12"
    assert "16 days before the scan -- WARNING" in capsys.readouterr().out


def test_a_missing_table_falls_back_quietly(tmp_path, capsys):
    assert rs.load_macro_facts("2026-09-28", root=str(tmp_path)) == {}
    assert "not found" in capsys.readouterr().out
