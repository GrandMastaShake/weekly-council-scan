"""Which session an instrument's close is, and whether it had settled.

Three things went into committed files with no trace, and each is pinned
here from the file that carried it.

2026-08-28.json was fetched on the Saturday at 14:10 UTC and holds
Thursday's 10-year, VIX and dollar index under Friday's date. Most likely
Yahoo had no usable Friday bar for ^TNX, ^VIX or DX-Y.NYB yet and the writer
took "the last bar on or before Friday"; the note that would have said so
was dropped on the way to the file, so it cannot be told from a Friday bar
that carried Thursday's values. The first is what the rule here stops.

2026-09-18.json was fetched at 22:40 ET on the Friday. Its WTI is 95.47, the
November contract's last trade; the settled front month was 100.30 (#110).
Read on the evening of the session, a futures bar is a quote.

And VIX is absent from 2025-03-14 and 2026-03-13, the two Fridays after US
clocks went forward: the fetch window opened on that Sunday, and Yahoo
returns nothing at all for ^VIX when it does.

The rule that replaces "the last bar on or before" is the Treasury path's:
the bar dated as_of or nothing, and a stand-in only when a later bar proves
the date was skipped, with its own date committed beside it.

No network: the provider and the clock are stubbed. The bars for dates that
have happened are the provider's own, as fetched 2026-10-05; files dated
after that are what a future run would write.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ROOT, SCRIPTS, settled_stamp, weekly_doc

import backfill_weekly as bf  # noqa: E402  (conftest stubs the provider)
import daily_observe as do  # noqa: E402
import rebuild_corrections as rc  # noqa: E402
import restate_instruments as ri  # noqa: E402
import truth_check as tc  # noqa: E402
from scan_pipeline import snapshot, snapshot_macro as sm  # noqa: E402

UTC = dt.timezone.utc
D = dt.date

TNX = sm.INSTRUMENTS["rates"]["US10Y"]
WTI = sm.INSTRUMENTS["commodities"]["WTI"]
DXY = sm.INSTRUMENTS["fx"]["DXY"]

FRI = D(2026, 8, 28)
SATURDAY_1410 = dt.datetime(2026, 8, 29, 14, 10, 48, tzinfo=UTC)
LONG_AFTER = dt.datetime(2026, 10, 5, 4, 17, 23, tzinfo=UTC)
STAMP = "2026-10-05T04:17:23Z"

# The provider's bars as fetched 2026-10-05: (date, close, volume).
AUG_WEEK = {
    "^TNX": [(D(2026, 8, 24), 4.704, 0), (D(2026, 8, 25), 4.639, 0),
             (D(2026, 8, 26), 4.664, 0), (D(2026, 8, 27), 4.672, 0),
             (D(2026, 8, 28), 4.72, 0), (D(2026, 8, 31), 4.758, 0)],
    "^VIX": [(D(2026, 8, 26), 15.21, 0), (D(2026, 8, 27), 14.51, 0),
             (D(2026, 8, 28), 14.43, 0), (D(2026, 8, 31), 14.92, 0)],
    "DX-Y.NYB": [(D(2026, 8, 26), 99.17, 0), (D(2026, 8, 27), 99.16, 0),
                 (D(2026, 8, 28), 99.70, 0), (D(2026, 8, 31), 99.43, 0)],
    "CL=F": [(D(2026, 8, 27), 83.53, 220113), (D(2026, 8, 28), 83.40, 167615),
             (D(2026, 8, 31), 85.76, 235761)],
}


# 2025-07-04: Globex printed a short holiday session, the Cboe indices and
# the dollar index printed nothing. 2025-07-04.json is the one committed
# file whose instruments come from two different sessions.
JULY_4TH = {
    "^TNX": [(D(2025, 7, 2), 4.293, 0), (D(2025, 7, 3), 4.348, 0),
             (D(2025, 7, 7), 4.395, 0)],
    "^VIX": [(D(2025, 7, 2), 16.64, 0), (D(2025, 7, 3), 16.38, 0),
             (D(2025, 7, 7), 17.79, 0)],
    "DX-Y.NYB": [(D(2025, 7, 2), 96.78, 0), (D(2025, 7, 3), 97.18, 0),
                 (D(2025, 7, 7), 97.48, 0)],
    "CL=F": [(D(2025, 7, 2), 67.45, 265200), (D(2025, 7, 3), 67.0, 0),
             (D(2025, 7, 4), 66.5, 0), (D(2025, 7, 7), 67.93, 332949)],
}


def without(rows, *days):
    return [r for r in rows if r[0] not in days]


class Frame:
    """What Ticker.history returns, as far as _fetch_one looks at it."""

    def __init__(self, rows):
        self.rows = rows

    @property
    def empty(self):
        return not self.rows

    def iterrows(self):
        for day, close, volume in self.rows:
            yield (dt.datetime(day.year, day.month, day.day),
                   {"Close": close, "Volume": volume})


@pytest.fixture
def provider(monkeypatch):
    """Stub yfinance and the clock. Returns (table, calls): set
    table[symbol] to a list of bars or to an exception."""
    table, calls = {}, []

    class Ticker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, start=None, end=None):
            calls.append((self.symbol, start, end))
            rows = table.get(self.symbol, [])
            if isinstance(rows, Exception):
                raise rows
            return Frame([r for r in rows
                          if start <= r[0].isoformat() < end])

    monkeypatch.setattr(sm.yf, "Ticker", Ticker, raising=False)
    monkeypatch.setattr(sm, "_utcnow", lambda: LONG_AFTER)
    return table, calls


def days(rows):
    return {r[0] for r in rows}


# -- the bar dated as_of, or nothing -------------------------------------------

def test_the_bar_dated_as_of_is_the_observation():
    got = sm.select_bar(days(AUG_WEEK["^TNX"]), FRI, TNX, LONG_AFTER)
    assert got == (FRI, None)


def test_a_friday_with_no_bar_yet_is_missing_and_thursday_is_not_used():
    """2026-08-29, 14:10 UTC, as it was: nothing dated the 28th, nothing
    after it. The old writer answered 4.672. A missing bar is not evidence
    of a holiday, so the answer is no value and the reason."""
    seen = days(without(AUG_WEEK["^TNX"], FRI, D(2026, 8, 31)))
    observed, err = sm.select_bar(seen, FRI, TNX, SATURDAY_1410)
    assert observed is None
    assert "no bar dated 2026-08-28, and none after it yet" in err
    assert "no earlier session is substituted" in err


def test_a_later_bar_proves_the_date_was_skipped_and_the_week_stands_in():
    """Good Friday 2026. The backfill ran months later, with the following
    Monday's bar in hand: the 3rd was skipped, and the 2nd stands in."""
    seen = {D(2026, 3, 30), D(2026, 3, 31), D(2026, 4, 1), D(2026, 4, 2),
            D(2026, 4, 6)}
    assert sm.select_bar(seen, D(2026, 4, 3), TNX, LONG_AFTER) == (
        D(2026, 4, 2), None)


