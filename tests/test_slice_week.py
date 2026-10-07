"""A ticker's bar is the one dated the file's session, or the ticker is in
`missing`.

Until 2026-10-07 the backfill writer's slice_week took a ticker's last bar
on or before the Friday, anywhere in the Mon..Fri week. A name with no bar
on the session -- halted, delisted mid-week, a gap at the provider -- went
into the file as an earlier session's close under the Friday's date. An
audit of every committed equity bar found it had happened once: EA in
2026-08-07.json is its close of Tuesday 2026-08-04, on volume 0, the last
session before it was taken private.

Owner decision 2026-10-06 (DATA_FEED.md sec.1b): `missing`, as the weekly
job has always done. No new key; a gap stays a gap.

The closes and volumes here are made up. The dates are the real ones.
"""
from __future__ import annotations

import importlib.util
import json
from datetime import date as D

import pytest

from conftest import ROOT, weekly_doc

import backfill_weekly as bf  # noqa: E402  (conftest stubs the provider)
from scan_pipeline import snapshot  # noqa: E402

QUIET = {"rates": {}, "vol": {}, "commodities": {}, "fx": {}, "missing": []}

# The week EA left the market: Monday 2026-08-03 to Friday 2026-08-07.
WEEK = [D(2026, 8, 3), D(2026, 8, 4), D(2026, 8, 5), D(2026, 8, 6),
        D(2026, 8, 7)]
FRIDAY = WEEK[-1]
EA = (WEEK[:2], [208.0, 209.70], [5_000_000, 0])     # its last two sessions

# Christmas week 2026: the Friday is the holiday, Thursday the last session.
XMAS = D(2026, 12, 25)
EVE = D(2026, 12, 24)
XMAS_WEEK = [D(2026, 12, 21), D(2026, 12, 22), D(2026, 12, 23), EVE]
AFTER = D(2026, 12, 28)


def bars(days, close=50.0, volume=1000):
    days = sorted(days)
    return (days, [close] * len(days), [volume] * len(days))


def mirror_module():
    """The copy under scan_pipeline, loaded by path: nothing may import it
    by name (tests/test_corrections_and_feed.py holds that)."""
    path = ROOT.joinpath("scan_pipeline", "scripts", "backfill_weekly.py")
    spec = importlib.util.spec_from_file_location("mirror_slice_week", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=["scripts", "mirror"])
def writer(request, monkeypatch):
    """Both copies of the backfill writer, each with its instruments and
    its pauses stubbed out."""
    module = bf if request.param == "scripts" else mirror_module()
    monkeypatch.setattr(module.snapshot_macro, "fetch_special_instruments",
                        lambda friday: dict(QUIET), raising=False)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    return module


def put(tmp_path, doc):
    weekly = tmp_path / "weekly"
    weekly.mkdir(parents=True, exist_ok=True)
    path = weekly / (doc["as_of"] + ".json")
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8",
                    newline="\n")
    return path


# -- the slice -----------------------------------------------------------------

def test_the_bar_dated_the_session_and_no_other(writer):
    hist = (WEEK, [1.0, 2.0, 3.0, 4.0, 5.0], [10, 20, 30, 40, 50])
    assert writer.slice_week(hist, FRIDAY) == \
        ({"close": 5.0, "volume": 50}, FRIDAY)
    assert writer.slice_week(hist, WEEK[3]) == \
        ({"close": 4.0, "volume": 40}, WEEK[3])


def test_no_bar_on_the_session_is_no_bar(writer):
    """EA's Tuesday close is not its Friday close. What comes back instead
    is the date of the last bar there is, for the reason to name."""
    assert writer.slice_week(EA, FRIDAY) == (None, D(2026, 8, 4))
    # last week's bar is no bar for this week either, and is still named
    assert writer.slice_week(bars([D(2026, 7, 31)]), FRIDAY) == \
        (None, D(2026, 7, 31))
    # nothing before the session at all: pre-IPO, or never served
    assert writer.slice_week(([], [], []), FRIDAY) == (None, None)
    assert writer.slice_week(bars([D(2026, 8, 10)]), FRIDAY) == (None, None)


def test_the_reason_says_what_was_asked_and_what_there_is(writer):
    assert writer.missing_reason(FRIDAY, D(2026, 8, 4)) == \
        "no bar dated 2026-08-07; its last bar before that is dated 2026-08-04"
    assert writer.missing_reason(FRIDAY, None) == \
        "no bar dated 2026-08-07, and none before it in the download"
    for last in (D(2026, 8, 4), None):
        assert "likely" not in writer.missing_reason(FRIDAY, last)


# -- a week written whole ------------------------------------------------------

