"""The scorer for the owner's marks (lab Pass 44).

The ledger is his own chart calls, logged before they trade. These tests pin
what the registration fixed: which rows are scored, when a score falls due,
how a name is placed among its size tier, and that the shadow line is a record
and nothing more. Prices here are made up so each answer can be checked by
hand.
"""
from __future__ import annotations

import sys
from pathlib import Path

import datetime as dt

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lab"))

fm = pytest.importorskip("forward_marks")


def mark(t, call, **kw):
    return dict({"marked": "2026-11-20", "enter_open_of": "2026-11-23", "ticker": t, "call": call, "last_close": 10.0}, **kw)


def prices(n_sessions=140, drift=None):
    """Sessions from Monday 2026-11-16, one week before the entry day. Every
    name opens at 100; from the entry day (2026-11-23) name k's close on its
    i-th session is 100 * (1 + drift[k] * i). Returns (sessions, opens, close)."""
    drift = drift or {"SPY": 0.001, "AAA": 0.004, "BBB": 0.002, "CCC": 0.000, "DDD": -0.001, "EEE": -0.003, "ZZZ": 0.001}
    days, d = [], dt.date(2026, 11, 16)
    while len(days) < n_sessions + 5:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += dt.timedelta(days=1)
    close = {t: [100.0 if i < 5 else 100.0 * (1 + g * (i - 4)) for i in range(len(days))] for t, g in drift.items()}
    opens = {t: [100.0] * len(days) for t in drift}
    return days, opens, close


UNIVERSE = {t: {"ticker": t, "cap_m": str(cap), "sector": "x", "cap_date": "2026-11-20"}
            for t, cap in (("AAA", 5000), ("BBB", 4000), ("CCC", 3000), ("DDD", 2000), ("EEE", 1000))}


@pytest.fixture(autouse=True)
def one_tier(monkeypatch):
    monkeypatch.setattr(fm, "TIER_EDGES", [10 ** 6])
    monkeypatch.setattr(fm, "TIER_NAMES", ["all"])


def test_which_rows_are_scored():
    marks = [mark("AAA", "potential"), mark("BBB", "broken"), mark("CCC", "ideal"),
             mark("DDD", "potential"), mark("DDD", "withdrawn"),
             mark("AAA", "potential", duplicate_of_earlier_row=True),
             mark("EEE", "something else")]
    live = fm.live_marks(marks)
    assert [(m["ticker"], m["call"]) for m in live] == [("AAA", "potential"), ("BBB", "broken"), ("CCC", "ideal")]


def test_a_withdrawal_only_removes_the_same_entry_session():
    marks = [mark("DDD", "potential"), mark("DDD", "withdrawn"),
             mark("DDD", "potential", marked="2026-12-04", enter_open_of="2026-12-07")]
    live = fm.live_marks(marks)
    assert [(m["ticker"], m["enter_open_of"]) for m in live] == [("DDD", "2026-12-07")]


def test_place_among_peers():
    assert fm.place(0.05, [0.01, 0.02, 0.03, 0.10]) == 75.0
    assert fm.place(0.02, [0.02, 0.02]) == 50.0          # ties count as half
    assert fm.place(float("nan"), [0.01]) is None
    assert fm.place(0.01, []) is None


def test_scores_fall_due_at_20_65_and_130_sessions():
    days, opens, close = prices(n_sessions=70)
    rows = fm.score([mark("AAA", "potential")], days, opens, close, UNIVERSE)
    r = rows[0]
    assert r["entered"] == "2026-11-23" and r["status"] == "open"
    assert r["scores"]["4w"] is not None and r["scores"]["13w"] is not None and r["scores"]["26w"] is None
    # the 20th session's close: 100 * (1 + 0.004 * 20) from an open of 100
    assert r["scores"]["4w"]["return"] == pytest.approx(0.08)
    assert r["scores"]["4w"]["spy"] == pytest.approx(0.02)
    assert r["scores"]["13w"]["return"] == pytest.approx(0.004 * 65)


def test_the_best_name_places_at_100_and_the_worst_at_0():
    days, opens, close = prices()
    rows = {r["ticker"]: r for r in fm.score([mark("AAA", "potential"), mark("EEE", "broken"), mark("CCC", "ideal")],
                                             days, opens, close, UNIVERSE)}
    assert rows["AAA"]["scores"]["13w"]["place"] == 100.0
    assert rows["EEE"]["scores"]["13w"]["place"] == 0.0
    assert rows["CCC"]["scores"]["13w"]["place"] == 50.0       # two peers above, two below
    assert rows["AAA"]["scores"]["13w"]["peers"] == 4          # itself is not a peer
    assert rows["AAA"]["status"] == "closed"


def test_a_mark_whose_entry_day_has_not_come_is_not_scored():
    days, opens, close = prices(n_sessions=30)
    rows = fm.score([mark("AAA", "potential", marked="2027-06-04", enter_open_of="2027-06-07")], days, opens, close, UNIVERSE)
    assert rows[0]["status"] == "not yet entered" and rows[0]["scores"] == {}


def test_a_name_outside_the_universe_takes_the_tier_its_size_ranks_in():
    days, opens, close = prices()
    rows = fm.score([mark("ZZZ", "potential")], days, opens, close, UNIVERSE, outsider_caps={"ZZZ": 2500.0})
    assert rows[0]["tier"] == "all" and rows[0]["scores"]["4w"]["peers"] == 5
    assert rows[0]["scores"]["4w"]["place"] == 60.0             # 0.1% a session: above CCC, DDD and EEE, below AAA and BBB


def test_the_shadow_line_records_a_break_and_does_not_change_the_score():
    days, opens, close = prices()
    plain = fm.score([mark("EEE", "potential")], days, opens, close, UNIVERSE)[0]
    shadow = {"lower_line_on_mark_date": 95.0, "slope_year": 0.10}
    with_line = fm.score([mark("EEE", "potential", shadow=shadow)], days, opens, close, UNIVERSE)[0]
    assert with_line["scores"] == plain["scores"]
    b = with_line["shadow_break"]
    # EEE loses 0.3 a session from 100: under 95-and-rising within four weeks, read on a week's last session
    assert b is not None and dt.date.fromisoformat(b["week_ending"]).weekday() == 4 and b["close"] < b["line"]
    rising = fm.score([mark("AAA", "potential", shadow=shadow)], days, opens, close, UNIVERSE)[0]
    assert rising["shadow_break"] is None


def test_nothing_is_concluded_under_forty_marks():
    days, opens, close = prices()
    rows = fm.score([mark("AAA", "potential"), mark("EEE", "broken")], days, opens, close, UNIVERSE)
    s = fm.summarise(rows)
    assert s["potential"]["13w"]["scored"] == 1 and s["potential"]["13w"]["mean_place"] == 100.0
    lines = fm.verdict(s)
    assert all("too few" in ln for ln in lines)
    many = {t: dict(s[t]) for t in s}
    many["potential"]["13w"] = {"scored": 40, "mean_place": 58.0, "share_above_50": 0.6, "t_against_50": 2.1,
                                "mean_return_over_spy": 0.01}
    assert "it is." in fm.verdict(many)[0] and "above 50" in fm.verdict(many)[0]