def test_a_stand_in_never_comes_from_an_earlier_week():
    """A Monday holiday has no earlier day in its week. Last Friday's close
    under Monday's date would be a week-old value in a daily file."""
    seen = {D(2026, 10, 9), D(2026, 10, 13)}
    observed, err = sm.select_bar(seen, D(2026, 10, 12), TNX, LONG_AFTER)
    assert observed is None
    assert "its week has no earlier bar to stand in" in err


# -- a bar the exchange has not settled ----------------------------------------

@pytest.mark.parametrize("now,readable", [
    (dt.datetime(2026, 9, 18, 22, 14, tzinfo=UTC), False),   # Fri 18:14 ET
    (dt.datetime(2026, 9, 19, 2, 40, tzinfo=UTC), False),    # Fri 22:40 ET
    (dt.datetime(2026, 9, 19, 12, 59, tzinfo=UTC), False),
    (dt.datetime(2026, 9, 19, 13, 0, tzinfo=UTC), True),
    (dt.datetime(2026, 9, 19, 13, 7, tzinfo=UTC), True),     # Sat 09:07 ET
])
def test_a_futures_bar_is_not_read_before_it_settles(now, readable):
    """02:40 UTC is when 2026-09-18.json was fetched, and its WTI is 95.47
    against a settled 100.30. 13:07 UTC is the earliest read on file, and
    WTI was right in all five files read from then on."""
    day = D(2026, 9, 18)
    observed, err = sm.select_bar({D(2026, 9, 17), day}, day, WTI, now)
    if readable:
        assert (observed, err) == (day, None)
    else:
        assert observed is None
        assert "CL=F: the bar dated 2026-09-18 is a quote" in err
        assert "not read before 2026-09-19T13:00Z" in err


def test_the_cboe_indices_are_final_the_same_evening():
    """^TNX and ^VIX were right in all eleven evening files. Holding them
    back to Saturday would cost a 10-year for nothing."""
    evening = dt.datetime(2026, 9, 18, 22, 14, tzinfo=UTC)
    day = D(2026, 9, 18)
    assert sm.select_bar({day}, day, TNX, evening) == (day, None)
    assert sm.select_bar({day}, day, sm.INSTRUMENTS["vol"]["VIX"],
                         evening) == (day, None)


def test_exactly_the_instruments_that_trade_past_the_close_wait():
    late = {(block, ticker)
            for block, instruments in sm.INSTRUMENTS.items()
            for ticker, cfg in instruments.items()
            if cfg.get("settles") == sm.NEXT_DAY}
    assert late == {("rates", "US2Y_FUT"), ("commodities", "WTI"),
                    ("commodities", "GOLD"), ("commodities", "SILVER"),
                    ("fx", "DXY")}


def test_the_gate_and_the_writer_agree_on_who_waits_and_until_when():
    """truth_check stays stdlib-only, so it repeats the list. A repeat that
    drifts is a gate enforcing last month's rule."""
    late = {block: tuple(t for t, cfg in instruments.items()
                         if cfg.get("settles") == sm.NEXT_DAY)
            for block, instruments in sm.INSTRUMENTS.items()}
    assert {b: t for b, t in late.items() if t} == tc.LATE_SETTLING
    assert tc.SETTLED_HOUR_UTC == sm.SETTLED_HOUR_UTC
    assert sm.settled_at(D(2026, 9, 18)) == dt.datetime(
        2026, 9, 19, 13, 0, tzinfo=UTC)


# -- the fetch -----------------------------------------------------------------

def test_the_window_opens_on_the_weeks_monday_never_the_sunday(provider):
    """Friday minus five days is the Sunday the clocks go forward once a
    year. Yahoo answers that window with nothing for ^VIX, and VIX is
    absent from both committed files where it happened."""
    table, calls = provider
    table["^VIX"] = [(D(2025, 3, 13), 24.66, 0), (D(2025, 3, 14), 21.77, 0)]
    entry, err = sm._fetch_one("VIX", sm.INSTRUMENTS["vol"]["VIX"],
                               D(2025, 3, 14))
    assert (entry, err) == ({"close": 21.77, "volume": None}, None)
    assert calls == [("^VIX", "2025-03-10", "2025-03-22")]

    for friday in (D(2026, 3, 13), D(2027, 3, 19), D(2026, 10, 9)):
        sm._fetch_one("VIX", sm.INSTRUMENTS["vol"]["VIX"], friday)
        start = dt.date.fromisoformat(calls[-1][1])
        assert start.weekday() == 0 and start <= friday


