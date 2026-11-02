"""The -5% CORE stop is in the book (the owner's ruling of 2026-11-02).

exit-shadow.md shadowed it from 2026-08-17. Over eleven booked cycles and
37 CORE position-weeks it fired five times, saved money five times and cut
no winner; every tighter level in the calibration table fired on a week
that finished green, and -6% missed HIG. The owner enforced it on
2026-11-02 and left the rest where the log asked: the thesis leg a re-entry
block, the -8% SPEC stop in shadow.

The rule the tracker now runs: every name is CORE unless --open was told
otherwise with --spec; a CORE name is stopped out the first session its Low
trades at or under 95% of the entry, filled at the stop level, or at the
Open when the bar opens through it (the next print after the touch is the
open itself: three of the seven shadow firings were gaps, LRCX 2.15% through
its stop on 2026-10-07). Entry, the week's bars and the stop sit on one
adjusted download, the same-snapshot rule of #112, so an ex-dividend inside
the week moves the stop with the entry. A SPEC name, or a position from a
week opened before the rule, is held to Friday as before.

No network: the provider is stubbed where the tracker meets it. The bars
here are made up to hold the cases, and say so.
"""
from __future__ import annotations

import datetime as dt
import importlib.util

import pytest
import yaml
import yfinance  # the stub conftest installs

from conftest import ROOT


