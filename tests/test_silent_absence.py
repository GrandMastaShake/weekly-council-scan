"""A name that is simply not there.

2024-08-09.json was started on 2026-08-26 by a backfill of 44 named tickers
and filled the next day with the 277 of STOCK_UNIVERSE. Neither list had an
index or sector ETF in it. The file sat in the panel without them and passed
every gate, because a missing name fails nothing in the file it is missing
from, until the session-witness rule asked every file for SPY
(tests/test_weekly_session.py). That rule asks for one name.

DATA_FEED.md sec.1: `missing` is required and never empty by omission. This
is the check that asks for the rest, by comparing a week with the panel
around it.

It is the first file, which is why the obvious rule does not find it. "In
the week before and the week after, but not here" needs a week before. So
the sixteen ETFs are held in every week, and every other name between the
first week that carries it and the last.
"""
from __future__ import annotations

import json
import subprocess
import sys

from conftest import ROOT, SCRIPTS, weekly_doc

import truth_check as tc  # noqa: E402
from scan_pipeline import snapshot  # noqa: E402  (conftest stubs the provider)

ETFS = list(tc.INDEX_AND_SECTOR_ETFS)
STOCKS = ["AAPL", "JNJ", "XOM"]
FRIDAYS = ["2026-08-07", "2026-08-14", "2026-08-21", "2026-08-28",
           "2026-09-04"]


def week(as_of, stocks=STOCKS, etfs=ETFS, missing=()):
    doc = weekly_doc(as_of, list(etfs) + list(stocks))
    doc["missing"] = [{"ticker": t, "reason": "no bar dated " + as_of}
                      for t in missing]
    return doc


def full_panel(**overrides):
    """Five ordinary weeks, with the ones named in `overrides` replaced."""
    files = {day + ".json": week(day) for day in FRIDAYS}
    files.update(overrides)
    return files


def check(repo):
    rep = tc.Report()
    tc.check_silent_absence(repo, rep)
    return rep


def warns(rep):
    return [line for line in rep.lines if line.startswith("WARN")]


def test_the_gate_and_the_writer_agree_on_the_sixteen():
    """truth_check stays stdlib-only, so it repeats the names. They are the
    ones equity_universe() adds to every full write, and the only ones in
    `series` that market_state derives from."""
    etfs = set(snapshot.INDEX_TICKERS) | set(snapshot.SECTOR_TICKERS)
    assert set(tc.INDEX_AND_SECTOR_ETFS) == etfs
    assert len(tc.INDEX_AND_SECTOR_ETFS) == len(etfs) == 16
    assert etfs <= set(snapshot.equity_universe())


def test_an_ordinary_panel_is_quiet(panel, tmp_path):
    panel(full_panel())
    rep = check(tmp_path)
    assert warns(rep) == []
    assert rep.counts == {"OK": 1, "WARN": 0, "FAIL": 0, "SKIP": 0}
    assert "each of 5 week(s)" in rep.lines[0]


def test_a_first_week_written_from_a_ticker_list_is_named(panel, tmp_path):
    """2024-08-09 as it stood: every stock, no ETF, nothing in `missing`
    about them. No week comes before it, so nothing on its earlier side
    carries anything."""
    first = FRIDAYS[0]
    panel(full_panel(**{first + ".json": week(first, etfs=())}))

    rep = check(tmp_path)
    found = warns(rep)

    assert rep.counts == {"OK": 0, "WARN": 1, "FAIL": 0, "SKIP": 0}, rep.lines
    assert found[0].startswith(
        "WARN: feed: 2026-08-07.json has neither a bar nor a `missing` "
        "entry for 16 name(s): DIA, IWM, QQQ, SMH, SPY, XLB,")
    assert ("--start 2026-08-07 --end 2026-08-07 --only "
            + ",".join(sorted(ETFS)) + " --merge") in found[0]


def test_the_newest_week_is_held_to_the_etfs_too(panel, tmp_path):
    """The other end of the panel, where the next partial file would land:
    a merge run past the last week on file."""
    newest = FRIDAYS[-1]
    panel(full_panel(**{newest + ".json": week(newest, stocks=["AAPL"],
                                               etfs=["SPY"])}))
    found = warns(check(tmp_path))
    assert len(found) == 1
    assert "2026-09-04.json" in found[0] and "for 15 name(s)" in found[0]
    assert " SPY," not in found[0] and "JNJ" not in found[0]


