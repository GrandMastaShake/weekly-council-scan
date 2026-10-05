"""US2Y is the Treasury 2-year, and never the future that used to carry the name.

Through 2026-10-02 the feed committed Yahoo's 2YY=F as "US2Y" on the belief
that a front-month yield future tracks the cash 2-year within a few bp. It
is a contract nobody trades: volume 0 on 51 of 54 sessions, open interest 4.
The mark sat still for weeks and met the cash yield only at month-end
settlement, so market_state carried a 2-year 20 to 36 bp low and a 2s10s
that much too steep, three weeks running (#110, #119, #129), and 24 of the
113 committed weeks were more than 10 bp off.

Four things are pinned here. The Treasury fetch takes the row for the day
or says why it has none, and stands another day in only on proof. A weekly
file names Treasury per instrument and stays a Yahoo file. The deriver reads
a 2-year only where that label or the committed history supplies one -- a
value with no Treasury label is a futures mark, and a gap is null with a
reason. And the gate fails on a market_state that shows anything else.

No network: the archive and the clock are stubbed.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from conftest import ROOT, SCRIPTS, weekly_doc

import backfill_us2y as bu  # noqa: E402  (conftest stubs the provider)
import backfill_weekly as bf  # noqa: E402
import daily_observe as do  # noqa: E402
import rederive_market_state as rd  # noqa: E402
import truth_check as tc  # noqa: E402
from scan_pipeline import snapshot, snapshot_macro as sm  # noqa: E402

# Real rows, copied from Treasury's files on 2026-10-04. The 2024 header has
# no "1.5 Month" column; the 2026 one does.
CSV_2024 = (
    'Date,"1 Mo","2 Mo","3 Mo","4 Mo","6 Mo","1 Yr","2 Yr","3 Yr","5 Yr",'
    '"7 Yr","10 Yr","20 Yr","30 Yr"\n'
    "08/09/2024,5.54,5.40,5.33,5.22,5.02,4.50,4.05,3.86,3.80,3.85,3.94,4.33,4.23\n"
    "08/08/2024,5.55,5.42,5.34,5.21,5.01,4.48,4.04,3.86,3.83,3.89,3.99,4.38,4.28\n"
)
CSV_2026 = (
    'Date,"1 Mo","1.5 Month","2 Mo","3 Mo","4 Mo","6 Mo","1 Yr","2 Yr",'
    '"3 Yr","5 Yr","7 Yr","10 Yr","20 Yr","30 Yr"\n'
    "10/02/2026,4.04,4.09,4.11,4.19,4.26,4.27,4.46,4.83,4.96,5.06,5.17,5.28,5.67,5.63\n"
    "10/01/2026,4.06,4.10,4.13,4.17,4.26,4.27,4.44,4.78,4.91,5.01,5.12,5.24,5.64,5.61\n"
    "09/30/2026,4.02,4.13,4.16,4.20,4.29,4.33,4.54,4.88,5.00,5.09,5.19,5.29,5.68,5.64\n"
    "09/29/2026,4.04,4.14,4.18,4.25,4.30,4.36,4.58,4.89,4.98,5.06,5.16,5.26,5.64,5.59\n"
    "09/28/2026,4.04,4.14,4.20,4.28,4.33,4.41,4.59,4.92,5.01,5.06,5.15,5.24,5.60,5.56\n"
    "09/25/2026,4.04,4.14,4.20,4.24,4.32,4.33,4.50,4.81,4.94,4.98,5.06,5.17,5.54,5.49\n"
    "07/02/2026,3.70,3.73,3.81,3.82,3.91,3.98,3.96,4.14,4.16,4.23,4.35,4.49,4.99,4.98\n"
    "07/01/2026,3.67,3.71,3.72,3.85,3.95,4.00,4.00,4.17,4.19,4.24,4.35,4.48,4.97,4.97\n"
)
# 2025-02-14, before the 1.5-month bill existed: the cell is simply empty.
CSV_BLANK_CELL = (
    'Date,"1 Mo","1.5 Month","2 Mo","3 Mo","4 Mo","6 Mo","1 Yr","2 Yr",'
    '"3 Yr","5 Yr","7 Yr","10 Yr","20 Yr","30 Yr"\n'
    "02/14/2025,4.37,,4.38,4.34,4.35,4.32,4.23,4.26,4.26,4.33,4.41,4.47,4.75,4.69\n"
)

THU = dt.date(2026, 10, 1)
FRI = dt.date(2026, 10, 2)
JULY_3 = dt.date(2026, 7, 3)        # Independence Day observed: no row
SATURDAY_UTC = dt.datetime(2026, 10, 3, 1, 13, tzinfo=dt.timezone.utc)
STAMP = "2026-10-03T01:13:00Z"
TREASURY = {"source": "treasury", "fetched_at": STAMP}


def rows_2026():
    return sm.parse_treasury_csv(CSV_2026)


def through(day):
    """The 2026 archive as it stood at the end of `day`: nothing later."""
    return {d: r for d, r in rows_2026().items() if d <= day}


@pytest.fixture
def archive(monkeypatch):
    """Stub the Treasury archive and the clock. Returns the per-year dict so
    a test can change what the archive says."""
    years = {2024: sm.parse_treasury_csv(CSV_2024), 2026: rows_2026()}
    monkeypatch.setattr(sm, "fetch_treasury_par_curve",
                        lambda year: years.get(year, {}))
    monkeypatch.setattr(sm, "_utcnow", lambda: SATURDAY_UTC)
    return years


# -- reading the file ----------------------------------------------------------

def test_columns_are_read_by_name_not_position():
    """The 2-year is the 9th field in 2026 and the 8th in 2024. A reader
    built on one year's layout takes the 3-year from the other."""
    old = sm.parse_treasury_csv(CSV_2024)[dt.date(2024, 8, 9)]
    new = rows_2026()[FRI]
    assert old["2 Yr"] == 4.05
    assert new["2 Yr"] == 4.83
    assert CSV_2024.splitlines()[1].split(",")[8] == "3.86", (
        "the fixture must keep the trap: 9th field of the 2024 row is 3 Yr")
    assert CSV_2026.splitlines()[1].split(",")[8] == "4.83"


def test_a_blank_cell_is_absent_never_zero():
    row = sm.parse_treasury_csv(CSV_BLANK_CELL)[dt.date(2025, 2, 14)]
    assert "1.5 Month" not in row
    assert row["2 Yr"] == 4.26
    assert 0.0 not in row.values()


def test_an_empty_body_is_a_year_with_nothing_published():
    """Treasury answers 200 with zero bytes for a year that has no rows."""
    assert sm.parse_treasury_csv("") == {}


def test_a_page_that_is_not_the_file_raises():
    with pytest.raises(ValueError, match="not the par yield curve CSV"):
        sm.parse_treasury_csv("<html><body>Access Denied</body></html>")