def test_an_ordinary_bar_carries_no_observed_and_no_note(provider):
    table, _ = provider
    table.update(AUG_WEEK)
    entry, err = sm._fetch_one("US10Y", TNX, FRI)
    assert err is None
    assert entry == {"close": 4.72, "volume": None}


def test_a_stand_in_says_which_session_it_is(provider):
    """July 4th 2025. The futures printed a short session; ^TNX did not."""
    table, _ = provider
    table["^TNX"] = JULY_4TH["^TNX"]
    table["CL=F"] = JULY_4TH["CL=F"]
    entry, err = sm._fetch_one("US10Y", TNX, D(2025, 7, 4))
    assert err is None
    assert entry["close"] == 4.348
    assert entry["observed"] == "2025-07-03"
    assert "2025-07-04" in entry["note"] and "2025-07-03" in entry["note"]

    crude, err = sm._fetch_one("WTI", WTI, D(2025, 7, 4))
    assert (crude, err) == ({"close": 66.5, "volume": None}, None)


def test_a_nan_bar_is_not_a_bar(provider):
    """A row with no close would otherwise be 'the bar dated as_of' and go
    into the file as NaN."""
    table, _ = provider
    table["^TNX"] = without(AUG_WEEK["^TNX"], FRI) + [(FRI, float("nan"), 0)]
    entry, err = sm._fetch_one("US10Y", TNX, FRI)
    assert err is None
    assert entry["observed"] == "2026-08-27"
    assert entry["close"] == 4.672


def test_an_evening_read_of_crude_is_missing_with_the_reason(
        provider, monkeypatch):
    table, _ = provider
    table["CL=F"] = [(D(2026, 9, 17), 101.91, 265972),
                     (D(2026, 9, 18), 95.47, 300567)]
    monkeypatch.setattr(sm, "_utcnow", lambda: dt.datetime(
        2026, 9, 19, 2, 40, 26, tzinfo=UTC))
    entry, err = sm._fetch_one("WTI", WTI, D(2026, 9, 18))
    assert entry is None
    assert "is a quote until the exchange settlement is loaded" in err


def test_a_dead_symbol_does_not_end_the_batch(provider):
    table, _ = provider
    table["^TNX"] = OSError("timed out")
    assert sm._fetch_one("US10Y", TNX, FRI) == (None, "OSError: timed out")
    table["^TNX"] = []
    entry, err = sm._fetch_one("US10Y", TNX, FRI)
    assert entry is None and err.startswith("no data returned for window")


def test_normalization_is_one_function(provider):
    assert sm.normalize_bar(47.2, 0, TNX) == (4.72, None)
    assert sm.normalize_bar(83.4, 167615.0, WTI) == (83.4, 167615)
    assert sm.normalize_bar(4529.89990234375, float("nan"), WTI) == (
        4529.8999, None)


# -- what reaches the caller, and the file -------------------------------------

@pytest.fixture
def treasury_quiet(monkeypatch):
    """US2Y is not this file's subject; give it a fixed Treasury answer."""
    monkeypatch.setattr(sm, "_fetch_treasury", lambda ticker, cfg, day: (
        {"close": 4.83, "volume": None},
        {"source": "treasury", "fetched_at": STAMP}, None))


def test_a_stand_in_is_named_in_provenance_and_only_a_stand_in(
        provider, treasury_quiet):
    table, _ = provider
    table.update(JULY_4TH)
    got = sm.fetch_special_instruments("2025-07-04")

    assert got["rates"]["US10Y"] == {
        "close": 4.348, "volume": None,
        "note": "^TNX printed nothing on 2025-07-04; used 2025-07-03, the "
                "last bar of that week"}
    assert got["provenance"]["rates"]["US10Y"] == {
        "source": "yahoo", "fetched_at": STAMP, "observed": "2025-07-03"}
    assert got["provenance"]["vol"]["VIX"]["observed"] == "2025-07-03"
    assert got["provenance"]["fx"]["DXY"]["observed"] == "2025-07-03"
    assert got["commodities"]["WTI"] == {"close": 66.5, "volume": None}
    assert "commodities" not in got["provenance"], (
        "an instrument read for the date asked has no entry")


def test_the_saturday_of_2026_08_29_as_the_writer_now_answers_it(
        provider, treasury_quiet, monkeypatch):
    """The three index symbols have no Friday bar; crude does. Before, the
    file got 4.672, 14.51 and 99.16 with nothing to say they were
    Thursday's. Now it gets three reasons."""
    table, _ = provider
    for symbol in ("^TNX", "^VIX", "DX-Y.NYB"):
        table[symbol] = without(AUG_WEEK[symbol], FRI, D(2026, 8, 31))
    table["CL=F"] = without(AUG_WEEK["CL=F"], D(2026, 8, 31))
    monkeypatch.setattr(sm, "_utcnow", lambda: SATURDAY_1410)
    got = sm.fetch_special_instruments("2026-08-28")

    assert "US10Y" not in got["rates"]
    assert got["vol"] == {} and got["fx"] == {}
    assert got["commodities"]["WTI"] == {"close": 83.4, "volume": 167615}
    lost = {m["ticker"]: m["reason"] for m in got["missing"]}
    assert set(lost) >= {"US10Y", "VIX", "DXY"}
    assert all("none after it yet" in lost[t] for t in ("US10Y", "VIX", "DXY"))
    assert set(got["provenance"]) == {"rates"}, "only Treasury's US2Y"