def test_a_name_that_stopped_trading_midweek_is_missing_not_filed(
        tmp_path, writer):
    """2026-08-07.json as it would be written now. The committed file holds
    EA at 209.70 on volume 0 under the Friday's date; it is not edited."""
    history = {"SPY": bars(WEEK), "AAPL": bars(WEEK), "EA": EA}
    rec = writer.build_and_write(FRIDAY, ["AAPL", "EA", "SPY"], history,
                                 str(tmp_path))
    doc = json.loads(open(rec["path"], encoding="utf-8").read())
    assert sorted(doc["series"]) == ["AAPL", "SPY"]
    assert doc["missing"] == [{
        "ticker": "EA",
        "reason": "no bar dated 2026-08-07; its last bar before that is "
                  "dated 2026-08-04"}]
    assert "session_note" not in doc


def test_a_name_with_no_bar_at_all_is_missing_with_the_other_reason(
        tmp_path, writer):
    history = {"SPY": bars(WEEK), "SPCX": ([], [], [])}
    rec = writer.build_and_write(FRIDAY, ["SPCX", "SPY"], history,
                                 str(tmp_path))
    assert rec["doc"]["missing"] == [{
        "ticker": "SPCX",
        "reason": "no bar dated 2026-08-07, and none before it in the "
                  "download"}]


def test_in_a_holiday_week_the_session_is_the_day_the_file_names(
        tmp_path, writer, monkeypatch):
    """Thursday's bars, and the file says so. A name whose last bar is
    Wednesday's did not trade on that session either, and is missing: no
    ticker gets a day of its own."""
    monkeypatch.setattr(snapshot, "witness_listing", lambda friday: {
        day: 1.0 for day in XMAS_WEEK + [AFTER]})
    history = {"SPY": bars(XMAS_WEEK + [AFTER]),
               "AAPL": bars(XMAS_WEEK + [AFTER]),
               "HALT": bars(XMAS_WEEK[:3])}
    rec = writer.build_and_write(XMAS, ["AAPL", "HALT", "SPY"], history,
                                 str(tmp_path))
    doc = json.loads(open(rec["path"], encoding="utf-8").read())
    assert doc["session_note"] == "Friday holiday; bars from 2026-12-24"
    assert sorted(doc["series"]) == ["AAPL", "SPY"]
    assert doc["missing"] == [{
        "ticker": "HALT",
        "reason": "no bar dated 2026-12-24; its last bar before that is "
                  "dated 2026-12-23"}]


# -- a name merged into a week on file -----------------------------------------

def test_a_merge_does_not_file_an_earlier_session_under_the_friday(
        tmp_path, writer):
    """`--only EQR --merge` over 2026-08-21 put EQR's close of Monday
    2026-08-17 in that week's file. Whatever else refuses such a run, the
    slice no longer hands the bar over."""
    friday = D(2026, 8, 21)
    path = put(tmp_path, weekly_doc("2026-08-21", ["SPY", "AAPL"]))
    rec = writer.merge_into_existing(
        friday, ["OLDCO"], {"OLDCO": bars([D(2026, 8, 17)])}, str(path))
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert "OLDCO" not in doc["series"] and rec["added"] == []
    assert doc["missing"] == [{
        "ticker": "OLDCO",
        "reason": "no bar dated 2026-08-21; its last bar before that is "
                  "dated 2026-08-17"}]


def test_a_merge_into_a_holiday_week_takes_the_bar_of_the_named_session(
        tmp_path, writer):
    """The file holds Thursday. A merged name's Thursday bar is that
    session's, and goes in; one with only Wednesday's does not."""
    doc = weekly_doc("2026-12-25", ["SPY"])
    doc["session_note"] = "Friday holiday; bars from 2026-12-24"
    path = put(tmp_path, doc)
    rec = writer.merge_into_existing(
        XMAS, ["HALT", "PLTR"],
        {"PLTR": (XMAS_WEEK, [1.0, 2.0, 3.0, 4.0], [10, 20, 30, 40]),
         "HALT": bars(XMAS_WEEK[:3])}, str(path))
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["series"]["PLTR"] == {"close": 4.0, "volume": 40}
    assert rec["added"] == ["PLTR"] and "HALT" not in after["series"]
    assert after["missing"] == [{
        "ticker": "HALT",
        "reason": "no bar dated 2026-12-24; its last bar before that is "
                  "dated 2026-12-23"}]
    assert after["session_note"] == doc["session_note"]


@pytest.mark.parametrize("note", [
    "holiday", "Friday holiday; bars from Thursday",
    "Friday holiday; bars from 2026-12-25",      # the Friday is no stand-in
    "Friday holiday; bars from 2026-12-18",      # another week's session
    "Friday holiday; bars from 2026-13-45", 20261224, "", None])
def test_a_week_whose_session_cannot_be_read_is_not_merged_into(
        tmp_path, writer, note):
    """Taken for 'the Friday', a holiday week would get no bar for any name
    merged into it, and each would be listed in `missing` beside a session
    it did trade on. A null note is one of these: the writer leaves the key
    out of a week that holds its Friday, and the gate fails a null."""
    doc = weekly_doc("2026-12-25", ["SPY"])
    doc["session_note"] = note
    path = put(tmp_path, doc)
    before = path.read_bytes()
    with pytest.raises(SystemExit, match="session cannot be read"):
        writer.merge_into_existing(XMAS, ["PLTR"],
                                   {"PLTR": bars(XMAS_WEEK)}, str(path))
    assert path.read_bytes() == before