def test_a_failed_fetch_is_retried_once_and_never_cached(monkeypatch):
    calls = []

    def flaky(url):
        calls.append(url)
        if len(calls) == 1:
            raise OSError("timed out")
        return CSV_2026

    monkeypatch.setattr(sm, "_TREASURY_CACHE", {})
    monkeypatch.setattr(sm, "_http_get_text", flaky)
    monkeypatch.setattr(sm.time, "sleep", lambda s: None)

    assert sm.fetch_treasury_par_curve(2026)[FRI]["2 Yr"] == 4.83
    assert len(calls) == 2 and "2026" in calls[0]
    sm.fetch_treasury_par_curve(2026)
    assert len(calls) == 2, "a success is cached for the process"

    def down(url):
        raise OSError("timed out")

    monkeypatch.setattr(sm, "_TREASURY_CACHE", {})
    monkeypatch.setattr(sm, "_http_get_text", down)
    with pytest.raises(OSError):
        sm.fetch_treasury_par_curve(2026)
    assert sm._TREASURY_CACHE == {}


# -- which row answers for a date ----------------------------------------------

def test_the_row_dated_as_of_is_the_observation():
    assert sm.select_treasury_row(rows_2026(), FRI, "2 Yr") == (
        4.83, FRI, None)


def test_a_missing_row_is_not_evidence_of_a_holiday():
    """An ordinary Friday, read at the scheduled hour, with Thursday's row
    still on top: Treasury posted late, or a stale copy came back. Taking
    the latest row would commit Thursday's 4.78 under Friday's date, in a
    file nobody may edit. The first cut of this rule decided by the clock
    and stood Thursday in, because the Friday job always runs after the day
    has ended."""
    value, observed, err = sm.select_treasury_row(through(THU), FRI, "2 Yr")
    assert value is None and observed is None
    assert "2026-10-02" in err and "none after it yet" in err
    assert "no earlier session is substituted" in err


def test_a_holiday_takes_the_last_row_of_its_week_once_a_later_row_proves_it():
    """2026-07-03: no row, and the archive goes on after it. Treasury
    skipped the day, so Thursday stands in and the day is named."""
    assert sm.select_treasury_row(rows_2026(), JULY_3, "2 Yr") == (
        4.14, dt.date(2026, 7, 2), None)


def test_a_holiday_is_not_filled_on_the_night_itself():
    """The same holiday, read that evening. Nothing is dated after it yet,
    and a holiday cannot be told from a late post, so it stays a gap."""
    value, _, err = sm.select_treasury_row(
        through(dt.date(2026, 7, 2)), JULY_3, "2 Yr")
    assert value is None and "none after it yet" in err


def test_a_stand_in_never_comes_from_an_earlier_week():
    rows = through(dt.date(2026, 9, 25))
    rows[dt.date(2026, 10, 5)] = {"2 Yr": 4.85}       # proof the day passed
    value, _, err = sm.select_treasury_row(rows, FRI, "2 Yr")
    assert value is None
    assert "its week has no earlier row to stand in" in err


def test_a_row_with_no_2y_cell_is_an_error_not_a_reason_to_look_elsewhere():
    rows = rows_2026()
    del rows[FRI]["2 Yr"]
    value, _, err = sm.select_treasury_row(rows, FRI, "2 Yr")
    assert value is None and "has no '2 Yr' value" in err


@pytest.mark.parametrize("bad", [0.0, -0.25, 483.0])
def test_a_cell_that_cannot_be_a_yield_is_refused(bad):
    """A committed close cannot be edited afterwards."""
    rows = rows_2026()
    rows[FRI]["2 Yr"] = bad
    value, _, err = sm.select_treasury_row(rows, FRI, "2 Yr")
    assert value is None and "plausible yield" in err


def recording(years):
    asked = []

    def fetch(year):
        asked.append(year)
        return years.get(year, {})

    return fetch, asked


def test_new_years_day_reads_its_stand_in_from_last_years_file():
    """Friday 2027-01-01: Thursday's row is in the 2026 file. That night the
    2027 file is still empty, so there is no proof and no value; once the
    4th has posted there is."""
    as_of = dt.date(2027, 1, 1)
    years = {2027: {}, 2026: {dt.date(2026, 12, 31): {"2 Yr": 4.5}}}
    fetch, asked = recording(years)

    rows = sm.week_rows(as_of, fetch=fetch)
    assert asked == [2027, 2026]
    assert sm.select_treasury_row(rows, as_of, "2 Yr")[0] is None

    years[2027] = {dt.date(2027, 1, 4): {"2 Yr": 4.52}}
    rows = sm.week_rows(as_of, fetch=fetch)
    assert sm.select_treasury_row(rows, as_of, "2 Yr") == (
        4.5, dt.date(2026, 12, 31), None)


def test_new_years_eve_finds_its_proof_in_next_years_file():
    """Friday 2027-12-31 (New Year's Day observed): the row that proves the
    day was skipped is the first of 2028."""
    as_of = dt.date(2027, 12, 31)
    years = {2027: {dt.date(2027, 12, 30): {"2 Yr": 4.4}},
             2028: {dt.date(2028, 1, 3): {"2 Yr": 4.41}}}
    fetch, asked = recording(years)

    rows = sm.week_rows(as_of, fetch=fetch)
    assert asked == [2027, 2028]
    assert sm.select_treasury_row(rows, as_of, "2 Yr") == (
        4.4, dt.date(2027, 12, 30), None)


def test_an_ordinary_week_does_not_fetch_a_second_year():
    fetch, asked = recording({2026: rows_2026()})
    sm.week_rows(FRI, fetch=fetch)
    assert asked == [2026]


def test_a_missing_row_in_mid_year_does_not_fetch_a_second_year():
    fetch, asked = recording({2026: through(THU)})
    sm.week_rows(FRI, fetch=fetch)
    assert asked == [2026]


# -- the instrument table and the batch ----------------------------------------

def test_the_future_is_no_longer_filed_under_us2y():
    """The regression, pinned by name: 2YY=F under the key "US2Y"."""
    rates = sm.INSTRUMENTS["rates"]
    assert rates["US2Y"].get("provider") == snapshot.TREASURY_SOURCE
    assert rates["US2Y"]["column"] == "2 Yr"
    assert "symbol" not in rates["US2Y"]
    assert rates["US2Y_FUT"]["symbol"] == "2YY=F"
    others = [t for block in sm.INSTRUMENTS.values() for t, cfg in block.items()
              if "provider" in cfg and t != "US2Y"]
    assert others == [], "one provider, with exactly one named exception"


def yahoo_stub(ticker, cfg, friday):
    closes = {"^TNX": 5.277, "2YY=F": 4.635}
    if cfg["symbol"] in closes:
        return {"close": closes[cfg["symbol"]], "volume": None}, None
    return {"close": 1.0, "volume": None}, None


def test_us2y_comes_from_treasury_and_says_so(monkeypatch, archive):
    monkeypatch.setattr(sm, "_fetch_one", yahoo_stub)
    got = sm.fetch_special_instruments("2026-10-02")

    assert got["rates"]["US2Y"] == {"close": 4.83, "volume": None}
    assert got["rates"]["US2Y_FUT"]["close"] == 4.635
    assert got["rates"]["US10Y"]["close"] == 5.277
    assert got["provenance"] == {"rates": {"US2Y": TREASURY}}
    assert got["missing"] == []


def test_a_failed_treasury_fetch_is_missing_and_the_future_does_not_stand_in(
        monkeypatch):
    def down(year):
        raise OSError("timed out")

    monkeypatch.setattr(sm, "_fetch_one", yahoo_stub)
    monkeypatch.setattr(sm, "fetch_treasury_par_curve", down)
    monkeypatch.setattr(sm, "_utcnow", lambda: SATURDAY_UTC)
    got = sm.fetch_special_instruments("2026-10-02")

    assert "US2Y" not in got["rates"]
    assert got["rates"]["US2Y_FUT"]["close"] == 4.635, "the batch survives"
    assert got["provenance"] == {}
    assert [m["ticker"] for m in got["missing"]] == ["US2Y"]
    assert got["missing"][0]["reason"].startswith("treasury: OSError")


