"""The owner's cash cap (2026-09-21): at most 20% cash outside an abort.

apply_cash_cap runs after the cash floor. It tops a short book up to 80%
invested without breaking the per-name maximum or the per-sponsor cap, and
says CASH CAP UNMET when the names cannot get there.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scan_pipeline import run_scan as rs  # noqa: E402


def book(portfolio, attribution=None):
    return {"portfolio": dict(portfolio), "attribution": dict(attribution or {})}


def test_a_book_already_at_80_percent_is_left_alone():
    r = book({"A": 0.30, "B": 0.30, "C": 0.20})
    assert rs.apply_cash_cap(r) is None
    assert r["portfolio"] == {"A": 0.30, "B": 0.30, "C": 0.20}
    assert "cash_cap" not in r


def test_a_short_book_is_topped_up_to_80_percent_in_proportion():
    r = book({"A": 0.20, "B": 0.20, "C": 0.20})
    note = rs.apply_cash_cap(r, max_position=0.30, sponsor_cap=1.0)
    assert sum(r["portfolio"].values()) == pytest.approx(0.80, abs=1e-5)
    assert len(set(r["portfolio"].values())) == 1, "equal weights stay equal"
    assert "60.0% -> 80.0%" in note and "UNMET" not in note


def test_a_position_stops_at_the_maximum_and_the_rest_keep_rising():
    r = book({"A": 0.28, "B": 0.14, "C": 0.14, "D": 0.14})
    rs.apply_cash_cap(r, max_position=0.30, sponsor_cap=1.0)
    p = r["portfolio"]
    assert sum(p.values()) == pytest.approx(0.80, abs=1e-5)
    assert p["A"] == pytest.approx(0.30)
    assert max(p.values()) <= 0.30 + 1e-9


def test_the_sponsor_cap_holds_while_topping_up():
    r = book({"A": 0.25, "B": 0.10, "C": 0.10, "D": 0.10},
             {"A": "Cecil", "B": "Marky", "C": "Marky", "D": "Ophelia"})
    rs.apply_cash_cap(r, max_position=0.30, sponsor_cap=0.40)
    p = r["portfolio"]
    assert sum(p.values()) == pytest.approx(0.80, abs=1e-5)
    assert p["B"] + p["C"] <= 0.40 + 1e-6
    assert max(p.values()) <= 0.30 + 1e-9


def test_too_few_names_says_unmet_rather_than_breaking_a_limit():
    r = book({"A": 0.20, "B": 0.20})
    note = rs.apply_cash_cap(r, max_position=0.30, sponsor_cap=1.0)
    assert r["portfolio"] == {"A": 0.30, "B": 0.30}
    assert "CASH CAP UNMET" in note


def test_the_floor_then_the_cap_leaves_a_risk_off_book_between_80_and_85():
    """A 3-name book at the 30% maximum is 90% invested; the 15% floor scales
    it to 76.5%, and the cap brings it back to 80%: 20% cash, still above the
    floor. A fully invested book keeps the floor's 85% untouched."""
    r = book({"A": 0.30, "B": 0.30, "C": 0.30})
    r["portfolio"] = {t: w * (1 - rs.CASH_FLOOR_DEFAULT) for t, w in r["portfolio"].items()}
    rs.apply_cash_cap(r, max_position=0.30, sponsor_cap=1.0)
    assert sum(r["portfolio"].values()) == pytest.approx(0.80, abs=1e-5)
    full = book({"A": 0.30, "B": 0.25, "C": 0.25, "D": 0.20})
    full["portfolio"] = {t: w * (1 - rs.CASH_FLOOR_DEFAULT) for t, w in full["portfolio"].items()}
    assert rs.apply_cash_cap(full) is None
    assert sum(full["portfolio"].values()) == pytest.approx(0.85)


def test_an_empty_book_is_not_touched():
    r = book({})
    assert rs.apply_cash_cap(r) is None
    assert r["portfolio"] == {}