def test_the_stand_in_date_reaches_the_committed_weekly_file(
        provider, treasury_quiet, tmp_path):
    table, _ = provider
    table["^TNX"] = [(D(2026, 4, 2), 4.313, 0), (D(2026, 4, 6), 4.335, 0)]
    special = sm.fetch_special_instruments("2026-04-03")
    # The equities of a Good Friday file are Thursday's too, by the same
    # proof, and a weekly file is not written without its SPY bar at all
    # (tests/test_weekly_session.py).
    thursday = {"bars": {"SPY": {"close": 655.0, "volume": 1}},
                "missing": [], "session": "2026-04-02"}
    path = snapshot.write_weekly("2026-04-03", thursday, special,
                                 out_dir=str(tmp_path))
    doc = json.loads(Path(path).read_text(encoding="utf-8"))

    assert doc["session_note"] == "Friday holiday; bars from 2026-04-02"
    assert doc["source"] == "yahoo", "sector-regime-heatmap reads this"
    assert doc["rates"]["US10Y"] == {"close": 4.313, "volume": None}
    assert doc["provenance"]["rates"]["US10Y"] == {
        "source": "yahoo", "fetched_at": STAMP, "observed": "2026-04-02"}
    assert "series" not in doc["provenance"], (
        "check_basis() refuses a provenance.series source it does not know")
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    (tmp_path / "weekly").rename(repo / "data" / "weekly")
    assert fails(repo) == []


def test_the_daily_file_carries_it_the_same_way():
    special = {"rates": {"US10Y": {"close": 4.313, "volume": None}},
               "vol": {}, "commodities": {}, "fx": {}, "missing": [],
               "provenance": {"rates": {"US10Y": {
                   "source": "yahoo", "fetched_at": STAMP,
                   "observed": "2026-04-02"}}}}
    bars = {"bars": {"SPY": {"close": 668.0, "volume": 1}}, "missing": []}
    doc = do.build_document("2026-04-03", bars, special)
    assert doc["source"] == "yahoo-daily"
    assert doc["provenance"]["rates"]["US10Y"]["observed"] == "2026-04-02"


def test_a_rewritten_holiday_week_stamps_its_stand_ins_as_backfill(
        tmp_path, monkeypatch):
    """backfill_weekly --force writes the week, then restamps the file as a
    backfill. A stand-in's label names the file's own provider, so it takes
    the same identity; Treasury's label is not the backfill's to restamp.
    SPY's bar on the Monday after is what lets Thursday stand in at all."""
    special = {
        "rates": {"US10Y": {"close": 4.313, "volume": None},
                  "US2Y": {"close": 3.84, "volume": None}},
        "vol": {}, "commodities": {}, "fx": {}, "missing": [],
        "provenance": {"rates": {
            "US10Y": {"source": "yahoo", "fetched_at": STAMP,
                      "observed": "2026-04-02"},
            "US2Y": {"source": "treasury", "fetched_at": STAMP}}}}
    monkeypatch.setattr(bf.snapshot_macro, "fetch_special_instruments",
                        lambda friday: special)
    monkeypatch.setattr(bf.time, "sleep", lambda s: None)

    rec = bf.build_and_write(D(2026, 4, 3), ["SPY"],
                             {"SPY": ([D(2026, 4, 2), D(2026, 4, 6)],
                                      [655.0, 658.9], [1, 1])},
                             str(tmp_path))
    doc = json.loads(Path(rec["path"]).read_text(encoding="utf-8"))
    assert doc["session_note"] == "Friday holiday; bars from 2026-04-02"
    assert doc["source"] == bf.BACKFILL_SOURCE == "yahoo-backfill"
    assert doc["provenance"]["rates"]["US10Y"] == {
        "source": "yahoo-backfill", "fetched_at": bf.RUN_TS,
        "observed": "2026-04-02"}
    assert doc["provenance"]["rates"]["US2Y"] == {
        "source": "treasury", "fetched_at": STAMP}


# -- the gate: read before it settled ------------------------------------------

def fails(repo, subdir="weekly"):
    rep = tc.Report()
    tc.check_feed(repo, rep, subdir=subdir,
                  require_friday=(subdir == "weekly"), label=subdir)
    return [line for line in rep.lines if line.startswith("FAIL")]


def week(as_of, fetched_at=None, **blocks):
    doc = weekly_doc(as_of, ["SPY"], fetched_at=fetched_at)
    for block, closes in blocks.items():
        doc[block] = {t: {"close": c, "volume": None}
                      for t, c in closes.items()}
    return doc


def test_the_gate_refuses_a_futures_close_read_on_friday_evening(panel):
    """What a runner still on the old writer pushes: the Friday job at
    21:13 ET, crude and all. Its own fetch time is the evidence."""
    repo = panel({"2026-10-09.json": week(
        "2026-10-09", fetched_at="2026-10-10T01:13:42Z",
        rates={"US10Y": 5.2}, commodities={"WTI": 90.0},
        fx={"DXY": 102.0})}).parents[1]
    got = fails(repo)
    assert len(got) == 2
    assert "commodities.WTI was read at 2026-10-10T01:13:42Z, before " \
           "2026-10-10T13:00Z" in got[0]
    assert "fx.DXY" in got[1]
    assert not any("US10Y" in line for line in got)


def test_the_gate_accepts_the_same_file_read_on_saturday_morning(panel):
    repo = panel({"2026-10-09.json": week(
        "2026-10-09", fetched_at="2026-10-10T13:07:47Z",
        commodities={"WTI": 90.0}, fx={"DXY": 102.0})}).parents[1]
    assert fails(repo) == []


def test_the_eleven_files_written_before_the_rule_are_not_failed(panel):
    """They cannot be edited. macro/instrument_audit.json lists them."""
    repo = panel({"2026-09-18.json": week(
        "2026-09-18", fetched_at="2026-09-19T02:40:26Z",
        commodities={"WTI": 95.47})}).parents[1]
    assert fails(repo) == []
    assert tc.SETTLEMENT_RULE_SINCE == "2026-10-05"


