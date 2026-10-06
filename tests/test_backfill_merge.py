"""Merge semantics: adding tickers to a week without disturbing it.

Adding a ticker to a past week and rewriting that week are different
operations. The script only had the second one, so `--only <44> --force`
deleted 243 names from 107 files and the job reported success.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from conftest import ROOT, SCRIPTS, weekly_doc

import backfill_weekly as bf  # noqa: E402  (conftest stubs the provider)
from scan_pipeline.config.tickers import BACKFILL_44_TICKERS  # noqa: E402

BACKFILL = SCRIPTS / "backfill_weekly.py"
EXISTING = ["SPY", "AAPL", "MSFT", "XOM", "JNJ"]
FRIDAY = date(2026, 8, 21)


def history_for(tickers, close=50.0):
    """The shape slice_week() reads: (dates, closes, volumes) per ticker.

    Dates are date objects, not ISO strings -- slice_week bisects them.
    """
    return {t: ([FRIDAY], [close], [123456]) for t in tickers}


def write_week(tmp_path, doc, name="2026-08-21.json") -> Path:
    d = tmp_path / "weekly"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    return p


def test_merge_leaves_every_other_series_bit_identical(tmp_path):
    doc = weekly_doc("2026-08-21", EXISTING)
    before = json.loads(json.dumps(doc))
    p = write_week(tmp_path, doc)

    bf.merge_into_existing(FRIDAY, ["PLTR"], history_for(["PLTR"]), str(p))

    after = json.loads(p.read_text(encoding="utf-8"))
    for ticker, bar in before["series"].items():
        assert after["series"][ticker] == bar
    assert "PLTR" in after["series"]
    assert len(after["series"]) == len(before["series"]) + 1


def test_merge_does_not_restamp_the_file_level_anchor(tmp_path):
    """Restamping would relabel every untouched series with a fetch that
    never happened to it."""
    doc = weekly_doc("2026-08-21", EXISTING, fetched_at="2026-08-22T16:01:01Z")
    p = write_week(tmp_path, doc)

    bf.merge_into_existing(FRIDAY, ["PLTR"], history_for(["PLTR"]), str(p))

    after = json.loads(p.read_text(encoding="utf-8"))
    assert after["fetched_at"] == "2026-08-22T16:01:01Z"
    assert after["source"] == "yahoo"


def test_merged_names_carry_their_own_anchor(tmp_path):
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    bf.merge_into_existing(FRIDAY, ["PLTR"], history_for(["PLTR"]), str(p))

    prov = json.loads(p.read_text(encoding="utf-8"))["provenance"]["series"]
    assert set(prov) == {"PLTR"}
    assert prov["PLTR"]["source"] == bf.BACKFILL_SOURCE
    assert prov["PLTR"]["fetched_at"].endswith("Z")


def test_merged_bars_are_normalised_like_scanned_ones(tmp_path):
    """The first cut wrote the raw slice and landed 179.94000244140625 beside
    the panel's rounded closes."""
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    bf.merge_into_existing(FRIDAY, ["PLTR"],
                           history_for(["PLTR"], close=179.94000244140625), str(p))

    bar = json.loads(p.read_text(encoding="utf-8"))["series"]["PLTR"]
    assert bar["close"] == 179.94
    assert isinstance(bar["volume"], int)


def test_missing_is_honest_in_both_directions(tmp_path):
    doc = weekly_doc("2026-08-21", EXISTING)
    doc["missing"] = [{"ticker": "PLTR", "reason": "was not fetched"}]
    p = write_week(tmp_path, doc)

    # PLTR now has a bar; GHOST does not.
    bf.merge_into_existing(FRIDAY, ["PLTR", "GHOST"], history_for(["PLTR"]), str(p))

    after = json.loads(p.read_text(encoding="utf-8"))
    listed = {m["ticker"] for m in after["missing"]}
    assert "PLTR" not in listed, "a ticker we just filled is no longer missing"
    assert "GHOST" in listed, "a ticker we could not fetch is listed, not absent"