def test_a_friday_whose_row_is_not_up_is_missing_and_thursday_is_not_used(
        monkeypatch, archive):
    """The Friday job, end to end, on the night Treasury is late."""
    archive[2026] = through(THU)
    monkeypatch.setattr(sm, "_fetch_one", yahoo_stub)
    got = sm.fetch_special_instruments("2026-10-02")

    assert "US2Y" not in got["rates"]
    assert got["provenance"] == {}
    assert [m["ticker"] for m in got["missing"]] == ["US2Y"]
    assert "none after it yet" in got["missing"][0]["reason"]


def test_a_proven_holiday_records_the_day_the_value_was_published_for(
        monkeypatch, archive):
    """A late run, a backfill: the archive has moved on past the holiday."""
    monkeypatch.setattr(sm, "_fetch_one", yahoo_stub)
    got = sm.fetch_special_instruments("2026-07-03")
    assert got["rates"]["US2Y"]["close"] == 4.14
    assert got["provenance"]["rates"]["US2Y"]["observed"] == "2026-07-02"


# -- the committed file --------------------------------------------------------

def special(us2y=4.83, fut=4.635, prov=TREASURY):
    rates = {"US10Y": {"close": 5.277, "volume": None}}
    if us2y is not None:
        rates["US2Y"] = {"close": us2y, "volume": None}
    if fut is not None:
        rates["US2Y_FUT"] = {"close": fut, "volume": None}
    out = {"rates": rates, "vol": {}, "commodities": {}, "fx": {},
           "missing": []}
    if prov is not None:
        out["provenance"] = {"rates": {"US2Y": dict(prov)}}
    return out


def written(tmp_path, spec):
    path = snapshot.write_weekly(
        "2026-10-02", {"SPY": {"close": 668.0, "volume": 1}}, spec,
        out_dir=str(tmp_path))
    return path, json.loads(Path(path).read_text(encoding="utf-8"))


def test_the_weekly_file_names_treasury_per_instrument_and_stays_a_yahoo_file(
        tmp_path):
    """sector-regime-heatmap refuses a week whose file-level source it does
    not know, so the second publisher is named beside the one instrument."""
    path, doc = written(tmp_path, special())
    assert doc["source"] == snapshot.PROVIDER == "yahoo"
    assert doc["provenance"] == {"rates": {"US2Y": TREASURY}}
    assert "series" not in doc["provenance"]
    assert snapshot.is_treasury_sourced(doc, "rates", "US2Y")
    assert not snapshot.is_treasury_sourced(doc, "rates", "US2Y_FUT")
    assert not snapshot.is_treasury_sourced(doc, "rates", "US10Y")

    raw = Path(path).read_bytes()
    raw.decode("ascii")
    assert b"\r\n" not in raw and raw.endswith(b"\n")


def test_only_the_exact_label_marks_a_treasury_value(tmp_path):
    _, doc = written(tmp_path, special())
    for other in ("yahoo", "treasury-backfill", "Treasury", ""):
        doc["provenance"]["rates"]["US2Y"]["source"] = other
        assert not snapshot.is_treasury_sourced(doc, "rates", "US2Y")
        assert tc._treasury_us2y(doc) is None


def test_the_stand_in_date_reaches_the_committed_file(tmp_path):
    _, doc = written(tmp_path, special(
        us2y=4.14, prov=dict(TREASURY, observed="2026-07-02")))
    assert doc["provenance"]["rates"]["US2Y"]["observed"] == "2026-07-02"


def test_a_label_for_an_instrument_that_was_not_written_is_dropped(tmp_path):
    """Treasury failed, so there is no US2Y to label; an anchor for an entry
    that is not there describes nothing and the feed gate refuses it."""
    _, doc = written(tmp_path, special(us2y=None))
    assert "US2Y" not in doc["rates"]
    assert "provenance" not in doc


def test_a_special_block_with_no_provenance_writes_none(tmp_path):
    _, doc = written(tmp_path, special(prov=None))
    assert "provenance" not in doc
    assert not snapshot.is_treasury_sourced(doc, "rates", "US2Y")


def test_the_daily_file_carries_the_same_label():
    bars = {"bars": {"SPY": {"close": 668.0, "volume": 1}}, "missing": []}
    doc = do.build_document("2026-10-02", bars, special())
    assert doc["source"] == "yahoo-daily"
    assert doc["provenance"] == {"rates": {"US2Y": TREASURY}}
    assert "provenance" not in do.build_document("2026-10-02", bars, None)


def test_a_full_rewrite_keeps_the_label_through_its_restamp(
        tmp_path, monkeypatch):
    """backfill_weekly --force writes the week, then reloads it to stamp the
    backfill source and timestamp on the file. The instrument's own label
    has to come back out of that round trip."""
    monkeypatch.setattr(bf.snapshot_macro, "fetch_special_instruments",
                        lambda friday: special())
    monkeypatch.setattr(bf.time, "sleep", lambda s: None)

    rec = bf.build_and_write(FRI, ["SPY"], {"SPY": ([FRI], [668.0], [1])},
                             str(tmp_path))

    doc = json.loads(Path(rec["path"]).read_text(encoding="utf-8"))
    assert doc["source"] == bf.BACKFILL_SOURCE
    assert doc["provenance"] == {"rates": {"US2Y": TREASURY}}


# -- the deriver ---------------------------------------------------------------

def week(as_of, us10y, us2y=None, fut=None, treasury=False):
    """One weekly doc. treasury=True is a post-cutover file; without it,
    `us2y` is what every file through 2026-10-02 holds: the futures mark."""
    doc = weekly_doc(as_of, ["SPY"])
    doc["rates"] = {"US10Y": {"close": us10y, "volume": None}}
    if us2y is not None:
        doc["rates"]["US2Y"] = {"close": us2y, "volume": None}
    if fut is not None:
        doc["rates"]["US2Y_FUT"] = {"close": fut, "volume": None}
    if treasury:
        doc["provenance"] = {"rates": {"US2Y": {
            "source": "treasury", "fetched_at": as_of + "T23:00:00Z"}}}
    return doc


def history(weekly_dir, closes):
    """Write us2y_treasury.json beside a weekly dir. closes: {week: close}."""
    doc = bu.empty_history()
    doc["series"] = {w: {"close": c, "fetched_at": "2026-10-05T02:35:18Z"}
                     for w, c in closes.items()}
    path = Path(snapshot.us2y_history_path(str(weekly_dir)))
    path.write_text(snapshot.canonical_json(doc), encoding="utf-8",
                    newline="")
    return path


def derive(weekly_dir):
    return snapshot.derive_market_state(
        str(weekly_dir), str(weekly_dir.parent / "no-facts.json"))