def test_a_week_with_no_note_holds_its_friday(writer):
    assert writer.file_session({"as_of": "2026-08-07"}, FRIDAY) == FRIDAY
    assert writer.file_session(
        {"session_note": "Friday holiday; bars from 2026-12-24"}, XMAS) == EVE


def test_every_committed_week_says_which_session_it_holds(writer):
    """All of them parse, and the five holiday weeks name a day of their own
    week. A merge into any committed week knows which bar to take."""
    notes = {}
    for path in sorted((ROOT / "data" / "weekly").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        friday = D.fromisoformat(doc["as_of"])
        session = writer.file_session(doc, friday, path.name)
        if session != friday:
            notes[doc["as_of"]] = session.isoformat()
    assert notes == {"2025-04-18": "2025-04-17", "2025-07-04": "2025-07-03",
                     "2026-04-03": "2026-04-02", "2026-06-19": "2026-06-18",
                     "2026-07-03": "2026-07-02"}


def test_a_name_the_week_holds_is_never_listed_missing(tmp_path, writer):
    """EA in 2026-08-07.json. The provider keeps one bar of a delisted
    symbol, so a fetch for the week comes back with nothing dated its
    session. The week holds a bar for it all the same, and `missing` beside
    a bar says two things about one name. (The mirror still fetches a held
    name again; with the slice held to the session it listed this one.)"""
    doc = weekly_doc("2026-08-07", ["SPY", "EA"])
    doc["series"]["EA"] = {"close": 209.7, "volume": 0}
    path = put(tmp_path, doc)
    before = json.loads(path.read_text(encoding="utf-8"))
    writer.merge_into_existing(FRIDAY, ["EA"], {"EA": EA}, str(path))
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["series"]["EA"] == before["series"]["EA"]
    assert after["missing"] == before["missing"] == []


# -- the plan, and the volume rule ---------------------------------------------

def bad_note_panel(tmp_path, bad="2026-12-25"):
    """Four ordinary weeks and Christmas week, whose note cannot be read."""
    weekly = tmp_path / "weekly"
    for as_of in ("2026-12-04", "2026-12-11", "2026-12-18", "2026-12-25"):
        doc = weekly_doc(as_of, ["SPY", "AAPL"])
        if as_of == bad:
            doc["session_note"] = "thin trade"
        put(tmp_path, doc)
    return weekly


def test_the_plan_refuses_a_week_whose_session_it_cannot_read(tmp_path):
    """Before any download, so a dry run refuses it too. The note is in the
    file; a dry run that printed OK over it would be a plan the real run
    cannot carry out."""
    weekly = bad_note_panel(tmp_path)
    fridays = [D(2026, 12, 18), XMAS]
    with pytest.raises(SystemExit, match="2026-12-25.json has session_note"):
        bf.held_already(str(weekly), fridays, ["PLTR"])
    assert bf.held_already(str(weekly), fridays[:1], ["AAPL"]) == {
        "AAPL": [D(2026, 12, 18)]}


def test_the_volume_rule_reads_the_session_only_of_a_week_in_the_run(
        tmp_path):
    """It reads the whole panel for the weeks a pair already shares. A week
    outside the run whose note cannot be read has nothing to add to that
    count and is the feed gate's to report; inside the run it stops the
    merge, and the line names the file."""
    weekly = bad_note_panel(tmp_path)
    history = {"PLTR": bars([D(2026, 12, 4), D(2026, 12, 11)])}
    assert bf.same_bars_refusals(
        str(weekly), [D(2026, 12, 4), D(2026, 12, 11)], ["PLTR"],
        history) == []
    with pytest.raises(SystemExit, match="2026-12-25.json has session_note"):
        bf.same_bars_refusals(str(weekly), [XMAS], ["PLTR"], history)


# -- the committed panel -------------------------------------------------------

def test_the_one_committed_case_is_still_as_it_was_written():
    """A weekly file is an observation and is not edited. The record of
    what EA's bar is lives in macro/series_audit.json."""
    doc = json.loads((ROOT / "data" / "weekly" / "2026-08-07.json").read_text(
        encoding="utf-8"))
    assert doc["series"]["EA"] == {"close": 209.7, "volume": 0}


def test_the_note_both_copies_read_is_the_writers_own():
    """The mirror spells the note out, because it writes it itself; held
    here to the constant the weekly writer and the gate use."""
    mirror = mirror_module()
    assert mirror._SESSION_NOTE.pattern == bf._SESSION_NOTE.pattern
    assert bf._SESSION_NOTE.match(snapshot.SESSION_NOTE % "2026-12-24")