def test_merging_into_the_wrong_week_is_refused(tmp_path):
    p = write_week(tmp_path, weekly_doc("2026-08-14", EXISTING),
                   name="2026-08-14.json")
    with pytest.raises(SystemExit, match="refusing to merge"):
        bf.merge_into_existing(FRIDAY, ["PLTR"], history_for(["PLTR"]), str(p))


def test_no_provenance_block_when_nothing_merged(tmp_path):
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    bf.merge_into_existing(FRIDAY, ["GHOST"], {}, str(p))
    assert "provenance" not in json.loads(p.read_text(encoding="utf-8"))


# --- A name the week already holds.
#     Every test above merges a ticker the week does not have. Until
#     2026-10-06 nothing asked what happens to one it does, and the answer
#     was that its committed bar was written over.
def test_merge_never_replaces_a_bar_the_week_already_holds(tmp_path):
    """`--only AAPL --merge` on a week that has AAPL wrote the freshly
    fetched bar over the committed one and stamped it in provenance.series.
    A fresh fetch is adjusted to a later date, so it is a different number
    for any name that has paid a dividend or split since, and the count of
    series does not move, which is all panel_guard and CI compare."""
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    committed = p.read_bytes()

    rec = bf.merge_into_existing(FRIDAY, ["AAPL"],
                                 history_for(["AAPL"], close=50.0), str(p))

    after = json.loads(p.read_text(encoding="utf-8"))
    assert after["series"]["AAPL"] == {"close": 100.0, "volume": 1_000_000}
    assert "provenance" not in after, "nothing was added, so no anchor"
    assert p.read_bytes() == committed, "nothing to add, so nothing is written"
    assert rec["present"] == ["AAPL"] and rec["added"] == []


def test_a_name_merged_earlier_keeps_the_anchor_it_was_merged_with(tmp_path):
    """The second merge run to name a ticker. Its bar and its stamp are the
    record of the first: restamped, the file would say the week's PLTR was
    fetched on a day it was not."""
    doc = weekly_doc("2026-08-21", EXISTING + ["PLTR"])
    doc["series"]["PLTR"] = {"close": 179.94, "volume": 61_000_000}
    first = {"source": "yahoo-backfill", "fetched_at": "2026-08-26T04:24:20Z"}
    doc["provenance"] = {"series": {"PLTR": dict(first)}}
    p = write_week(tmp_path, doc)

    bf.merge_into_existing(FRIDAY, ["PLTR", "VST"],
                           history_for(["PLTR", "VST"], close=50.0), str(p))

    after = json.loads(p.read_text(encoding="utf-8"))
    assert after["series"]["PLTR"] == {"close": 179.94, "volume": 61_000_000}
    assert after["provenance"]["series"]["PLTR"] == first
    assert after["series"]["VST"] == {"close": 50.0, "volume": 123456}
    assert after["provenance"]["series"]["VST"]["fetched_at"] == bf.RUN_TS


def test_a_name_the_week_holds_is_not_listed_missing_when_the_fetch_is_empty(
        tmp_path):
    """The provider keeps one bar of a delisted symbol, the last (AVB, EA).
    Named in a merge, such a ticker comes back with no bar for the week, and
    it went into `missing` beside the bar the week still held for it."""
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    committed = p.read_bytes()

    rec = bf.merge_into_existing(FRIDAY, ["AAPL"], {}, str(p))

    after = json.loads(p.read_text(encoding="utf-8"))
    assert after["missing"] == []
    assert "AAPL" in after["series"]
    assert p.read_bytes() == committed
    assert rec["present"] == ["AAPL"] and rec["absent"] == []


def test_a_held_name_keeps_its_missing_entry_when_the_file_is_rewritten(
        tmp_path):
    """Leaving a held name alone covers `missing` in the other direction too.
    A ticker in both `series` and `missing` is a contradiction no committed
    file has, and it is still not a merge's to settle: the run that adds
    PLTR rewrites the file and must not tidy AAPL's entry away with it."""
    doc = weekly_doc("2026-08-21", EXISTING)
    entry = {"ticker": "AAPL", "reason": "listed by an earlier writer"}
    doc["missing"] = [dict(entry)]
    p = write_week(tmp_path, doc)

    rec = bf.merge_into_existing(FRIDAY, ["AAPL", "PLTR"],
                                 history_for(["AAPL", "PLTR"], close=50.0),
                                 str(p))

    after = json.loads(p.read_text(encoding="utf-8"))
    assert rec["changed"] and rec["added"] == ["PLTR"]
    assert after["missing"] == [entry]
    assert after["series"]["AAPL"] == {"close": 100.0, "volume": 1_000_000}
    assert set(after["provenance"]["series"]) == {"PLTR"}