# The last two committed weeks as they actually are: futures marks 4.472 and
# 4.635 under "US2Y", Treasury 4.81 and 4.83.
PRE_CUTOVER = {
    "2026-09-25.json": week("2026-09-25", 5.184, us2y=4.472),
    "2026-10-02.json": week("2026-10-02", 5.277, us2y=4.635),
}
# The week after, written by the Treasury-aware writer.
CUTOVER = week("2026-10-09", 5.30, us2y=4.86, fut=4.66, treasury=True)
TRUE_HISTORY = {"2026-09-25": 4.81, "2026-10-02": 4.83}


def test_a_us2y_with_no_treasury_label_is_a_futures_mark_and_is_never_read(
        panel):
    """The defect itself. Without the history the honest answer is null."""
    rates = derive(panel(PRE_CUTOVER))["rates"]
    assert rates["US2Y"]["lvl"] is None
    assert "never substituted" in rates["US2Y"]["lvl_reason"]
    assert "2026-10-02" in rates["US2Y"]["lvl_reason"]
    assert "us2y_treasury.json not found" in rates["US2Y"]["lvl_reason"]
    assert rates["US2Y"]["d1w_bps"] is None
    assert rates["US2Y"]["pctile_2y"] is None
    assert rates["curve_2s10s_bps"] is None
    assert rates["US10Y"]["lvl"] == 5.28, "the 10-year is untouched"


def test_a_missing_2y_makes_the_curve_leg_unknown_not_positive(panel):
    assert derive(panel(PRE_CUTOVER))["regime"].split(" / ")[1] == \
        "curve-unknown"


def test_the_history_supplies_the_weeks_the_panel_cannot_edit(panel):
    """The committed state this change regenerates: 4.83, +2 bp, 2s10s 45 --
    where the futures mark gave 4.63, +16 bp and 65."""
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    state = derive(weekly)
    assert state["rates"]["US2Y"] == {"lvl": 4.83, "d1w_bps": 2,
                                      "pctile_2y": 50}
    assert state["rates"]["curve_2s10s_bps"] == 45
    assert state["regime"].split(" / ")[1] == "curve-positive"


def test_a_treasury_sourced_week_is_read_from_its_own_file(panel):
    weekly = panel({"2026-10-02.json": PRE_CUTOVER["2026-10-02.json"],
                    "2026-10-09.json": CUTOVER})
    history(weekly, {"2026-10-02": 4.83})
    rates = derive(weekly)["rates"]
    assert rates["US2Y"]["lvl"] == 4.86
    assert rates["curve_2s10s_bps"] == 44


def test_the_cutover_week_is_differenced_on_one_basis(panel):
    """The seam. Last week's file says 4.635 (the future), this week's says
    4.86 (Treasury): read straight from the files that is +22 bp, and the
    2-year actually moved +3."""
    weekly = panel({"2026-10-02.json": PRE_CUTOVER["2026-10-02.json"],
                    "2026-10-09.json": CUTOVER})
    history(weekly, {"2026-10-02": 4.83})
    assert derive(weekly)["rates"]["US2Y"]["d1w_bps"] == 3


def test_the_weeks_own_observation_wins_over_a_history_entry(panel):
    weekly = panel({"2026-10-09.json": CUTOVER})
    history(weekly, {"2026-10-09": 4.99})
    assert derive(weekly)["rates"]["US2Y"]["lvl"] == 4.86


def test_a_history_entry_for_a_week_the_panel_lacks_is_not_in_the_window(
        panel):
    """It would enter the percentile as a week that was never observed."""
    weekly = panel(PRE_CUTOVER)
    history(weekly, dict(TRUE_HISTORY, **{"2026-09-18": 9.99}))
    docs = snapshot._load_weekly_files(str(weekly))
    pts = snapshot.cash_2y_series(
        docs, snapshot.load_us2y_history(snapshot.us2y_history_path(
            str(weekly)))[0])
    assert pts == TRUE_HISTORY


def test_a_week_with_no_treasury_value_is_a_gap_with_a_reason(panel):
    """A Friday the Treasury fetch failed: US2Y is in `missing`, the future
    is in the file, and market_state must not reach for it."""
    weekly = panel({
        "2026-10-02.json": PRE_CUTOVER["2026-10-02.json"],
        "2026-10-09.json": week("2026-10-09", 5.30, fut=4.66),
    })
    history(weekly, {"2026-10-02": 4.83})
    rates = derive(weekly)["rates"]
    assert rates["US2Y"]["lvl"] is None
    assert "no Treasury 2-year for 2026-10-09" in rates["US2Y"]["lvl_reason"]
    assert "no us2y_treasury.json entry" in rates["US2Y"]["lvl_reason"]
    assert rates["curve_2s10s_bps"] is None


def test_the_week_after_a_gap_says_which_week_is_missing(panel):
    weekly = panel({
        "2026-10-09.json": week("2026-10-09", 5.30, fut=4.66),
        "2026-10-16.json": week("2026-10-16", 5.31, us2y=4.88, treasury=True),
    })
    history(weekly, {})
    rates = derive(weekly)["rates"]
    assert rates["US2Y"]["lvl"] == 4.88
    assert rates["US2Y"]["d1w_bps"] is None
    assert "no Treasury 2-year for 2026-10-09" in \
        rates["US2Y"]["d1w_bps_reason"]


def test_without_the_history_the_percentile_is_null_not_a_rank_among_one(
        panel):
    """A runner that has the new code but never received the file. Its one
    Treasury week ranked against itself is the 0th percentile, and that
    would be published as fact."""
    weekly = panel(dict(PRE_CUTOVER, **{"2026-10-09.json": CUTOVER}))
    rates = derive(weekly)["rates"]
    assert rates["US2Y"]["lvl"] == 4.86
    assert rates["US2Y"]["pctile_2y"] is None
    assert "us2y_treasury.json not found" in rates["US2Y"]["pctile_2y_reason"]
    assert rates["US2Y"]["d1w_bps"] is None
    assert "us2y_treasury.json not found" in rates["US2Y"]["d1w_bps_reason"]


def test_an_unreadable_history_degrades_the_same_way(panel):
    weekly = panel(dict(PRE_CUTOVER, **{"2026-10-09.json": CUTOVER}))
    Path(snapshot.us2y_history_path(str(weekly))).write_text(
        "{not json", encoding="utf-8")
    pts, problem = snapshot.load_us2y_history(
        snapshot.us2y_history_path(str(weekly)))
    assert pts == {} and "unreadable" in problem
    assert derive(weekly)["rates"]["US2Y"]["pctile_2y"] is None


def test_a_panel_whose_every_week_has_its_own_value_needs_no_history(panel):
    """The file is for the weeks that cannot speak for themselves. Where
    there are none, its absence takes nothing away."""
    weekly = panel({
        "2026-10-09.json": CUTOVER,
        "2026-10-16.json": week("2026-10-16", 5.31, us2y=4.88, treasury=True),
    })
    assert derive(weekly)["rates"]["US2Y"] == {
        "lvl": 4.88, "d1w_bps": 2, "pctile_2y": 50}


def test_the_history_file_is_found_beside_the_weekly_directory(tmp_path):
    """So a caller that names weekly_dir has named it too, and the Friday
    job's call needs no new argument."""
    got = Path(snapshot.us2y_history_path(str(tmp_path / "data" / "weekly")))
    assert got == tmp_path / "data" / "us2y_treasury.json"