def _load_tracker():
    spec = importlib.util.spec_from_file_location(
        "portfolio_tracker_stop", ROOT / "portfolio" / "tracker.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tk = _load_tracker()

D = dt.date
MON, TUE, WED, THU, FRI = (D(2026, 11, 2), D(2026, 11, 3), D(2026, 11, 4),
                           D(2026, 11, 5), D(2026, 11, 6))
WEEK = "2026-11-02"


def bar(o, high, low, close):
    return {"Open": o, "High": high, "Low": low, "Close": close}


class Frame:
    """What the provider hands back, as far as the tracker looks at it."""

    columns = ("Close", "High", "Low", "Open", "Volume")

    def __init__(self, rows):
        self.rows = rows

    @property
    def empty(self):
        return not self.rows

    def iterrows(self):
        for day, fields in self.rows:
            yield dt.datetime(day.year, day.month, day.day), dict(fields)


@pytest.fixture
def provider(monkeypatch):
    """Stub yfinance.download. Set table[symbol] to {date: bar}."""
    table = {}

    def download(symbol, start=None, end=None, progress=False,
                 auto_adjust=True):
        assert auto_adjust is True
        rows = table.get(symbol, {})
        return Frame([(day, rows[day]) for day in sorted(rows)
                      if start <= day.isoformat() < end])

    monkeypatch.setattr(yfinance, "download", download, raising=False)
    return table


@pytest.fixture(autouse=True)
def nothing_in_the_repo(tmp_path, monkeypatch):
    """Every path the tracker writes, moved under tmp_path. The official
    book is never touched by a test, whatever the test gets wrong."""
    book = tmp_path / "portfolio"
    book.mkdir()
    (book / "history").mkdir()
    (tmp_path / "scorecards").mkdir()
    monkeypatch.setattr(tk, "PORTFOLIO_DIR", book)
    monkeypatch.setattr(tk, "CURRENT_PATH", book / "current.yaml")
    monkeypatch.setattr(tk, "HISTORY_DIR", book / "history")
    monkeypatch.setattr(tk, "RESTATEMENTS_DIR", book / "restatements")
    monkeypatch.setattr(tk, "METRICS_PATH", book / "metrics.json")
    monkeypatch.setattr(tk, "SCORECARDS_DIR", tmp_path / "scorecards")
    monkeypatch.setattr(tk, "SCOREBOARD_PATH", tmp_path / "scoreboard.md")
    monkeypatch.setattr(tk, "REPORTS_DIR", tmp_path / "reports")


# -- the fill rule, on bars alone ---------------------------------------------

# A $100 entry. The stop is $95.
HELD_NO_TOUCH = [("2026-11-02", bar(100.0, 101.0, 96.0, 97.0)),
                 ("2026-11-03", bar(97.0, 99.0, 95.01, 98.0))]
HELD_TOUCH_WED = HELD_NO_TOUCH + [("2026-11-04", bar(97.5, 98.0, 94.0, 94.5)),
                                  ("2026-11-05", bar(94.5, 99.0, 93.0, 98.9))]
HELD_GAP_THU = HELD_NO_TOUCH + [("2026-11-04", bar(97.5, 98.0, 95.5, 96.0)),
                                ("2026-11-05", bar(92.85, 94.0, 91.0, 93.5))]


def test_a_week_that_never_trades_down_to_the_stop_does_not_fire():
    assert tk.stop_fill(100.0, -5.0, HELD_NO_TOUCH) is None


def test_a_low_a_cent_above_the_stop_is_not_a_touch():
    assert tk.stop_fill(100.0, -5.0, [("2026-11-03", bar(97.0, 99.0, 95.01, 98.0))]) is None
    assert tk.stop_fill(100.0, -5.0, [("2026-11-03", bar(97.0, 99.0, 95.0, 98.0))]) == (
        "2026-11-03", 95.0, "stop_level")


def test_the_first_touch_fills_at_the_stop_level_and_the_week_after_it_is_not_seen():
    """Thursday's recovery to 98.9 is the week the book no longer has."""
    assert tk.stop_fill(100.0, -5.0, HELD_TOUCH_WED) == ("2026-11-04", 95.0, "stop_level")


def test_a_bar_that_opens_through_the_stop_fills_at_its_open():
    """The next print after the touch is the open: 92.85, not 95. The gap is
    the book's, as LRCX's was on 2026-10-07."""
    assert tk.stop_fill(100.0, -5.0, HELD_GAP_THU) == ("2026-11-05", 92.85, "gap_open")


def test_a_bar_that_opens_on_the_stop_is_a_gap_fill_at_that_open():
    assert tk.stop_fill(100.0, -5.0, [("2026-11-03", bar(95.0, 97.0, 94.0, 96.0))]) == (
        "2026-11-03", 95.0, "gap_open")


def test_a_bar_with_no_low_cannot_fire():
    held = [("2026-11-03", {"Open": 97.0, "High": 99.0, "Low": None, "Close": 90.0}),
            ("2026-11-04", bar(90.0, 91.0, 89.0, 90.5))]
    assert tk.stop_fill(100.0, -5.0, held) == ("2026-11-04", 90.0, "gap_open")


def test_the_entry_day_itself_can_fire():
    """AMD traded 4.61% under its Monday-open entry on 2026-09-28 and did not
    fire; a Monday that goes 5% through does. The stop is from the entry,
    not from the first close."""
    assert tk.stop_fill(100.0, -5.0, [("2026-11-02", bar(100.0, 100.5, 94.9, 96.0))]) == (
        "2026-11-02", 95.0, "stop_level")


def test_the_book_shows_the_stop_to_the_cent():
    # PGR @ $230.66 on 2026-11-02: the exit-shadow template says $219.13.
    assert tk.stop_level(230.66, -5.0) == 219.13
    assert tk.stop_level(105.405, -5.0) == 100.13


# -- booking: every name CORE unless --spec says otherwise ----------------------

def picks(*tickers):
    return {"date": WEEK, "vix": 19.42, "spy_return": None, "fed_stance": "Hold.",
            "picks": [{"ticker": t, "weight": 0.2, "sponsor": "Cecil"} for t in tickers]}


def monday_open(table, symbol, o):
    table[symbol] = {MON: bar(o, o * 1.01, o * 0.99, o)}


def test_open_arms_the_core_stop_and_leaves_a_spec_name_without_one(provider):
    monday_open(provider, "PGR", 230.66)
    monday_open(provider, "ZS", 300.0)
    monday_open(provider, "SPY", 759.45)
    current = tk.open_positions(WEEK, picks("PGR", "ZS"), spec=["zs"])
    by = {p["ticker"]: p for p in current["positions"]}
    assert by["PGR"]["tier"] == "CORE"
    assert by["PGR"]["stop_pct"] == -5.0
    assert by["PGR"]["stop_loss"] == 219.13
    assert by["ZS"]["tier"] == "SPEC"
    assert by["ZS"]["stop_pct"] is None
    assert by["ZS"]["stop_loss"] is None
    on_disk = yaml.safe_load(tk.CURRENT_PATH.read_text(encoding="utf-8"))
    assert [p["tier"] for p in on_disk["positions"]] == ["CORE", "SPEC"]


def test_open_without_spec_books_every_name_core(provider):
    monday_open(provider, "PGR", 230.66)
    monday_open(provider, "SPY", 759.45)
    current = tk.open_positions(WEEK, picks("PGR"))
    assert current["positions"][0]["tier"] == "CORE"


def test_a_spec_name_that_is_not_in_the_book_is_said_and_ignored(provider, capsys):
    monday_open(provider, "PGR", 230.66)
    monday_open(provider, "SPY", 759.45)
    current = tk.open_positions(WEEK, picks("PGR"), spec=["ZS"])
    assert current["positions"][0]["tier"] == "CORE"
    assert "not in this book, ignored: ZS" in capsys.readouterr().out


def test_arm_stops_gives_an_untiered_week_its_stops_and_leaves_a_tiered_one_alone():
    current = {"week": WEEK, "status": "open", "positions": [
        {"ticker": "PGR", "entry_price": 230.66, "stop_loss": None},
        {"ticker": "LIN", "entry_price": 519.78, "stop_loss": None},
        {"ticker": "ZS", "entry_price": 300.0, "tier": "SPEC", "stop_pct": None, "stop_loss": None},
    ]}
    assert tk.arm_stops(current, spec=["LIN"]) == ["PGR", "LIN"]
    by = {p["ticker"]: p for p in current["positions"]}
    assert (by["PGR"]["tier"], by["PGR"]["stop_pct"], by["PGR"]["stop_loss"]) == ("CORE", -5.0, 219.13)
    assert (by["LIN"]["tier"], by["LIN"]["stop_loss"]) == ("SPEC", None)
    assert by["ZS"]["tier"] == "SPEC"
    assert tk.arm_stops(current) == []


# -- closing: the stop is scored on the same snapshot as the entry --------------

def open_book(positions, spy_entry=759.45):
    """A current.yaml as --open writes it, on disk."""
    current = {
        "week": WEEK, "status": "open", "positions": positions,
        "spy_entry": spy_entry, "spy_entry_source": "open",
        "vix_at_entry": 19.42, "fed_stance": "Hold.",
        "total_weight": sum(p["weight"] for p in positions),
        "cash_weight": 1.0 - sum(p["weight"] for p in positions),
    }
    tk.CURRENT_PATH.write_text(yaml.safe_dump(current, sort_keys=False), encoding="utf-8")
    return current


def position(ticker, entry, weight, tier="CORE"):
    return {
        "ticker": ticker, "weight": weight, "sponsor": "Cecil", "thesis": "",
        "entry_price": entry, "entry_date": WEEK, "entry_price_source": "open",
        "tier": tier, "stop_pct": -5.0 if tier == "CORE" else None,
        "stop_loss": tk.stop_level(entry, -5.0) if tier == "CORE" else None,
        "target": None, "direction": "long", "status": "open",
        "exit_price": None, "exit_date": None, "exit_reason": None, "pnl_pct": None,
    }


# A made-up week for a $100 name: down to 94 on Wednesday, back to 101 by
# Friday. Held to Friday it makes +1%; stopped on Wednesday it loses 5%.
ROUND_TRIP = {
    MON: bar(100.0, 101.0, 98.0, 99.0),
    TUE: bar(99.0, 99.5, 96.5, 97.0),
    WED: bar(97.0, 98.0, 94.0, 95.5),
    THU: bar(95.5, 99.0, 95.0, 98.5),
    FRI: bar(98.5, 101.5, 98.0, 101.0),
}
SPY_FLAT = {d: bar(759.45, 760.0, 758.0, 759.45) for d in (MON, TUE, WED, THU, FRI)}


def test_a_core_name_is_stopped_on_the_low_and_a_spec_name_on_the_same_bars_rides(provider):
    provider["CORE"] = ROUND_TRIP
    provider["SPEC"] = ROUND_TRIP
    provider["SPY"] = SPY_FLAT
    open_book([position("CORE", 100.0, 0.5), position("SPEC", 100.0, 0.3, tier="SPEC")])

    closed = tk.close_positions(WEEK)

    by = {p["ticker"]: p for p in closed["positions"]}
    core, spec = by["CORE"], by["SPEC"]
    assert (core["exit_reason"], core["stop_fill"], core["exit_date"]) == (
        "stop_loss", "stop_level", "2026-11-04")
    assert core["exit_price"] == 95.0
    assert core["pnl_pct"] == -5.0
    assert core["return_basis"] == "total_return_same_snapshot"
    assert (spec["exit_reason"], spec["exit_date"], spec["pnl_pct"]) == ("week_end", "2026-11-06", 1.0)
    assert closed["stops_fired"] == ["CORE"]
    # 0.5 * -5.0 + 0.3 * 1.0 = -2.2; the stopped weight sits in cash after Wednesday.
    assert closed["weighted_return"] == -2.2
    assert closed["spy_return"] == 0.0
    assert closed["alpha"] == -2.2
    assert closed["hit_rate"] == 0.5
    assert not tk.CURRENT_PATH.exists()
    archived = yaml.safe_load((tk.HISTORY_DIR / f"{WEEK}.yaml").read_text(encoding="utf-8"))
    assert archived["stops_fired"] == ["CORE"]
    assert archived["positions"][0]["stop_fill"] == "stop_level"


def test_a_gap_through_the_stop_fills_at_the_open(provider):
    week = dict(ROUND_TRIP)
    week[WED] = bar(93.0, 95.0, 92.0, 94.5)  # opens 2% through the $95 stop
    provider["GAP"] = week
    provider["SPY"] = SPY_FLAT
    open_book([position("GAP", 100.0, 0.8)])

    closed = tk.close_positions(WEEK)

    p = closed["positions"][0]
    assert (p["exit_reason"], p["stop_fill"], p["exit_price"], p["pnl_pct"]) == (
        "stop_loss", "gap_open", 93.0, -7.0)


def test_an_ex_dividend_inside_the_week_moves_the_stop_with_the_entry(provider):
    """Booked at $100.00 on Monday. The provider's later snapshot, adjusted for
    a $1 dividend gone ex on Wednesday, shows that same open as $99.00 and
    the Wednesday low as $94.05. Against the stored $95 stop that is a
    touch; against the entry on the same basis ($94.05 is 5% under $99.00
    exactly) it is one too, and the fill is scored on that basis. What the
    rule must not do is mix the two: a $95.00 stored stop and a $94.60 low
    on the adjusted basis would fire a stop the real market never touched."""
    week = {
        MON: bar(99.0, 100.0, 97.0, 98.0),
        TUE: bar(98.0, 98.5, 95.5, 96.0),
        WED: bar(96.0, 97.0, 94.6, 96.5),   # 4.44% under the adjusted entry
        THU: bar(96.5, 99.0, 96.0, 98.5),
        FRI: bar(98.5, 101.0, 98.0, 100.0),
    }
    provider["DIV"] = week
    provider["SPY"] = SPY_FLAT
    open_book([position("DIV", 100.0, 0.8)])

    closed = tk.close_positions(WEEK)

    p = closed["positions"][0]
    assert p["exit_reason"] == "week_end"
    assert p["entry_price_adjusted"] == 99.0
    assert p["pnl_pct"] == round((100.0 - 99.0) / 99.0 * 100, 2)
    assert p["stop_loss"] == 95.0  # what the book showed all week, unchanged


def test_a_week_opened_before_the_rule_is_held_to_friday(provider):
    """portfolio/history/*.yaml before 2026-11-02 carry stop_loss: null and
    no tier. Closing one of those again must not invent a stop."""
    provider["OLD"] = ROUND_TRIP
    provider["SPY"] = SPY_FLAT
    old = position("OLD", 100.0, 0.8)
    for key in ("tier", "stop_pct"):
        del old[key]
    old["stop_loss"] = None
    open_book([old])

    closed = tk.close_positions(WEEK)

    p = closed["positions"][0]
    assert (p["exit_reason"], p["pnl_pct"]) == ("week_end", 1.0)
    assert closed["stops_fired"] == []


def test_the_scorecard_says_which_stop_fired_and_how(provider):
    provider["CORE"] = ROUND_TRIP
    provider["SPY"] = SPY_FLAT
    open_book([position("CORE", 100.0, 0.8)])
    closed = tk.close_positions(WEEK)

    card = tk.generate_scorecard(closed)

    assert "| CORE | 80.0% | Cecil | $100.00 | $95.00 | -5.00% | stop_loss (stop_level, 2026-11-04, stop $95.0) |" in card
    assert "**Stops fired:** CORE" in card


def test_the_committed_book_is_armed():
    """The week open when the rule landed was armed by --arm-stops; every
    position in portfolio/current.yaml, when there is one, has a tier."""
    path = ROOT / "portfolio" / "current.yaml"
    if not path.exists():
        pytest.skip("no week open")
    current = yaml.safe_load(path.read_text(encoding="utf-8"))
    for p in current["positions"]:
        assert p.get("tier") in tk.TIERS, p["ticker"]
        if p["tier"] == "CORE":
            assert p["stop_loss"] == tk.stop_level(p["entry_price"], tk.CORE_STOP_PCT), p["ticker"]