# --- The command line, where the incident actually happened.
#     These run main() in-process rather than shelling out: a subprocess gets
#     a fresh interpreter without conftest's provider stub, so it would need
#     yfinance installed to reach the argument check. The guard is what is
#     under test, not the import.
def guard(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["backfill_weekly.py", *args])
    with pytest.raises(SystemExit) as excinfo:
        bf.main()
    return excinfo


def test_only_with_force_is_refused_outright(monkeypatch, capsys):
    guard(monkeypatch, "--out", "data", "--only", "PLTR", "--force")
    err = capsys.readouterr().err
    assert "deleting every other series" in err
    assert "2026-08-26" in err


def test_merge_without_only_is_refused(monkeypatch, capsys):
    guard(monkeypatch, "--out", "data", "--merge")
    assert "pass --only" in capsys.readouterr().err


def test_full_universe_force_reaches_the_plan(monkeypatch, capsys):
    """--force is correct for its actual purpose: a whole-file rewrite, so it
    must get past the guard rather than being refused with it."""
    monkeypatch.setattr(sys, "argv",
                        ["backfill_weekly.py", "--out", "data", "--force",
                         "--dry-run", "--start", "2026-08-21",
                         "--end", "2026-08-21"])
    try:
        bf.main()
    except SystemExit as e:      # argparse refusal would exit 2 here
        assert "deleting every other series" not in capsys.readouterr().err
        assert e.code != 2, "a full-universe --force must not hit the guard"
    out = capsys.readouterr().out
    assert "deleting every other series" not in out


# --- A name the week already holds, at the command line: what the run says
#     and how it exits. The script printed "N refreshed" and exited 0.
WEEK = ("--start", "2026-08-21", "--end", "2026-08-21")
COMMITTED_BAR = {"close": 100.0, "volume": 1_000_000}


def run_main(monkeypatch, *args) -> int:
    monkeypatch.setattr(sys, "argv", ["backfill_weekly.py", *args])
    return bf.main()


def provider(monkeypatch, bars):
    """Stand in for the download: {ticker: {day: close}}. A ticker or a day
    it does not name has no bar, as with a pre-IPO or delisted symbol."""
    def download(tickers, first, last):
        out = {}
        for t in tickers:
            days = sorted(bars.get(t, {}))
            out[t] = (days, [bars[t][d] for d in days], [123456] * len(days))
        return out
    monkeypatch.setattr(bf, "download_equity_history", download)


def no_provider(monkeypatch):
    def download(*args, **kwargs):
        raise AssertionError("nothing to add, so nothing is downloaded")
    monkeypatch.setattr(bf, "download_equity_history", download)


def test_a_run_adds_what_is_missing_and_says_what_it_left_alone(
        monkeypatch, capsys, tmp_path):
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    provider(monkeypatch, {"AAPL": {FRIDAY: 50.0}, "PLTR": {FRIDAY: 50.0}})

    code = run_main(monkeypatch, "--out", str(tmp_path),
                    "--only", "AAPL,PLTR", "--merge", *WEEK)

    assert code == 0
    after = json.loads(p.read_text(encoding="utf-8"))
    assert after["series"]["AAPL"] == COMMITTED_BAR
    assert after["series"]["PLTR"] == {"close": 50.0, "volume": 123456}
    assert set(after["provenance"]["series"]) == {"PLTR"}
    out = capsys.readouterr().out
    assert ("already in the week, left alone: 1 of the 2 (ticker, week) "
            "pair(s) named") in out
    assert "in all 1 week(s): AAPL" in out
    assert "merged +1 new, 1 already present (left alone), 0 absent" in out
    assert "files_written=1 files_unchanged=0" in out
    assert "ALREADY PRESENT: 1 bar(s)" in out
    assert "NOTHING MERGED" not in out