def test_the_history_is_an_input_the_purity_check_sees(panel):
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    facts = str(weekly.parent / "no-facts.json")
    out = weekly.parent / "market_state.json"

    snapshot._write_json(str(out), snapshot.derive_chain(str(weekly), facts))
    assert snapshot.rederive_and_compare(str(weekly), facts, str(out)) == (
        True, None)

    history(weekly, {"2026-09-25": 4.81, "2026-10-02": 4.90})
    match, where = snapshot.rederive_and_compare(str(weekly), facts, str(out))
    assert not match and where.startswith("$.rates.")


def test_the_weekly_jobs_single_step_agrees_with_the_chain_across_the_seam(
        panel):
    """The job derives one step from last week's state; the gate derives the
    whole chain. If the two read the 2-year differently the gate fails every
    Friday."""
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    facts = str(weekly.parent / "no-facts.json")
    last_week = snapshot.derive_chain(str(weekly), facts)

    weekly = panel({"2026-10-09.json": CUTOVER})
    step = snapshot.derive_market_state(str(weekly), facts, last_week)
    chain = snapshot.derive_chain(str(weekly), facts)
    assert snapshot.canonical_json(step) == snapshot.canonical_json(chain)
    assert step["rates"]["US2Y"] == {"lvl": 4.86, "d1w_bps": 3,
                                     "pctile_2y": 67}


# -- the feed gate -------------------------------------------------------------

def gate(repo):
    rep = tc.Report()
    tc.check_feed(repo, rep)
    tc.check_us2y_history(repo, rep)
    return rep


def fails(rep):
    return [line for line in rep.lines if line.startswith("FAIL")]


def warns(rep):
    return [line for line in rep.lines if line.startswith("WARN")]


def test_the_gate_and_the_deriver_agree_on_the_names():
    """truth_check stays stdlib-only, so it repeats two constants."""
    assert tc.TREASURY_SOURCE == snapshot.TREASURY_SOURCE
    assert tc.US2Y_HISTORY[-1] == snapshot.US2Y_HISTORY_FILE


def test_the_gate_accepts_a_treasury_labelled_week(panel, tmp_path):
    panel({"2026-10-09.json": CUTOVER})
    rep = gate(tmp_path)
    assert fails(rep) == []
    assert any("1 in their own file" in line for line in rep.lines)


def test_the_gate_refuses_a_label_for_an_instrument_that_is_not_there(
        panel, tmp_path):
    doc = week("2026-10-09", 5.30, fut=4.66, treasury=True)
    panel({"2026-10-09.json": doc})
    assert any("provenance names 'US2Y', which is not in 'rates'" in line
               for line in fails(gate(tmp_path)))


@pytest.mark.parametrize("observed,why", [
    ("2026-10-09", "not an earlier day"),      # the file's own date
    ("2026-10-02", "not an earlier day"),      # last week
    ("Thursday", "not an ISO date"),
])
def test_the_gate_refuses_a_stand_in_date_from_outside_the_week(
        panel, tmp_path, observed, why):
    doc = week("2026-10-09", 5.30, us2y=4.86, treasury=True)
    doc["provenance"]["rates"]["US2Y"]["observed"] = observed
    panel({"2026-10-09.json": doc})
    assert any(why in line for line in fails(gate(tmp_path)))


def test_the_gate_accepts_a_stand_in_date_from_the_same_week(panel, tmp_path):
    doc = week("2026-07-03", 4.485, us2y=4.14, treasury=True)
    doc["provenance"]["rates"]["US2Y"]["observed"] = "2026-07-02"
    panel({"2026-07-03.json": doc})
    assert fails(gate(tmp_path)) == []


def test_the_gate_refuses_an_empty_provenance_block(panel, tmp_path):
    doc = week("2026-10-09", 5.30)
    doc["provenance"] = {}
    panel({"2026-10-09.json": doc})
    assert any("'provenance' is empty" in line
               for line in fails(gate(tmp_path)))


def test_a_week_with_no_treasury_2y_is_a_warning_and_never_a_failure(
        panel, tmp_path):
    """The honest outcome is already in place -- market_state says null --
    so the gate names the gap and the fix without refusing the panel."""
    weekly = panel(dict(PRE_CUTOVER, **{
        "2026-10-09.json": week("2026-10-09", 5.30, fut=4.66)}))
    history(weekly, TRUE_HISTORY)
    rep = gate(tmp_path)
    assert fails(rep) == []
    assert len(warns(rep)) == 1
    assert "1 of 3 week(s) have no Treasury 2-year: 2026-10-09" in \
        warns(rep)[0]
    assert "backfill_us2y.py" in warns(rep)[0]


def test_the_gate_validates_the_history_file(panel, tmp_path):
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    rep = gate(tmp_path)
    assert fails(rep) == [] and warns(rep) == []
    assert any("2 from data/us2y_treasury.json" in line for line in rep.lines)


def test_the_gate_refuses_a_history_entry_for_a_week_with_no_file(
        panel, tmp_path):
    weekly = panel(PRE_CUTOVER)
    history(weekly, dict(TRUE_HISTORY, **{"2026-09-18": 4.76}))
    assert any("names a week with no weekly file" in line
               for line in fails(gate(tmp_path)))


@pytest.mark.parametrize("close", [0, -4.83, "4.83", None, True])
def test_the_gate_refuses_a_history_close_that_is_not_a_positive_number(
        panel, tmp_path, close):
    weekly = panel(PRE_CUTOVER)
    history(weekly, {"2026-09-25": 4.81, "2026-10-02": close})
    assert any("series['2026-10-02'] close" in line
               for line in fails(gate(tmp_path)))


def test_the_gate_refuses_two_different_treasury_values_for_one_week(
        panel, tmp_path):
    """The deriver reads the weekly file's. The gate does not let the
    disagreement stand, because one of the two is wrong."""
    weekly = panel({"2026-10-09.json": CUTOVER})
    history(weekly, {"2026-10-09": 4.99})
    assert any("two different Treasury 2-year values" in line
               for line in fails(gate(tmp_path)))

    history(weekly, {"2026-10-09": 4.86})
    assert fails(gate(tmp_path)) == [], "the same value twice is harmless"


def test_the_gate_refuses_a_history_file_that_is_not_ascii(panel, tmp_path):
    weekly = panel(PRE_CUTOVER)
    path = history(weekly, TRUE_HISTORY)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["about"] = "2s10s " + chr(0x2014) + " steep"     # an em dash
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert any("not pure ASCII" in line for line in fails(gate(tmp_path)))


# -- the gate on market_state itself -------------------------------------------

def market_state(repo, as_of, lvl, d1w=0, pct=50):
    """A market_state with just the fields the gate reads. A null level
    carries null everything, as the deriver writes it."""
    if lvl is None:
        d1w = pct = None
    (repo / "data" / "market_state.json").write_text(
        json.dumps({"as_of": as_of, "rates": {"US2Y": {
            "lvl": lvl, "d1w_bps": d1w, "pctile_2y": pct}}}),
        encoding="utf-8")


def test_the_gate_refuses_a_market_state_that_shows_the_future(
        panel, tmp_path):
    """The defect as it stood on main, 2026-10-04: 4.63 where the Treasury
    2-year was 4.83. Three weekly syntheses caught it by reading; nothing
    mechanical did. This is what a runner on the old deriver would push."""
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    market_state(tmp_path, "2026-10-02", 4.63, d1w=16, pct=99)
    got = fails(gate(tmp_path))
    assert len(got) == 1
    assert "carries US2Y 4.63 for 2026-10-02" in got[0]
    assert "the Treasury 2-year is 4.83" in got[0]