def test_an_unlabelled_us2y_is_the_future_and_waits_like_one(panel):
    """A stale runner still files 2YY=F under US2Y. No Treasury label, so
    it is the future, read on the evening."""
    stale = week("2026-10-09", fetched_at="2026-10-10T01:13:42Z",
                 rates={"US2Y": 4.61})
    got = fails(panel({"2026-10-09.json": stale}).parents[1])
    assert len(got) == 1 and "rates.US2Y was read at" in got[0]


def test_the_treasury_2_year_does_not_wait(panel):
    """Treasury posts the day's curve that evening, and it is final."""
    doc = week("2026-10-09", fetched_at="2026-10-10T01:13:42Z",
               rates={"US2Y": 4.83})
    doc["provenance"] = {"rates": {"US2Y": {
        "source": "treasury", "fetched_at": "2026-10-10T01:13:42Z"}}}
    assert fails(panel({"2026-10-09.json": doc}).parents[1]) == []


def test_an_instruments_own_label_is_the_fetch_time_that_counts(panel):
    """A close restated later was read later, whatever the file's stamp."""
    doc = week("2026-10-09", fetched_at="2026-10-10T01:13:42Z",
               commodities={"WTI": 90.0})
    doc["provenance"] = {"commodities": {"WTI": {
        "source": "yahoo-backfill", "fetched_at": "2026-10-14T15:00:00Z"}}}
    assert fails(panel({"2026-10-09.json": doc}).parents[1]) == []


def test_a_stand_in_is_judged_against_the_session_it_is(panel):
    """Thursday's settled bar, read on the Saturday of a holiday week."""
    doc = week("2026-12-25", fetched_at="2026-12-26T01:13:42Z",
               commodities={"WTI": 88.0})
    doc["provenance"] = {"commodities": {"WTI": {
        "source": "yahoo", "fetched_at": "2026-12-26T01:13:42Z",
        "observed": "2026-12-24"}}}
    assert fails(panel({"2026-12-25.json": doc}).parents[1]) == []


def test_the_gate_holds_a_daily_file_to_the_same_rule(tmp_path):
    doc = week("2026-10-06", fetched_at="2026-10-06T23:41:42Z",
               commodities={"WTI": 89.63})
    doc["cadence"] = "daily"
    doc["source"] = "yahoo-daily"
    daily = tmp_path / "data" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-10-06.json").write_text(json.dumps(doc), encoding="utf-8")
    got = fails(tmp_path, "daily")
    assert len(got) == 1 and "commodities.WTI was read at" in got[0]


# -- the gate: what a correction restated --------------------------------------

LABEL = {"source": "yahoo-backfill", "fetched_at": STAMP}
REASON = ("US10Y, VIX and DXY held the 2026-08-27 close: the provider had "
          "no bar dated 2026-08-28 for its index symbols when the file was "
          "fetched.")


def august_28():
    """2026-08-28.json's instrument blocks, as committed."""
    doc = weekly_doc("2026-08-28", ["SPY", "AAPL"],
                     fetched_at="2026-08-29T14:10:48Z")
    doc["rates"] = {"US10Y": {"close": 4.672, "volume": None},
                    "US2Y": {"close": 4.17, "volume": None}}
    doc["vol"] = {"VIX": {"close": 14.51, "volume": None}}
    doc["commodities"] = {"WTI": {"close": 83.4, "volume": 142318}}
    doc["fx"] = {"DXY": {"close": 99.16, "volume": None}}
    return doc


def restated_correction(base):
    """What restate_instruments.py writes for the three index closes."""
    doc = json.loads(json.dumps(base))
    doc["rates"]["US10Y"]["close"] = 4.72
    doc["vol"]["VIX"]["close"] = 14.43
    doc["fx"]["DXY"]["close"] = 99.7
    doc["provenance"] = {"rates": {"US10Y": dict(LABEL)},
                         "vol": {"VIX": dict(LABEL)},
                         "fx": {"DXY": dict(LABEL)}}
    doc["restated"] = [
        {"block": "rates", "ticker": "US10Y",
         "was": {"close": 4.672, "volume": None}},
        {"block": "vol", "ticker": "VIX",
         "was": {"close": 14.51, "volume": None}},
        {"block": "fx", "ticker": "DXY",
         "was": {"close": 99.16, "volume": None}},
    ]
    doc["corrects"] = "2026-08-28.json"
    doc["reason"] = REASON
    return doc


def corrected_panel(panel, mutate=None, base=None):
    base = base or august_28()
    fixed = restated_correction(august_28())
    if mutate:
        mutate(fixed)
    weekly = panel({"2026-08-28.json": base,
                    "2026-08-28.corrected.json": fixed})
    return weekly.parents[1], weekly


def test_the_gate_accepts_a_correction_that_records_what_it_restated(panel):
    repo, _ = corrected_panel(panel)
    assert fails(repo) == []


def test_the_gate_refuses_a_changed_close_nobody_recorded(panel):
    def sneak(doc):
        doc["commodities"]["WTI"]["close"] = 84.0

    repo, _ = corrected_panel(panel, sneak)
    got = fails(repo)
    assert len(got) == 1
    assert "commodities.WTI" in got[0]
    assert "'restated' does not record the change" in got[0]


def test_the_gate_refuses_a_restated_close_with_no_label(panel):
    """Fetched in October, sitting under an August stamp."""
    def unlabel(doc):
        del doc["provenance"]["vol"]

    repo, _ = corrected_panel(panel, unlabel)
    got = fails(repo)
    assert len(got) == 1
    assert "vol.VIX is restated but carries no provenance.vol.VIX label" \
        in got[0]


