"""The weekend pick (lab Pass 67).

These tests pin the registered rules with made-up numbers: a pick is
five different names from the universe, the file is append-only, a pick
written at or after Monday 04:00 is late, both fives are measured equal
weight from the entry open to the last close, and nothing is read before
40 scored weeks.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lab"))

wp = pytest.importorskip("weekend_pick")

U = {"A", "B", "C", "D", "E", "F", "G"}
FIVE = [(t, "Cecil", "because") for t in "ABCDE"]


def test_a_pick_is_five_different_names_from_the_universe():
    with pytest.raises(ValueError):
        wp.add_pick([], "2026-11-27", FIVE[:4], "2026-11-29T18:00:00-05:00", U)
    with pytest.raises(ValueError):
        wp.add_pick([], "2026-11-27", FIVE[:4] + [("A", "Cecil", "x")], "2026-11-29T18:00:00-05:00", U)
    with pytest.raises(ValueError):
        wp.add_pick([], "2026-11-27", FIVE[:4] + [("ZZZ", "Cecil", "x")], "2026-11-29T18:00:00-05:00", U)
    with pytest.raises(ValueError):
        wp.add_pick([], "2026-11-27", FIVE[:4] + [("E", "Nobody", "x")], "2026-11-29T18:00:00-05:00", U)
    with pytest.raises(ValueError):
        wp.add_pick([], "2026-11-26", FIVE, "2026-11-29T18:00:00-05:00", U)


def test_the_file_is_append_only_and_marks_a_late_pick():
    picks = []
    row = wp.add_pick(picks, "2026-11-27", FIVE, "2026-11-30T03:59:59-05:00", U)
    assert not row["late"] and row["applies_to_week_of"] == "2026-11-30"
    with pytest.raises(ValueError):
        wp.add_pick(picks, "2026-11-27", FIVE, "2026-11-29T18:00:00-05:00", U)
    with pytest.raises(ValueError):
        wp.add_pick(picks, "2026-11-20", FIVE, "2026-11-29T18:00:00-05:00", U)
    assert wp.add_pick(picks, "2026-12-04", FIVE, "2026-12-07T04:00:00-05:00", U)["late"]


def test_both_fives_are_measured_the_same_way():
    px = {"SPY": (100, 101, 102.01), "A": (10, 10, 11), "B": (10, 10, 9), "C": (10, 11, 11), "D": (10, 10, 10.5)}
    r = wp.score_week(["A", "B"], ["A", "C", "D"], px)
    assert r["W"] == pytest.approx(0.0) and r["O"] == pytest.approx((0.1 + 0.0 + 0.05) / 3)
    assert r["SPY"] == pytest.approx(0.01) and r["overlap"] == 1
    assert r["gap_edge"] == pytest.approx((0.0 + 0.1 + 0.0) / 3 - 0.01)
    assert r["adds_gap"] == pytest.approx(0.05) and r["drops_gap"] == pytest.approx(0.0)
    assert r["adds_week"] == pytest.approx(0.025) and r["drops_week"] == pytest.approx(-0.1)


def test_nothing_is_read_before_forty_scored_weeks():
    row = {"W": 0.01, "O": 0.0, "gap_edge": 0.0, "adds_gap": 0.0, "drops_gap": 0.0,
           "adds_week": 0.0, "drops_week": 0.0, "overlap": 2}
    with pytest.raises(ValueError):
        wp.lines([row] * 39)
    rows = [dict(row, W=0.01 + 0.001 * (i % 3)) for i in range(40)]
    out = wp.lines(rows)
    assert out["picking earlier is better"] and not out["the Council buys after the move"]


def test_a_holiday_week_booked_on_tuesday_is_still_found():
    assert wp.council_week("2026-11-30", {"2026-12-01": ["A"]}) == "2026-12-01"
    assert wp.council_week("2026-11-30", {"2026-12-07": ["A"]}) is None


def test_the_cutoff_is_new_york_time_whatever_the_machine():
    """2026-11-25: logged was datetime.now() with no zone, read against a
    naive 04:00. On a runner in UTC a pick made at 23:30 Sunday in New York
    read as 04:30 Monday, late; one made at 03:30 New York read on time
    either way, and the file could not say which clock wrote it."""
    on_time = wp.add_pick([], "2026-11-27", FIVE, "2026-11-30T04:30:00+00:00", U)
    assert not on_time["late"]                         # 23:30 Sunday in New York
    assert not wp.add_pick([], "2026-11-27", FIVE, "2026-11-30T08:59:59+00:00", U)["late"]
    assert wp.add_pick([], "2026-11-27", FIVE, "2026-11-30T09:00:00+00:00", U)["late"]
    # Summer: 04:00 EDT is 08:00 UTC.
    assert wp.add_pick([], "2026-06-26", FIVE, "2026-06-29T08:00:00+00:00", U)["late"]
    assert not wp.add_pick([], "2026-06-26", FIVE, "2026-06-29T07:59:59+00:00", U)["late"]


def test_a_time_with_no_offset_is_refused_and_now_et_has_one():
    with pytest.raises(ValueError):
        wp.add_pick([], "2026-11-27", FIVE, "2026-11-29T18:00:00", U)
    stamp = wp.now_et()
    assert wp.logged_et(stamp).utcoffset() is not None
    assert stamp[-6:] in ("-05:00", "-04:00")