def test_the_gate_accepts_a_market_state_that_shows_the_treasury_2y(
        panel, tmp_path):
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    market_state(tmp_path, "2026-10-02", 4.83, d1w=2, pct=50)
    rep = gate(tmp_path)
    assert fails(rep) == []
    assert any("US2Y for 2026-10-02 is 4.83, the Treasury 2-year" in line
               for line in rep.lines)


def test_the_gate_reads_the_weeks_own_value_before_the_history(
        panel, tmp_path):
    weekly = panel({"2026-10-02.json": PRE_CUTOVER["2026-10-02.json"],
                    "2026-10-09.json": CUTOVER})
    history(weekly, {"2026-10-02": 4.83})
    market_state(tmp_path, "2026-10-09", 4.86, d1w=3)
    assert fails(gate(tmp_path)) == []
    market_state(tmp_path, "2026-10-09", 4.66, d1w=3)
    assert any("the Treasury 2-year is 4.86 (weekly/2026-10-09.json)" in line
               for line in fails(gate(tmp_path)))


def test_the_gate_refuses_any_number_for_a_week_with_no_treasury_2y(
        panel, tmp_path):
    """No value exists, so the only honest state is null."""
    weekly = panel(PRE_CUTOVER)
    history(weekly, {"2026-09-25": 4.81})
    market_state(tmp_path, "2026-10-02", 4.63)
    assert any("so it must be null" in line for line in fails(gate(tmp_path)))

    market_state(tmp_path, "2026-10-02", None)
    rep = gate(tmp_path)
    assert fails(rep) == []
    assert any("is null (no Treasury 2-year for that week)" in line
               for line in rep.lines)


def test_the_gate_refuses_a_null_once_the_value_exists(panel, tmp_path):
    """A gap was filled and market_state was not re-derived."""
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    market_state(tmp_path, "2026-10-02", None)
    assert any("carries US2Y None for 2026-10-02" in line
               for line in fails(gate(tmp_path)))


def test_the_gate_refuses_a_state_derived_where_the_history_was_missing(
        panel, tmp_path):
    """New code on the runner, the history file never copied there. The
    level comes from the week's own file and is right; the weekly change and
    the percentile come out null. Pushed to a tree that has the history,
    that state is stale and nothing else in CI says so."""
    weekly = panel(dict(PRE_CUTOVER, **{"2026-10-09.json": CUTOVER}))
    runner_state = derive(weekly)["rates"]["US2Y"]
    assert runner_state["lvl"] == 4.86 and runner_state["d1w_bps"] is None

    history(weekly, TRUE_HISTORY)
    market_state(tmp_path, "2026-10-09", 4.86, d1w=None, pct=None)
    got = fails(gate(tmp_path))
    assert len(got) == 1
    assert "d1w_bps is None although the Treasury 2-year exists for both " \
           "2026-10-02 and 2026-10-09" in got[0]
    assert "pctile_2y is None although the level is 4.86" in got[0]
    assert "rederive_market_state.py" in got[0]


def test_the_gate_refuses_a_weekly_change_measured_from_a_week_with_no_value(
        panel, tmp_path):
    weekly = panel({
        "2026-10-09.json": week("2026-10-09", 5.30, fut=4.66),
        "2026-10-16.json": week("2026-10-16", 5.31, us2y=4.88, treasury=True),
    })
    history(weekly, {})
    market_state(tmp_path, "2026-10-16", 4.88, d1w=22)
    assert any("d1w_bps is 22 although there is no Treasury 2-year for "
               "2026-10-09" in line for line in fails(gate(tmp_path)))
    market_state(tmp_path, "2026-10-16", 4.88, d1w=None)
    assert fails(gate(tmp_path)) == []


def test_the_gate_fails_where_a_state_was_derived_without_the_history_file(
        panel, tmp_path):
    """The runner's own gate, on the night it derives without the file. A
    missing history is only a warning in a tree that derives nothing."""
    panel(dict(PRE_CUTOVER, **{"2026-10-09.json": CUTOVER}))
    rep = gate(tmp_path)
    assert fails(rep) == [] and len(warns(rep)) == 1

    market_state(tmp_path, "2026-10-09", 4.86, d1w=None, pct=None)
    got = fails(gate(tmp_path))
    assert len(got) == 1
    assert "data/us2y_treasury.json not found" in got[0]
    assert "2 of 3 week(s) can only get their Treasury 2-year from it" in \
        got[0]


def test_the_gate_says_so_when_market_state_is_for_a_week_it_cannot_see(
        panel, tmp_path):
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    market_state(tmp_path, "2026-10-09", 4.86)
    rep = gate(tmp_path)
    assert fails(rep) == []
    assert any("as_of 2026-10-09, which has no weekly file here" in line
               for line in warns(rep))


def test_the_gate_refuses_a_market_state_it_cannot_read_the_2y_from(
        panel, tmp_path):
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    (tmp_path / "data" / "market_state.json").write_text(
        json.dumps({"as_of": "2026-10-02", "rates": {}}), encoding="utf-8")
    assert any("no readable as_of / rates.US2Y" in line
               for line in fails(gate(tmp_path)))


# -- the label survives the other writers --------------------------------------

def test_a_merge_that_adds_nothing_does_not_erase_the_rates_label(tmp_path):
    """merge_into_existing dropped the whole provenance block whenever its
    per-series part came up empty."""
    doc = week("2026-10-09", 5.30, us2y=4.86, treasury=True)
    d = tmp_path / "weekly"
    d.mkdir()
    p = d / "2026-10-09.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    bf.merge_into_existing(dt.date(2026, 10, 9), ["PLTR"],
                           {"PLTR": ([], [], [])}, str(p))

    after = json.loads(p.read_text(encoding="utf-8"))
    assert after["provenance"] == doc["provenance"]
    assert snapshot.is_treasury_sourced(after, "rates", "US2Y")


def test_a_merge_adds_its_anchor_beside_the_rates_label(tmp_path):
    doc = week("2026-10-09", 5.30, us2y=4.86, treasury=True)
    d = tmp_path / "weekly"
    d.mkdir()
    p = d / "2026-10-09.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    day = dt.date(2026, 10, 9)
    bf.merge_into_existing(day, ["PLTR"], {"PLTR": ([day], [50.0], [9])},
                           str(p))

    prov = json.loads(p.read_text(encoding="utf-8"))["provenance"]
    assert set(prov) == {"rates", "series"}
    assert set(prov["series"]) == {"PLTR"}