def test_a_name_listed_in_missing_is_not_absent(panel, tmp_path):
    """Listed with a reason is the honest outcome, and all the rule asks."""
    first = FRIDAYS[0]
    panel(full_panel(**{first + ".json": week(first, etfs=(), missing=ETFS)}))
    assert warns(check(tmp_path)) == []


def test_a_name_carried_before_and_after_is_expected_between(panel, tmp_path):
    hole = FRIDAYS[2]
    panel(full_panel(**{hole + ".json": week(hole, stocks=["AAPL", "XOM"])}))
    found = warns(check(tmp_path))
    assert len(found) == 1
    assert "2026-08-21.json" in found[0]
    assert "for 1 name(s): JNJ." in found[0]


def test_a_hole_two_weeks_wide_is_still_a_hole(panel, tmp_path):
    """The week before and the week after would miss both: each hides the
    other."""
    a, b = FRIDAYS[1], FRIDAYS[2]
    panel(full_panel(**{a + ".json": week(a, stocks=["AAPL", "XOM"]),
                        b + ".json": week(b, stocks=["AAPL", "XOM"])}))
    found = warns(check(tmp_path))
    assert [line.split()[2] for line in found] == [a + ".json", b + ".json"]
    assert all("for 1 name(s): JNJ." in line for line in found)


def test_two_stale_corrections_side_by_side_are_both_found(panel, tmp_path):
    """The correction trap, in the shape this panel has it: 2026-08-21 and
    2026-08-28 are both corrected and adjacent. A name merged into both
    bases is invisible in both weeks until the corrections are rebuilt,
    and each stale week is the other's neighbour."""
    files = full_panel()
    for day in ("2026-08-21", "2026-08-28"):
        stale = week(day)
        stale["corrects"] = day + ".json"
        stale["reason"] = "a bar was dropped"
        files[day + ".corrected.json"] = stale
    for name in list(files):            # the backfill lands in every base
        if not name.endswith(".corrected.json"):
            files[name]["series"]["PLTR"] = {"close": 10.0, "volume": 5}
    weekly = panel(files)

    found = warns(check(tmp_path))
    assert [line.split()[2] for line in found] == [
        "2026-08-21.corrected.json", "2026-08-28.corrected.json"]
    for line in found:
        assert "for 1 name(s): PLTR." in line
        assert "Its base has them: the correction has gone stale" in line
        assert "backfill_weekly.py" not in line, (
            "the base holds PLTR, so a merge has nothing to add there")

    for day in ("2026-08-21", "2026-08-28"):    # rebuild_corrections.py ran
        path = weekly / (day + ".corrected.json")
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["series"]["PLTR"] = {"close": 10.0, "volume": 5}
        path.write_text(json.dumps(doc), encoding="utf-8")
    assert warns(check(tmp_path)) == []


def test_each_absent_name_is_sent_to_the_repair_that_fits_it(panel, tmp_path):
    """--merge leaves a name the week already holds alone, and exits 2 when
    that is all it was given. So the command the warning prints lists only
    what the base lacks, and the rest is the correction's to pick up. Here
    the base lacks JNJ and holds PLTR; the correction has neither."""
    files = full_panel()
    for name in files:
        files[name]["series"]["PLTR"] = {"close": 10.0, "volume": 5}
    day = "2026-08-21"
    del files[day + ".json"]["series"]["JNJ"]
    stale = week(day, stocks=["AAPL", "XOM"])
    stale["corrects"] = day + ".json"
    stale["reason"] = "a bar was dropped"
    files[day + ".corrected.json"] = stale
    panel(files)

    found = warns(check(tmp_path))
    assert len(found) == 1
    line = found[0]
    assert "2026-08-21.corrected.json" in line
    assert "for 2 name(s): JNJ, PLTR." in line
    assert "Its base has PLTR: the correction has gone stale" in line
    assert ("To add JNJ: `python scripts/backfill_weekly.py --out data "
            "--start 2026-08-21 --end 2026-08-21 --only JNJ --merge`") in line


def test_a_name_that_joins_or_leaves_the_universe_is_not_expected(
        panel, tmp_path):
    """BNY, DOC, MRSH and VMRK first appear in 2026-09-25.json, and nothing
    is wrong with 2026-09-18.json for not having them."""
    files = {}
    for i, day in enumerate(FRIDAYS):
        stocks = list(STOCKS)
        if i <= 1:
            stocks.append("LEFT")       # in the first two weeks only
        if i >= 3:
            stocks.append("JOINED")     # in the last two weeks only
        files[day + ".json"] = week(day, stocks=stocks)
    panel(files)
    assert warns(check(tmp_path)) == []