def test_the_gate_refuses_a_correction_whose_base_moved_under_it(panel):
    base = august_28()
    base["rates"]["US10Y"]["close"] = 4.70
    repo, _ = corrected_panel(panel, base=base)
    got = fails(repo)
    assert len(got) == 1
    assert "says the base held 4.672, but it holds 4.7" in got[0]


def test_the_gate_refuses_a_restatement_that_restates_nothing(panel):
    def undo(doc):
        doc["fx"]["DXY"]["close"] = 99.16

    repo, _ = corrected_panel(panel, undo)
    assert any("equals its base; it restates nothing" in line
               for line in fails(repo))


def test_the_gate_refuses_an_instrument_added_or_dropped(panel):
    """rebuild_corrections.py copies the base and re-applies what is on
    record. An edit it has no record of is one the next rebuild erases."""
    def add(doc):
        doc["commodities"]["GOLD"] = {"close": 4529.9, "volume": 1}

    def drop(doc):
        del doc["commodities"]["WTI"]

    for change, side in ((add, "the correction"), (drop, "its base")):
        repo, weekly = corrected_panel(panel, change)
        got = fails(repo)
        assert len(got) == 1 and "is only in " + side in got[0]
        for path in weekly.glob("*.json"):
            path.unlink()


@pytest.mark.parametrize("bad", [
    [], "rates.US10Y", [{"block": "series", "ticker": "AAPL",
                         "was": {"close": 1.0}}],
    [{"block": "rates", "ticker": "US10Y", "was": {"close": "4.672"}}],
])
def test_the_gate_refuses_a_restated_record_it_cannot_read(panel, bad):
    def spoil(doc):
        doc["restated"] = bad

    repo, _ = corrected_panel(panel, spoil)
    assert any("'restated'" in line for line in fails(repo))


def test_the_gate_refuses_a_record_for_an_instrument_that_is_not_there(panel):
    def ghost(doc):
        doc["restated"].append({"block": "rates", "ticker": "US30Y",
                                "was": {"close": 5.0, "volume": None}})

    repo, _ = corrected_panel(panel, ghost)
    assert any("'restated' names rates.US30Y" in line for line in fails(repo))


def test_a_correction_that_only_drops_a_bar_needs_no_restated(panel):
    """The AVB correction, which predates all of this."""
    base = august_28()
    base["series"]["AVB"] = {"close": 65.9005, "volume": 0}
    fixed = json.loads(json.dumps(base))
    fixed["series"].pop("AVB")
    fixed["missing"] = [{"ticker": "AVB",
                         "reason": "zero-volume bar, close 65.9005"}]
    fixed["corrects"] = "2026-08-28.json"
    fixed["reason"] = "AVB printed behind zero volume"
    repo = panel({"2026-08-28.json": base,
                  "2026-08-28.corrected.json": fixed}).parents[1]
    assert fails(repo) == []


# -- rebuilding a correction that restates -------------------------------------

def run_rebuild(weekly):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "rebuild_corrections.py"),
         "--dir", str(weekly)], capture_output=True, text=True)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_a_rebuild_keeps_the_restated_closes_and_brings_in_the_new_names(
        panel):
    """The correction trap, for the new kind of edit. A backfill adds PLTR
    to the base behind the correction's back; the rebuilt correction has
    PLTR and still has Friday's 10-year."""
    _, weekly = corrected_panel(panel)
    base = read(weekly / "2026-08-28.json")
    base["series"]["PLTR"] = {"close": 10.0, "volume": 5}
    base["provenance"] = {"series": {"PLTR": dict(LABEL)}}
    (weekly / "2026-08-28.json").write_text(json.dumps(base),
                                            encoding="utf-8")

    r = run_rebuild(weekly)
    assert r.returncode == 0
    assert "restated rates.US10Y, vol.VIX, fx.DXY" in r.stdout

    after = read(weekly / "2026-08-28.corrected.json")
    assert "PLTR" in after["series"]
    assert after["rates"]["US10Y"]["close"] == 4.72
    assert after["vol"]["VIX"]["close"] == 14.43
    assert after["fx"]["DXY"]["close"] == 99.7
    assert after["rates"]["US2Y"] == base["rates"]["US2Y"]
    assert after["provenance"] == {
        "series": {"PLTR": LABEL}, "rates": {"US10Y": LABEL},
        "vol": {"VIX": LABEL}, "fx": {"DXY": LABEL}}
    assert len(after["restated"]) == 3
    assert after["corrects"] == "2026-08-28.json"
    assert after["reason"] == REASON
    assert fails(weekly.parents[1]) == []


def test_a_rebuild_is_a_no_op_on_a_correction_that_is_current(panel):
    _, weekly = corrected_panel(panel)
    assert run_rebuild(weekly).returncode == 0
    once = (weekly / "2026-08-28.corrected.json").read_bytes()
    assert run_rebuild(weekly).returncode == 0
    assert (weekly / "2026-08-28.corrected.json").read_bytes() == once


def test_a_rebuild_aborts_when_the_base_no_longer_holds_what_was_replaced(
        panel):
    """Someone rewrote the week, or the provider restated. Re-applying 4.72
    over a number nobody reviewed would be a guess."""
    _, weekly = corrected_panel(panel)
    base = read(weekly / "2026-08-28.json")
    base["rates"]["US10Y"]["close"] = 4.70
    (weekly / "2026-08-28.json").write_text(json.dumps(base),
                                            encoding="utf-8")
    before = (weekly / "2026-08-28.corrected.json").read_bytes()

    r = run_rebuild(weekly)
    assert "ABORT 2026-08-28.corrected.json: rates.US10Y is 4.7 in the " \
           "base, not the 4.672 this correction replaced" in r.stdout
    assert r.returncode == 1, "a backfill must not commit past this"
    assert (weekly / "2026-08-28.corrected.json").read_bytes() == before