def test_a_rebuilt_correction_keeps_the_rates_label(tmp_path):
    """rebuild_corrections had the same habit: emptying provenance.series
    took the rest of the block with it."""
    d = tmp_path / "data" / "weekly"
    d.mkdir(parents=True)
    base = week("2026-10-09", 5.30, us2y=4.86, treasury=True)
    base["series"]["AVB"] = {"close": 65.9005, "volume": 0}
    base["provenance"]["series"] = {"AVB": {
        "source": "yahoo-backfill", "fetched_at": "2026-10-10T04:08:06Z"}}
    (d / "2026-10-09.json").write_text(json.dumps(base), encoding="utf-8")

    corrected = json.loads(json.dumps(base))
    corrected["series"].pop("AVB")
    corrected["provenance"].pop("series")
    corrected["missing"] = [{"ticker": "AVB",
                             "reason": "zero-volume bar, close 65.9005"}]
    corrected["corrects"] = "2026-10-09.json"
    corrected["reason"] = "AVB printed behind zero volume"
    (d / "2026-10-09.corrected.json").write_text(json.dumps(corrected),
                                                 encoding="utf-8")

    r = subprocess.run([sys.executable, str(SCRIPTS / "rebuild_corrections.py"),
                        "--dir", str(d)], capture_output=True, text=True)
    assert r.returncode == 0 and "rebuilt" in r.stdout

    after = json.loads((d / "2026-10-09.corrected.json")
                       .read_text(encoding="utf-8"))
    assert after["provenance"] == {"rates": base["provenance"]["rates"]}
    assert fails(gate(tmp_path)) == []


# -- backfill_us2y.py ----------------------------------------------------------

def data_root(panel, files):
    return panel(files).parent


def read_history(root):
    return json.loads((root / "us2y_treasury.json").read_text(encoding="utf-8"))


def test_backfill_fills_exactly_the_weeks_that_have_no_treasury_2y(
        panel, archive):
    root = data_root(panel, {
        "2026-09-25.json": PRE_CUTOVER["2026-09-25.json"],
        "2026-10-02.json": week("2026-10-02", 5.277, us2y=4.83, fut=4.635,
                                treasury=True),
    })
    assert bu.main(["--data", str(root)]) == 0

    doc = read_history(root)
    assert set(doc["series"]) == {"2026-09-25"}, (
        "a week with its own Treasury value needs no entry")
    assert doc["series"]["2026-09-25"] == {"close": 4.81, "fetched_at": STAMP}
    assert doc["source"] == "treasury-backfill"
    assert doc["instrument"] == "US2Y" and doc["column"] == "2 Yr"


def test_backfill_writes_a_file_the_gate_and_the_deriver_accept(
        panel, archive, tmp_path):
    root = data_root(panel, PRE_CUTOVER)
    assert bu.main(["--data", str(root)]) == 0

    raw = (root / "us2y_treasury.json").read_bytes()
    raw.decode("ascii")
    assert b"\r\n" not in raw and raw.endswith(b"\n")
    assert raw.decode("ascii") == snapshot.canonical_json(json.loads(raw))
    assert fails(gate(tmp_path)) == []
    assert derive(root / "weekly")["rates"]["US2Y"]["lvl"] == 4.83


def test_backfill_never_rewrites_a_week_that_has_an_entry(panel, archive):
    """Append-only by week. The archive says 4.81; the committed 4.80 stays,
    and --check is what reports the difference."""
    root = data_root(panel, PRE_CUTOVER)
    history(root / "weekly", {"2026-09-25": 4.80})
    assert bu.main(["--data", str(root)]) == 0

    series = read_history(root)["series"]
    assert series["2026-09-25"]["close"] == 4.80
    assert series["2026-10-02"]["close"] == 4.83


def test_backfill_with_nothing_to_add_leaves_the_file_byte_identical(
        panel, archive):
    root = data_root(panel, PRE_CUTOVER)
    assert bu.main(["--data", str(root)]) == 0
    before = (root / "us2y_treasury.json").read_bytes()
    assert bu.main(["--data", str(root)]) == 0
    assert (root / "us2y_treasury.json").read_bytes() == before


def test_backfill_records_the_stand_in_day_for_a_proven_holiday(
        panel, archive):
    root = data_root(panel, {
        "2026-07-03.json": week("2026-07-03", 4.485, us2y=3.896)})
    assert bu.main(["--data", str(root)]) == 0
    assert read_history(root)["series"]["2026-07-03"] == {
        "close": 4.14, "fetched_at": STAMP, "observed": "2026-07-02"}


def test_backfill_does_not_fill_a_holiday_before_a_later_row_proves_it(
        panel, archive, capsys):
    """Run the same evening, the stand-in would go into a file whose entries
    are never rewritten. It waits."""
    archive[2026] = through(dt.date(2026, 7, 2))
    root = data_root(panel, {
        "2026-07-03.json": week("2026-07-03", 4.485, us2y=3.896)})
    assert bu.main(["--data", str(root)]) == 1
    assert not (root / "us2y_treasury.json").exists()
    assert "2026-07-03  not filled" in capsys.readouterr().out


def test_backfill_leaves_a_week_it_cannot_fill_as_a_gap_and_says_so(
        panel, archive, capsys):
    """One week the archive has no row for yet. It is not written, the run
    is not a success, and the weeks that could be filled still are."""
    root = data_root(panel, dict(PRE_CUTOVER, **{
        "2026-10-09.json": week("2026-10-09", 5.30, us2y=4.66)}))
    assert bu.main(["--data", str(root)]) == 1
    assert set(read_history(root)["series"]) == {"2026-09-25", "2026-10-02"}
    assert "2026-10-09  not filled" in capsys.readouterr().out


def test_backfill_dry_run_writes_nothing(panel, archive, capsys):
    root = data_root(panel, PRE_CUTOVER)
    assert bu.main(["--data", str(root), "--dry-run"]) == 0
    assert not (root / "us2y_treasury.json").exists()
    assert "DRY RUN" in capsys.readouterr().out


def facts_file(tmp_path):
    macro = tmp_path / "macro"
    macro.mkdir(exist_ok=True)
    (macro / "facts.json").write_text(
        json.dumps({"schema": "macro-facts/v1",
                    "policy": {"fed_stance": {"value": "Hike",
                                              "as_of": "2026-09-16"}}}),
        encoding="utf-8")
    return macro / "facts.json"


def test_a_fill_leaves_market_state_in_step_with_the_history(
        panel, archive, tmp_path):
    """Following the gate's advice used to end in a red gate: the fill made
    the committed state stale and nothing re-derived it. A filled gap and a
    market_state that still says null fail --feed, which the daily and
    backfill workflows run before they commit anything."""
    root = data_root(panel, PRE_CUTOVER)
    facts_file(tmp_path)
    market_state(tmp_path, "2026-10-02", None)

    assert bu.main(["--data", str(root)]) == 0

    state = json.loads((root / "market_state.json").read_text(encoding="utf-8"))
    assert state["rates"]["US2Y"] == {"lvl": 4.83, "d1w_bps": 2,
                                      "pctile_2y": 50}
    assert state["policy"]["fed_stance"] == "Hike", "facts.json was read"
    assert fails(gate(tmp_path)) == []


def test_a_fill_that_cannot_re_derive_says_so_and_is_not_a_success(
        panel, archive, tmp_path, capsys):
    """No facts.json to derive with. Deriving anyway would null the policy
    block of a committed file, so the state is left alone and named."""
    root = data_root(panel, PRE_CUTOVER)
    market_state(tmp_path, "2026-10-02", None)
    before = (root / "market_state.json").read_bytes()

    assert bu.main(["--data", str(root)]) == 1

    assert (root / "market_state.json").read_bytes() == before
    assert set(read_history(root)["series"]) == set(TRUE_HISTORY)
    assert "NOT re-derived" in capsys.readouterr().out


def test_check_passes_while_the_archive_still_agrees(panel, archive):
    root = data_root(panel, dict(PRE_CUTOVER, **{
        "2026-07-03.json": week("2026-07-03", 4.485, us2y=3.896)}))
    assert bu.main(["--data", str(root)]) == 0
    assert bu.main(["--data", str(root), "--check"]) == 0


