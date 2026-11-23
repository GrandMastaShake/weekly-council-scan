"""The forward switch lines (lab Pass 66).

These tests pin the registered rules with made-up numbers: two or more
flags is a defensive week; a line takes the Council's week when
defensive and the trend book's when not; a change of source costs
0.20%; a call applies to the week after its Friday; the calls file is
append-only and a call written after Monday's open is marked late.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lab"))

fs = pytest.importorskip("forward_switch")


def test_two_flags_is_defensive():
    assert [fs.call_for(n) for n in (0, 1, 2, 3)] == ["trending", "trending", "defensive", "defensive"]


def test_a_line_takes_the_source_its_switch_names_and_pays_to_change():
    weeks = [{"friday": "2026-11-27", "call": "defensive", "cold": True, "council": 0.01, "trend": 0.05, "spy": -0.02},
             {"friday": "2026-12-04", "call": "trending", "cold": True, "council": -0.03, "trend": 0.10, "spy": 0.02}]
    rows = fs.chain(weeks)
    v = rows[-1]["value"]
    assert v["on the Council's call"] == pytest.approx(100 * 1.01 * (1 - fs.SWITCH_COST) * 1.10, abs=1e-3)
    assert v["on the 40-week rule"] == pytest.approx(100 * 1.01 * 0.97, abs=1e-3)
    assert v["the Council's book"] == pytest.approx(100 * 1.01 * 0.97, abs=1e-3)
    assert v["the trend book"] == pytest.approx(100 * 1.05 * 1.10, abs=1e-3)
    assert v["SPY"] == pytest.approx(100 * 0.98 * 1.02, abs=1e-3)
    assert rows[0]["source"] == {"on the Council's call": "council", "on the 40-week rule": "council"}


def test_a_week_the_council_did_not_book_counts_as_flat_and_is_marked():
    rows = fs.chain([{"friday": "2026-11-27", "call": "defensive", "cold": False, "council": None, "trend": 0.04, "spy": 0.0}])
    assert rows[0]["council_missing"] and rows[0]["value"]["on the Council's call"] == 100.0
    assert rows[0]["value"]["on the 40-week rule"] == pytest.approx(104.0)


def test_a_call_applies_to_the_week_after_its_friday():
    calls = []
    fs.add_call(calls, "2026-11-20", 2, 223, "Regime flags: 2 up", "2026-11-23T07:58:00")
    ledger = {"weeks": [{"friday": "2026-11-20", "cold": True}, {"friday": "2026-11-27", "cold": False}],
              "books": {fs.TREND_BOOK: {"history": [{"friday": "2026-11-20", "equity": 100.0, "spy_close": 700.0},
                                                    {"friday": "2026-11-27", "equity": 102.0, "spy_close": 714.0}]}}}
    weeks = fs.join(calls, ledger, {"2026-11-23": 0.015, "2026-11-16": -0.5})
    assert len(weeks) == 1
    w = weeks[0]
    assert (w["friday"], w["call"], w["cold"]) == ("2026-11-27", "defensive", True)
    assert w["council"] == 0.015 and w["trend"] == pytest.approx(0.02) and w["spy"] == pytest.approx(0.02)


def test_a_holiday_week_booked_on_tuesday_is_still_found():
    calls = []
    fs.add_call(calls, "2026-11-20", 1, 1, "h", "2026-11-22T18:00:00")
    ledger = {"weeks": [{"friday": "2026-11-20", "cold": False}],
              "books": {fs.TREND_BOOK: {"history": [{"friday": "2026-11-20", "equity": 100.0, "spy_close": 700.0},
                                                    {"friday": "2026-11-27", "equity": 100.0, "spy_close": 700.0}]}}}
    assert fs.join(calls, ledger, {"2026-11-24": 0.02})[0]["council"] == 0.02
    assert fs.join(calls, ledger, {"2026-11-30": 0.02})[0]["council"] is None


def test_the_calls_file_is_append_only_and_marks_a_late_call():
    calls = []
    early = fs.add_call(calls, "2026-11-20", 2, 223, "h", "2026-11-23T09:29:59")
    assert not early["late"] and early["applies_to_week_of"] == "2026-11-23"
    with pytest.raises(ValueError):
        fs.add_call(calls, "2026-11-20", 0, 223, "h", "2026-11-23T08:00:00")
    with pytest.raises(ValueError):
        fs.add_call(calls, "2026-11-13", 0, 208, "h", "2026-11-23T08:00:00")
    late = fs.add_call(calls, "2026-11-27", 1, 230, "h", "2026-11-30T09:30:00")
    assert late["late"] and late["call"] == "trending"


def test_drawdown():
    assert fs.drawdown([100.0, 110.0, 99.0, 120.0]) == pytest.approx(-0.1)