def test_one_run_fills_the_early_weeks_of_a_name_later_weeks_carry(
        monkeypatch, capsys, tmp_path):
    """Why a held name is skipped and not a reason to refuse the run. A
    ticker that joined the feed part-way is in the Friday job's files from
    then on and in none before, and the backfill of its history is one
    --merge across both."""
    early = write_week(tmp_path, weekly_doc("2026-08-14", EXISTING),
                       name="2026-08-14.json")
    late = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING + ["PLTR"]))
    committed = late.read_bytes()
    provider(monkeypatch, {"PLTR": {date(2026, 8, 14): 48.0, FRIDAY: 50.0}})

    code = run_main(monkeypatch, "--out", str(tmp_path), "--only", "PLTR",
                    "--merge", "--start", "2026-08-14", "--end", "2026-08-21")

    assert code == 0
    assert late.read_bytes() == committed, "the week that had it is untouched"
    filled = json.loads(early.read_text(encoding="utf-8"))
    assert filled["series"]["PLTR"] == {"close": 48.0, "volume": 123456}
    out = capsys.readouterr().out
    assert "in 1 of 2 week(s): PLTR (2026-08-21)" in out
    assert "files_written=1 files_unchanged=1" in out
    assert "[file unchanged]" in out


@pytest.mark.parametrize("dry", [[], ["--dry-run"]], ids=["run", "dry-run"])
def test_a_run_with_nothing_to_add_stops_before_it_downloads(
        monkeypatch, capsys, tmp_path, dry):
    """Every named ticker is in every week, which the files show without a
    fetch. The workflow defaults to a dry run, and a plan that can do
    nothing must not print as one."""
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    committed = p.read_bytes()
    no_provider(monkeypatch)

    code = run_main(monkeypatch, "--out", str(tmp_path),
                    "--only", "AAPL,MSFT", "--merge", *WEEK, *dry)

    assert code == 2
    assert p.read_bytes() == committed
    out = capsys.readouterr().out
    assert ("NOTHING TO MERGE: all 2 named ticker(s) already have a bar in "
            "all 1 week(s) on file from 2026-08-21 to 2026-08-21") in out
    assert "no tool writes one for an equity bar yet" in out
    assert "rebuild_corrections.py" in out
    assert "have no file" not in out
    assert "dry-run OK" not in out


@pytest.mark.parametrize("dry", [[], ["--dry-run"]], ids=["run", "dry-run"])
def test_a_friday_with_no_file_does_not_make_it_a_plan(
        monkeypatch, capsys, tmp_path, dry):
    """One Friday of the range has no file. A run restricted with --only
    starts no week, so there is still nothing a fetch could add, and the
    dry run printed "dry-run OK" for a run that could only end in exit 2.

    The exit status and the untouched panel are the contract. Whether the
    words come from here or from a refusal ahead of this one, of the
    restricted run over a week with no file, is not."""
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    committed = p.read_bytes()
    no_provider(monkeypatch)

    try:
        code = run_main(monkeypatch, "--out", str(tmp_path), "--only", "AAPL",
                        "--merge", "--start", "2026-08-14",
                        "--end", "2026-08-21", *dry)
    except SystemExit as stop:
        code = stop.code

    assert code == 2
    assert p.read_bytes() == committed
    assert [f.name for f in (tmp_path / "weekly").iterdir()] == [
        "2026-08-21.json"], "no week was started"
    said = capsys.readouterr()
    assert "2026-08-14" in said.out + said.err, "the week with no file"
    assert "dry-run OK" not in said.out