def test_check_reports_a_difference_and_changes_nothing(
        panel, archive, capsys):
    root = data_root(panel, PRE_CUTOVER)
    assert bu.main(["--data", str(root)]) == 0
    before = (root / "us2y_treasury.json").read_bytes()

    archive[2026][dt.date(2026, 9, 25)]["2 Yr"] = 4.82      # Treasury revised
    assert bu.main(["--data", str(root), "--check"]) == 1
    out = capsys.readouterr().out
    assert "2026-09-25" in out and "committed 4.81" in out and "4.82" in out
    assert (root / "us2y_treasury.json").read_bytes() == before


def test_check_covers_a_weekly_files_own_treasury_value(
        panel, archive, capsys):
    root = data_root(panel, {
        "2026-10-02.json": week("2026-10-02", 5.277, us2y=4.80, fut=4.635,
                                treasury=True)})
    assert bu.main(["--data", str(root), "--check"]) == 1
    assert "weekly/2026-10-02.json" in capsys.readouterr().out


# -- rederive_market_state.py --------------------------------------------------

def test_rederive_writes_what_the_purity_gate_expects(panel, tmp_path, capsys):
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    facts = facts_file(tmp_path)
    market_state(tmp_path, "2026-10-02", 4.63, d1w=16, pct=99)

    assert rd.main(["--data", str(weekly.parent)]) == 0
    assert "first difference at" in capsys.readouterr().out
    assert snapshot.rederive_and_compare(
        str(weekly), str(facts), str(weekly.parent / "market_state.json")
    ) == (True, None)


def test_rederive_leaves_a_current_file_untouched(panel, tmp_path, capsys):
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    facts_file(tmp_path)
    assert rd.main(["--data", str(weekly.parent)]) == 0
    before = (weekly.parent / "market_state.json").read_bytes()
    capsys.readouterr()

    assert rd.main(["--data", str(weekly.parent)]) == 0
    assert (weekly.parent / "market_state.json").read_bytes() == before
    assert "nothing written" in capsys.readouterr().out


def test_rederive_refuses_to_run_without_facts(panel, tmp_path, capsys):
    weekly = panel(PRE_CUTOVER)
    history(weekly, TRUE_HISTORY)
    market_state(tmp_path, "2026-10-02", 4.63)
    before = (weekly.parent / "market_state.json").read_bytes()

    assert rd.main(["--data", str(weekly.parent)]) == 1
    assert (weekly.parent / "market_state.json").read_bytes() == before
    assert "NOT re-derived" in capsys.readouterr().out


# -- the CI guard on the history file ------------------------------------------

def ci_panel_check():
    """The inline script of ci.yml's panel step, as CI runs it."""
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml")
                         .read_text(encoding="utf-8"))
    step = [s for s in doc["jobs"]["test"]["steps"]
            if str(s.get("name", "")).startswith("Panel is intact")][0]
    return re.search(r"python - <<'PY'\n(.*)\nPY", step["run"], re.S).group(1)


@pytest.fixture
def two_commits(tmp_path):
    """A throwaway repo: commit one history file, then another, and run the
    CI step on the result. Returns (exit code, output)."""
    if shutil.which("git") is None:
        pytest.skip("git not available")

    def git(*args):
        r = subprocess.run(
            ["git", "-C", str(tmp_path), "-c", "user.name=t",
             "-c", "user.email=t@example.invalid", "-c", "core.autocrlf=false",
             "-c", "commit.gpgsign=false"] + list(args),
            capture_output=True, text=True)
        assert r.returncode == 0, r.stderr

    def run(first, second):
        git("init", "-q")
        (tmp_path / "data").mkdir()
        script = tmp_path / "ci_panel_check.py"
        script.write_text(ci_panel_check(), encoding="utf-8")
        for n, series in enumerate((first, second)):
            path = tmp_path / "data" / "us2y_treasury.json"
            if series is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(json.dumps({"series": series}),
                                encoding="utf-8")
            (tmp_path / "marker.txt").write_text(str(n), encoding="utf-8")
            git("add", "-A")
            git("commit", "-q", "-m", "c%d" % n)
        r = subprocess.run([sys.executable, str(script)], cwd=str(tmp_path),
                           capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    return run


COMMITTED = {"2026-09-25": {"close": 4.81, "fetched_at": "x"},
             "2026-10-02": {"close": 4.83, "fetched_at": "x"}}


def test_ci_passes_a_history_that_only_grew(two_commits):
    code, out = two_commits(COMMITTED, dict(COMMITTED, **{
        "2026-10-09": {"close": 4.86, "fetched_at": "y"}}))
    assert code == 0, out
    assert "2 week(s) unchanged, 1 added" in out


def test_ci_passes_the_commit_that_introduces_the_history(two_commits):
    code, out = two_commits(None, COMMITTED)
    assert code == 0, out
    assert "nothing to compare" in out


@pytest.mark.parametrize("after", [
    dict(COMMITTED, **{"2026-09-25": {"close": 4.80, "fetched_at": "x"}}),
    dict(COMMITTED, **{"2026-09-25": {"close": 4.81, "fetched_at": "x",
                                      "observed": "2026-09-24"}}),
    {"2026-10-02": COMMITTED["2026-10-02"]},
    None,
], ids=["value changed", "stand-in day changed", "week removed",
        "file deleted"])
def test_ci_fails_a_commit_that_rewrites_a_committed_week(two_commits, after):
    code, out = two_commits(COMMITTED, after)
    assert code == 1, out
    assert "US2Y HISTORY REGRESSION" in out


# -- the committed panel -------------------------------------------------------

# The last weekly file written with 2YY=F under "US2Y". Every file up to and
# including it can only ever get its Treasury 2-year from the history file,
# so this set is fixed and the assertion below cannot be broken by a later
# Friday going wrong.
LAST_FUTURES_WEEK = "2026-10-02"


def test_every_pre_cutover_week_has_a_committed_treasury_2y():
    weekly = ROOT / "data" / "weekly"
    series, problem = snapshot.load_us2y_history(
        snapshot.us2y_history_path(str(weekly)))
    assert problem is None
    weeks = sorted(f.stem for f in weekly.glob("*.json")
                   if not f.name.endswith(".corrected.json")
                   and f.stem <= LAST_FUTURES_WEEK)
    assert len(weeks) == 113
    assert [w for w in weeks if w not in series] == []


def test_the_committed_history_is_the_treasury_series_not_the_future():
    """Spot values against Treasury's published rows, and against the marks
    the weekly files hold for the same Fridays."""
    weekly = ROOT / "data" / "weekly"
    series, _ = snapshot.load_us2y_history(
        snapshot.us2y_history_path(str(weekly)))
    assert series["2026-10-02"] == 4.83
    assert series["2026-09-25"] == 4.81
    assert series["2026-09-18"] == 4.76
    assert series["2024-08-09"] == 4.05

    def future(as_of):
        doc = json.loads((weekly / (as_of + ".json"))
                         .read_text(encoding="utf-8"))
        return doc["rates"]["US2Y"]["close"]

    assert future("2026-10-02") == 4.635
    assert future("2026-09-18") == 4.404, "36 bp under the cash yield"