def test_an_abort_on_a_dropped_bar_fails_the_run_too(panel):
    """It printed ABORT and exited 0, so the backfill workflow went on to
    its commit step with a correction that no longer matched its base."""
    base = august_28()
    base["series"]["AVB"] = {"close": 184.06, "volume": 2_000_000}
    fixed = august_28()
    fixed["missing"] = [{"ticker": "AVB",
                         "reason": "zero-volume bar, close 65.9005"}]
    fixed["corrects"] = "2026-08-28.json"
    fixed["reason"] = "AVB printed behind zero volume"
    weekly = panel({"2026-08-28.json": base,
                    "2026-08-28.corrected.json": fixed})
    r = run_rebuild(weekly)
    assert "ABORT" in r.stdout and r.returncode == 1


def test_one_correction_can_carry_both_kinds_of_edit(panel):
    base = august_28()
    base["series"]["AVB"] = {"close": 65.9005, "volume": 0}
    fixed = restated_correction(base)
    fixed["series"].pop("AVB")
    fixed["missing"] = [{"ticker": "AVB",
                         "reason": "zero-volume bar, close 65.9005"}]
    weekly = panel({"2026-08-28.json": base,
                    "2026-08-28.corrected.json": fixed})
    r = run_rebuild(weekly)
    assert r.returncode == 0
    assert "dropped AVB; restated rates.US10Y" in r.stdout
    after = read(weekly / "2026-08-28.corrected.json")
    assert "AVB" not in after["series"]
    assert after["rates"]["US10Y"]["close"] == 4.72
    assert fails(weekly.parents[1]) == []


def test_a_correction_with_no_edit_on_record_is_skipped_not_emptied(panel):
    fixed = august_28()
    fixed["corrects"] = "2026-08-28.json"
    fixed["reason"] = "nothing recorded"
    weekly = panel({"2026-08-28.json": august_28(),
                    "2026-08-28.corrected.json": fixed})
    before = (weekly / "2026-08-28.corrected.json").read_bytes()
    r = run_rebuild(weekly)
    assert r.returncode == 0 and "skip" in r.stdout
    assert (weekly / "2026-08-28.corrected.json").read_bytes() == before


# -- writing the correction ----------------------------------------------------

def fetcher(closes, observed=None, err=None):
    """Stands in for snapshot_macro._fetch_one."""
    def fetch(ticker, cfg, day):
        if err and ticker in err:
            return None, err[ticker]
        entry = {"close": closes[ticker], "volume": None}
        if observed and ticker in observed:
            entry["observed"] = observed[ticker]
        return entry, None
    return fetch


FRIDAY_CLOSES = {"US10Y": 4.72, "VIX": 14.43, "DXY": 99.7}
THREE = ["rates.US10Y", "vol.VIX", "fx.DXY"]


def test_the_tool_writes_the_correction_and_leaves_the_base_alone(panel):
    weekly = panel({"2026-08-28.json": august_28()})
    base_bytes = (weekly / "2026-08-28.json").read_bytes()

    doc = ri.restate(weekly, "2026-08-28", THREE, REASON,
                     fetch=fetcher(FRIDAY_CLOSES), now=LONG_AFTER)

    assert (weekly / "2026-08-28.json").read_bytes() == base_bytes
    on_disk = read(weekly / "2026-08-28.corrected.json")
    assert on_disk == doc == restated_correction(august_28())
    assert on_disk["fetched_at"] == "2026-08-29T14:10:48Z", (
        "the file-level stamp still describes everything that was not "
        "restated")
    raw = (weekly / "2026-08-28.corrected.json").read_bytes()
    raw.decode("ascii")
    assert b"\r\n" not in raw and raw.endswith(b"\n")
    assert fails(weekly.parents[1]) == []


def test_rebuilding_what_the_tool_wrote_changes_nothing(panel):
    weekly = panel({"2026-08-28.json": august_28()})
    ri.restate(weekly, "2026-08-28", THREE, REASON,
               fetch=fetcher(FRIDAY_CLOSES), now=LONG_AFTER)
    written = (weekly / "2026-08-28.corrected.json").read_bytes()
    assert run_rebuild(weekly).returncode == 0
    assert (weekly / "2026-08-28.corrected.json").read_bytes() == written


def test_readers_get_the_restated_closes(panel):
    weekly = panel({"2026-08-28.json": august_28()})
    ri.restate(weekly, "2026-08-28", THREE, REASON,
               fetch=fetcher(FRIDAY_CLOSES), now=LONG_AFTER)
    (_, doc), = snapshot._load_weekly_files(str(weekly))
    assert doc["rates"]["US10Y"]["close"] == 4.72
    assert doc["fx"]["DXY"]["close"] == 99.7


@pytest.mark.parametrize("names,fetch,why", [
    (THREE, fetcher(FRIDAY_CLOSES, observed={"VIX": "2026-08-27"}),
     "That is a stand-in, not the close for the date"),
    (THREE, fetcher(dict(FRIDAY_CLOSES, DXY=99.16)),
     "fx.DXY is already 99.16"),
    (THREE, fetcher(FRIDAY_CLOSES, err={"US10Y": "OSError: timed out"}),
     "rates.US10Y: OSError: timed out"),
    (["rates.US2Y"], fetcher({}), "does not come from yahoo"),
    (["rates.US30Y"], fetcher({}), "is not a special instrument"),
    (["series.AAPL"], fetcher({}), "is not a special instrument"),
    (["commodities.GOLD"], fetcher({"GOLD": 4529.9}), "has no close in"),
    (["vol.VIX", "vol.VIX"], fetcher(FRIDAY_CLOSES), "named twice"),
    ([], fetcher(FRIDAY_CLOSES), "no instrument named"),
])
def test_one_refusal_writes_nothing(panel, names, fetch, why):
    """A correction is one reviewed statement about one file, not whichever
    parts of it happened to fetch."""
    weekly = panel({"2026-08-28.json": august_28()})
    with pytest.raises(ri.Refused, match=why):
        ri.restate(weekly, "2026-08-28", names, REASON, fetch=fetch,
                   now=LONG_AFTER)
    assert not (weekly / "2026-08-28.corrected.json").exists()