@pytest.mark.parametrize("dry", [[], ["--dry-run"]], ids=["run", "dry-run"])
def test_the_plan_refuses_a_file_that_is_not_its_week(
        monkeypatch, tmp_path, dry):
    """The plan reads each week's series to say what a merge leaves alone,
    so it holds the file to the check the merge makes. Without it this run
    said "nothing to merge" about 2026-08-21 on the strength of the bars of
    2026-08-14, filed under the wrong name."""
    write_week(tmp_path, weekly_doc("2026-08-14", EXISTING))
    no_provider(monkeypatch)

    with pytest.raises(SystemExit, match="refusing to merge into a file "
                                         "that is not the week"):
        run_main(monkeypatch, "--out", str(tmp_path),
                 "--only", "AAPL", "--merge", *WEEK, *dry)


def test_a_week_that_does_not_parse_is_refused_in_words(
        monkeypatch, tmp_path):
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    p.write_text('{"as_of": "2026-08-21", "series": {', encoding="utf-8")
    broken = p.read_bytes()
    no_provider(monkeypatch)

    with pytest.raises(SystemExit, match="does not parse as JSON"):
        run_main(monkeypatch, "--out", str(tmp_path),
                 "--only", "PLTR", "--merge", "--dry-run", *WEEK)
    assert p.read_bytes() == broken


def test_a_dry_run_says_what_the_merge_would_leave_alone(
        monkeypatch, capsys, tmp_path):
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    committed = p.read_bytes()
    no_provider(monkeypatch)

    code = run_main(monkeypatch, "--out", str(tmp_path),
                    "--only", "AAPL,PLTR", "--merge", "--dry-run", *WEEK)

    assert code == 0
    assert p.read_bytes() == committed
    out = capsys.readouterr().out
    assert "left alone: 1 of the 2 (ticker, week) pair(s) named" in out
    assert "in all 1 week(s): AAPL" in out
    assert "could be added, if the provider has a bar: 1 pair(s)" in out
    assert "dry-run OK" in out


def test_a_run_that_fetched_and_still_changed_nothing_exits_2(
        monkeypatch, capsys, tmp_path):
    """BACKFILL_44.md's own command run a second time, in small: one name
    the week holds and one with no bar that week, already in `missing` (as
    SPCX is before its IPO). Not every name is in every week, so only the
    fetch can tell that there is nothing to add."""
    doc = weekly_doc("2026-08-21", EXISTING)
    doc["missing"] = [{"ticker": "SPCX",
                       "reason": bf.MISSING_REASON % "2026-08-21"}]
    p = write_week(tmp_path, doc)
    committed = p.read_bytes()
    provider(monkeypatch, {"AAPL": {FRIDAY: 50.0}})

    code = run_main(monkeypatch, "--out", str(tmp_path),
                    "--only", "AAPL,SPCX", "--merge", *WEEK)

    assert code == 2
    assert p.read_bytes() == committed
    out = capsys.readouterr().out
    assert ("merged +0 new, 1 already present (left alone), 1 absent "
            "-> series=5 [file unchanged]") in out
    assert "files_written=0 files_unchanged=1" in out
    assert "NOTHING MERGED: no file was changed" in out
    assert "NOTHING TO MERGE" not in out, "that one is said before a fetch"


def test_a_run_that_left_nothing_alone_and_found_nothing_still_exits_0(
        monkeypatch, capsys, tmp_path):
    """Exit 2 is for a run that left a named ticker alone. A name the week
    never had, with no bar and already in `missing`, is the fetch finding
    what it found last time: nothing changes and nothing was skipped, and
    that run exited 0 before this rule and does now."""
    doc = weekly_doc("2026-08-21", EXISTING)
    doc["missing"] = [{"ticker": "SPCX",
                       "reason": bf.MISSING_REASON % "2026-08-21"}]
    p = write_week(tmp_path, doc)
    committed = p.read_bytes()
    provider(monkeypatch, {})

    code = run_main(monkeypatch, "--out", str(tmp_path),
                    "--only", "SPCX", "--merge", *WEEK)

    assert code == 0
    assert p.read_bytes() == committed
    out = capsys.readouterr().out
    assert "files_written=0 files_unchanged=1" in out
    assert "NOTHING" not in out and "ALREADY PRESENT" not in out