def test_at_the_two_ends_a_stock_cannot_be_told_from_a_universe_change(
        panel, tmp_path):
    """What this check does not see, pinned so that nobody takes its
    silence for more than it is. A stock missing from the first file reads
    as one that joined a week later; one dropped from the newest file reads
    as one that left."""
    first, newest = FRIDAYS[0], FRIDAYS[-1]
    panel(full_panel(**{first + ".json": week(first, stocks=["AAPL", "XOM"]),
                        newest + ".json": week(newest, stocks=["JNJ", "XOM"])}))
    assert warns(check(tmp_path)) == []


def test_it_warns_and_never_fails_the_gate(panel, tmp_path):
    """The file cannot be edited and the fix is a fetch. This script is also
    the gate of the weekly job, and a hole in an old week must not stop a
    new one from being pushed."""
    first = FRIDAYS[0]
    panel(full_panel(**{first + ".json": week(first, etfs=["SPY"])}))
    r = subprocess.run([sys.executable, str(SCRIPTS / "truth_check.py"),
                        "--repo", str(tmp_path), "--feed",
                        "--today", "2026-09-05"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    assert ("WARN: feed: 2026-08-07.json has neither a bar nor a `missing` "
            "entry for 15 name(s): DIA, IWM, QQQ, SMH, XLB,") in r.stdout
    assert "0 fail" in r.stdout
    assert "SPY bar" not in r.stdout, (
        "the witness is there, so the session check has nothing to say and "
        "this is the only one that names the file")


def test_a_file_the_feed_gate_refuses_is_left_to_it(panel, tmp_path):
    """Unreadable, or with no `series` object: check_feed reports those.
    This check says nothing about them and does not trip over them. A file
    with no `missing` key fails there too, and is read here for the bars it
    does have."""
    weekly = panel(full_panel())
    (weekly / "2026-08-14.json").write_text("{ not json", encoding="utf-8")
    (weekly / "2026-08-21.json").write_text(
        json.dumps({"as_of": "2026-08-21", "series": [], "missing": "none"}),
        encoding="utf-8")
    keyless = week("2026-08-28")
    del keyless["missing"]
    (weekly / "2026-08-28.json").write_text(json.dumps(keyless),
                                            encoding="utf-8")
    rep = check(tmp_path)
    assert warns(rep) == []
    assert "each of 3 week(s)" in rep.lines[0]


def test_a_tree_with_no_weekly_files_is_none_of_its_business(tmp_path):
    assert check(tmp_path).lines == []
    (tmp_path / "data" / "weekly").mkdir(parents=True)
    assert check(tmp_path).lines == []


# -- the committed panel -------------------------------------------------------

def committed(name):
    path = ROOT / "data" / "weekly" / name
    return json.loads(path.read_bytes().decode("ascii"))


def test_no_committed_week_lacks_a_name_it_should_hold():
    """The check, run on the real panel. It named one file until the sixteen
    were merged into it; it names none now, and a correction left stale by
    the next backfill would be the first thing to change that."""
    rep = check(ROOT)
    assert warns(rep) == []
    assert rep.counts["OK"] == 1


def test_the_first_week_has_its_sixteen_and_says_when_they_were_fetched():
    """2024-08-09.json, healed with --merge on 2026-10-06. The sixteen were
    fetched two years after the week and six weeks after the file, so each
    carries its own anchor: the same names a week later are adjusted to
    2026-08-12, before the September distributions, and a return read
    across the two files is overstated unless a reader resolves the anchor
    per ticker. Nothing else in the file moved, least of all its own stamp."""
    doc = committed("2024-08-09.json")
    labels = doc["provenance"]["series"]
    for ticker in tc.INDEX_AND_SECTOR_ETFS:
        assert ticker in doc["series"], ticker
        assert labels[ticker]["source"] == "yahoo-backfill"
        assert labels[ticker]["fetched_at"] > doc["fetched_at"]
    assert len({labels[t]["fetched_at"]
                for t in tc.INDEX_AND_SECTOR_ETFS}) == 1, "one fetch"
    assert doc["fetched_at"] == "2026-08-26T04:24:20Z"
    assert not {m["ticker"] for m in doc["missing"]} & set(
        tc.INDEX_AND_SECTOR_ETFS)

    following = committed("2024-08-16.json")
    assert not set(tc.INDEX_AND_SECTOR_ETFS) & set(
        (following.get("provenance") or {}).get("series", {})), (
        "a week later the sixteen carry the file-level anchor")
    assert following["fetched_at"] < labels["SPY"]["fetched_at"]
