"""The forward ledger of the trend-strength book (lab Pass 63).

These tests pin the frozen rules with made-up prices: orders are written on
Friday and filled at Monday's open, sales before buys; a name goes at 20%
under its high; no more than three names a sector; no buys in a cold
market; the pause after three losing sales; and a week is never counted
twice.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lab"))

fb = pytest.importorskip("forward_book")


def week(friday, ranked, opens=None, closes=None, cold=False):
    f = dt.date.fromisoformat(friday)
    return {"friday": friday, "week_monday": (f - dt.timedelta(days=4)).isoformat(), "monday": (f + dt.timedelta(days=3)).isoformat(),
            "opens": opens or {}, "closes": closes or {}, "spy_close": 100.0, "cold": cold, "ranked": ranked}


def screen(n=12, sectors=("Tech", "Health", "Energy", "Banks")):
    return [(f"N{i:02d}", sectors[i % len(sectors)], 50.0) for i in range(n)]


def test_orders_are_written_on_friday_and_filled_at_mondays_open():
    led = {"books": {}, "weeks": []}
    assert fb.step(led, week("2026-11-20", screen()))
    book = led["books"]["cap of three"]
    assert book["positions"] == {} and book["cash"] == fb.START_EQUITY
    assert book["pending"]["enter_open_of"] == "2026-11-23" and len(book["pending"]["buys"]) == fb.SLOTS
    px = {f"N{i:02d}": 50.0 for i in range(12)}
    fb.step(led, week("2026-11-27", screen(), opens=px, closes=px))
    assert len(book["positions"]) == fb.SLOTS and book["cash"] == pytest.approx(0.0, abs=1e-9)
    assert all(p["bought"] == "2026-11-23" for p in book["positions"].values())
    # ten equal buys of 10.0 each, 0.10% charged on the way in
    assert fb.equity(book) == pytest.approx(fb.START_EQUITY * (1 - fb.SLIP))


def test_no_more_than_three_from_one_sector():
    led = {"books": {}, "weeks": []}
    fb.step(led, week("2026-11-20", [(f"T{i}", "Tech", 50.0) for i in range(8)] + [("H0", "Health", 50.0)]))
    buys = led["books"]["cap of three"]["pending"]["buys"]
    assert [b["ticker"] for b in buys] == ["T0", "T1", "T2", "H0"]


def test_a_name_is_sold_twenty_percent_under_its_high_and_cash_is_reused():
    led = {"books": {}, "weeks": []}
    names = screen(10)
    fb.step(led, week("2026-11-20", names))
    px = {t: 50.0 for t, _, _ in names}
    fb.step(led, week("2026-11-27", [], opens=px, closes=px))
    down = dict(px, N00=39.9)                                   # just over 20% under its high of 50
    fb.step(led, week("2026-12-04", [("NEW", "Banks", 30.0)], opens=px, closes=down))
    book = led["books"]["cap of three"]
    assert book["pending"]["sells"] == ["N00"] and [b["ticker"] for b in book["pending"]["buys"]] == ["NEW"]
    fb.step(led, week("2026-12-11", [], opens=dict(down, N00=39.0, NEW=30.0), closes=dict(down, NEW=30.0)))
    assert "N00" not in book["positions"] and "NEW" in book["positions"]
    sale = [t for t in book["trades"] if t["side"] == "sell"][0]
    assert sale["price"] == 39.0 and sale["date"] == "2026-12-07"
    # the whole of the sale's proceeds went into the one empty slot
    assert book["cash"] == pytest.approx(0.0, abs=1e-9)
    assert book["positions"]["NEW"]["cost"] == pytest.approx(sale["proceeds"], abs=1e-4)     # the trade row is rounded


def test_nineteen_percent_under_the_high_is_kept():
    led = {"books": {}, "weeks": []}
    fb.step(led, week("2026-11-20", screen(10)))
    px = {f"N{i:02d}": 50.0 for i in range(10)}
    fb.step(led, week("2026-11-27", [], opens=px, closes=px))
    fb.step(led, week("2026-12-04", [], opens=px, closes=dict(px, N00=40.5)))
    assert led["books"]["cap of three"]["pending"]["sells"] == []


def test_no_new_buys_in_a_cold_market():
    led = {"books": {}, "weeks": []}
    fb.step(led, week("2026-11-20", screen(), cold=True))
    pend = led["books"]["cap of three"]["pending"]
    assert pend["buys"] == [] and pend["no_buys_because"] == "cold market"


def test_three_losing_sales_in_a_row_pause_one_book_and_not_the_other():
    led = {"books": {}, "weeks": []}
    names = screen(10)
    fb.step(led, week("2026-11-20", names))
    px = {t: 50.0 for t, _, _ in names}
    fb.step(led, week("2026-11-27", [], opens=px, closes=px))
    down = dict(px, N00=39.0, N01=39.0, N02=39.0)
    fresh = [("X1", "Banks", 20.0), ("X2", "Energy", 20.0), ("X3", "Health", 20.0)]
    fb.step(led, week("2026-12-04", fresh, opens=px, closes=down))
    plain, paused = led["books"]["cap of three"], led["books"]["cap of three, pause of eight weeks"]
    assert len(plain["pending"]["sells"]) == 3 and len(plain["pending"]["buys"]) == 3
    assert len(paused["pending"]["sells"]) == 3 and paused["pending"]["buys"] == []
    assert paused["paused_until"] == "2027-01-29" and paused["pending"]["no_buys_because"].startswith("paused")
    # once the three are sold: still paused on the eighth Friday after, buying again on the ninth
    fb.settle(paused, down, "2026-12-07")
    fb.decide(paused, "2027-01-29", "2027-02-01", fresh, False)
    assert paused["pending"]["buys"] == []
    fb.decide(paused, "2027-02-05", "2027-02-08", fresh, False)
    assert len(paused["pending"]["buys"]) == 3


def test_a_week_is_never_counted_twice_and_history_only_grows():
    led = {"books": {}, "weeks": []}
    w = week("2026-11-20", screen())
    assert fb.step(led, w) is True
    before = [dict(r) for r in led["books"]["cap of three"]["history"]]
    assert fb.step(led, w) is False
    assert led["books"]["cap of three"]["history"] == before and len(led["weeks"]) == 1


def test_a_buy_with_no_open_is_skipped_and_its_cash_kept():
    led = {"books": {}, "weeks": []}
    fb.step(led, week("2026-11-20", screen(10)))
    px = {f"N{i:02d}": 50.0 for i in range(9)}                  # N09 did not open
    fb.step(led, week("2026-11-27", [], opens=px, closes=px))
    book = led["books"]["cap of three"]
    assert len(book["positions"]) == 9 and book["cash"] == pytest.approx(fb.START_EQUITY / 10)


def test_the_latest_finished_friday():
    assert fb.last_friday(dt.date(2026, 11, 21)) == dt.date(2026, 11, 20)      # Saturday
    assert fb.last_friday(dt.date(2026, 11, 22)) == dt.date(2026, 11, 20)      # Sunday
    assert fb.last_friday(dt.date(2026, 11, 23)) == dt.date(2026, 11, 20)      # Monday
    assert fb.last_friday(dt.date(2026, 11, 27)) == dt.date(2026, 11, 20)      # a Friday does not count itself
    assert fb.last_friday(dt.date(2026, 11, 28)) == dt.date(2026, 11, 27)


def test_summary_counts_return_and_drawdown_from_one_hundred():
    book = fb.new_book(None)
    book["history"] = [{"friday": "2026-11-20", "equity": 100.0, "cash": 100.0, "names": 0, "spy_close": 200.0},
                       {"friday": "2026-11-27", "equity": 110.0, "cash": 0.0, "names": 10, "spy_close": 210.0},
                       {"friday": "2026-12-04", "equity": 99.0, "cash": 0.0, "names": 10, "spy_close": 220.0}]
    s = fb.summary(book)
    assert s["return"] == pytest.approx(-0.01) and s["spy_return"] == pytest.approx(0.10)
    assert s["largest_drawdown"] == pytest.approx(-0.10) and s["weeks"] == 3