def test_a_new_missing_entry_is_a_change_and_the_run_exits_0(
        monkeypatch, capsys, tmp_path):
    """A name the fetch could not find goes into `missing` with a reason,
    and that is a record the workflow has to reach its commit step to
    keep. Skipping another name in the same run does not make it nothing."""
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    provider(monkeypatch, {"AAPL": {FRIDAY: 50.0}})

    code = run_main(monkeypatch, "--out", str(tmp_path),
                    "--only", "AAPL,GHOST", "--merge", *WEEK)

    assert code == 0
    after = json.loads(p.read_text(encoding="utf-8"))
    assert [m["ticker"] for m in after["missing"]] == ["GHOST"]
    assert after["series"]["AAPL"] == COMMITTED_BAR
    out = capsys.readouterr().out
    assert "files_written=1 files_unchanged=0" in out
    assert "NOTHING MERGED" not in out


def test_force_does_not_make_a_merge_replace_a_bar(
        monkeypatch, capsys, tmp_path):
    """--force beside --merge was accepted and ignored. It still is, and
    says so: it is the flag someone reaches for to push a bar through."""
    p = write_week(tmp_path, weekly_doc("2026-08-21", EXISTING))
    provider(monkeypatch, {"AAPL": {FRIDAY: 50.0}, "PLTR": {FRIDAY: 50.0}})

    code = run_main(monkeypatch, "--out", str(tmp_path),
                    "--only", "AAPL,PLTR", "--merge", "--force", *WEEK)

    assert code == 0
    after = json.loads(p.read_text(encoding="utf-8"))
    assert after["series"]["AAPL"] == COMMITTED_BAR
    assert len(after["series"]) == len(EXISTING) + 1
    assert "--force has no effect with --merge" in capsys.readouterr().out


def test_what_is_left_alone_is_grouped_by_how_many_weeks_hold_it():
    a, b, c = date(2026, 8, 7), date(2026, 8, 14), date(2026, 8, 21)
    held = {"MSFT": [a, b, c], "AAPL": [a, b, c], "SPCX": [b, c], "PLTR": [c]}
    assert bf.describe_held(held, 3) == [
        "  in all 3 week(s): AAPL, MSFT",
        "  in 2 of 3 week(s): SPCX (2026-08-14..2026-08-21)",
        "  in 1 of 3 week(s): PLTR (2026-08-21)",
    ]


def test_running_the_44_ticker_merge_again_changes_no_committed_bar(
        monkeypatch, capsys, tmp_path):
    """The run this rule is for: BACKFILL_44.md's command, against a copy
    of the committed panel, with a provider that hands back another close
    for every bar the 44 already have there. Until 2026-10-06 that wrote
    over every one of them (4,612 on that day's panel) and exited 0, and
    panel_guard and the feed gate passed the result: no count had moved."""
    first, last = date(2024, 8, 9), date(2026, 8, 21)
    shutil.copytree(ROOT / "data" / "weekly", tmp_path / "weekly")
    committed = {p.name: p.read_bytes()
                 for p in (tmp_path / "weekly").iterdir()}
    names = sorted(BACKFILL_44_TICKERS)
    bars = {t: {} for t in names}
    for name, raw in committed.items():
        if not name.endswith(".json") or ".corrected" in name:
            continue
        doc = json.loads(raw)
        day = date.fromisoformat(doc["as_of"])
        if not first <= day <= last:
            continue
        for t in names:
            if t in doc["series"]:
                bars[t][day] = round(doc["series"][t]["close"] * 0.99, 4)
    held = sum(len(days) for days in bars.values())
    assert held > 4000, "the 44 are in the committed weeks this reads"
    provider(monkeypatch, bars)

    code = run_main(monkeypatch, "--out", str(tmp_path),
                    "--only", ",".join(names), "--merge",
                    "--start", first.isoformat(), "--end", last.isoformat())

    assert code == 2
    after = {p.name: p.read_bytes() for p in (tmp_path / "weekly").iterdir()}
    assert after == committed, "not one byte of the panel changed"
    out = capsys.readouterr().out
    assert "ALREADY PRESENT: %d bar(s)" % held in out
    assert "NOTHING MERGED: no file was changed" in out