def test_the_tool_refuses_without_a_reason_or_over_an_existing_correction(
        panel):
    weekly = panel({"2026-08-28.json": august_28()})
    with pytest.raises(ri.Refused, match="needs a reason"):
        ri.restate(weekly, "2026-08-28", THREE, "  ",
                   fetch=fetcher(FRIDAY_CLOSES), now=LONG_AFTER)
    ri.restate(weekly, "2026-08-28", THREE, REASON,
               fetch=fetcher(FRIDAY_CLOSES), now=LONG_AFTER)
    with pytest.raises(ri.Refused, match="already exists"):
        ri.restate(weekly, "2026-08-28", ["rates.US10Y"], REASON,
                   fetch=fetcher(FRIDAY_CLOSES), now=LONG_AFTER)


def test_a_dry_run_writes_nothing(panel):
    weekly = panel({"2026-08-28.json": august_28()})
    doc = ri.restate(weekly, "2026-08-28", THREE, REASON, dry_run=True,
                     fetch=fetcher(FRIDAY_CLOSES), now=LONG_AFTER)
    assert doc["rates"]["US10Y"]["close"] == 4.72
    assert not (weekly / "2026-08-28.corrected.json").exists()


def test_the_tool_goes_through_the_writers_own_fetch(panel, provider):
    """So the writer's rules hold for a correction too: the bar dated as_of
    or nothing. Here the provider still has no Friday bar for VIX."""
    table, _ = provider
    table.update(AUG_WEEK)
    table["^VIX"] = without(AUG_WEEK["^VIX"], FRI)
    weekly = panel({"2026-08-28.json": august_28()})
    with pytest.raises(ri.Refused, match="its last that week is 2026-08-27"):
        ri.restate(weekly, "2026-08-28", THREE, REASON, now=LONG_AFTER)

    table["^VIX"] = AUG_WEEK["^VIX"]
    doc = ri.restate(weekly, "2026-08-28", THREE, REASON, now=LONG_AFTER)
    assert [doc[b][t]["close"] for b, t in (
        ("rates", "US10Y"), ("vol", "VIX"), ("fx", "DXY"))] == [
            4.72, 14.43, 99.7]


# -- the committed panel -------------------------------------------------------

WEEKLY = ROOT / "data" / "weekly"


def test_every_committed_correction_is_current_against_its_base():
    """The correction trap as a test. A correction is a full copy of its
    base, so a backfill that touches the week leaves it stale and the new
    names invisible, with no error anywhere -- unless this fails."""
    corrections = sorted(WEEKLY.glob("*.corrected.json"))
    assert corrections
    for path in corrections:
        doc = read(path)
        base = read(path.with_name(doc["corrects"]))
        assert any(rc.recorded_edits(doc)), path.name
        assert rc.apply_edits(base, doc) == doc, (
            path.name + " is stale: run scripts/rebuild_corrections.py")


def test_2026_08_28_is_corrected_to_fridays_three_closes():
    """Cboe's own history has VIX at 14.51 on the 27th and 14.43 on the
    28th; the Treasury par curve has the 10-year at 4.67 and 4.73."""
    path = WEEKLY / "2026-08-28.corrected.json"
    if not path.is_file():
        pytest.skip("no correction committed for 2026-08-28")
    fixed, base = read(path), read(WEEKLY / "2026-08-28.json")

    assert (base["rates"]["US10Y"]["close"], base["vol"]["VIX"]["close"],
            base["fx"]["DXY"]["close"]) == (4.672, 14.51, 99.16), (
        "the original is an observation and stays as it was written")
    assert (fixed["rates"]["US10Y"]["close"], fixed["vol"]["VIX"]["close"],
            fixed["fx"]["DXY"]["close"]) == (4.72, 14.43, 99.7)
    assert sorted(i["block"] + "." + i["ticker"]
                  for i in fixed["restated"]) == [
        "fx.DXY", "rates.US10Y", "vol.VIX"]
    for block, ticker in (("rates", "US10Y"), ("vol", "VIX"), ("fx", "DXY")):
        label = fixed["provenance"][block][ticker]
        assert label["source"] == "yahoo-backfill"
        assert label["fetched_at"] > fixed["fetched_at"]
        assert "observed" not in label
    assert fixed["source"] == "yahoo" and fixed["series"] == base["series"]
    assert fixed["fetched_at"] == base["fetched_at"] == "2026-08-29T14:10:48Z"
    untouched = {b: {t: v for t, v in fixed[b].items()
                     if (b, t) not in {("rates", "US10Y"), ("vol", "VIX"),
                                       ("fx", "DXY")}}
                 for b in snapshot.SPECIAL_BLOCKS}
    assert untouched == {b: {t: v for t, v in base[b].items()
                             if t in untouched[b]}
                         for b in snapshot.SPECIAL_BLOCKS}


def test_no_committed_file_breaks_the_settlement_rule():
    """Nothing dated 2026-10-05 or later may carry an evening read. This
    is the gate, run on the real panel."""
    rep = tc.Report()
    tc.check_feed(ROOT, rep)
    tc.check_feed(ROOT, rep, subdir="daily", require_friday=False,
                  label="daily")
    assert [line for line in rep.lines if line.startswith("FAIL")] == []
    assert settled_stamp("2026-10-09") == "2026-10-10T13:20:00Z"
