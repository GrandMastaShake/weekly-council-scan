"""What a file's `missing` list holds.

DATA_FEED.md sec.1: "A ticker that could not be fetched is listed with a
reason." The gate required the key and never looked inside it. `missing`
could be a string, an entry could be a bare name or an object with no
reason in it, and every check passed. Three checks then took such an entry
at its word: a ticker in the list is a name accounted for (check_feed_names,
check_silent_absence, --config), so `{"ticker": "GLD"}` typed into a week
that had no GLD bar made "has no bar and no `missing` entry" go away and
recorded nothing.

The entry is read downstream as well. sector-regime-heatmap prints the
reason on its daily tape. rebuild_corrections.py and backfill_weekly.py
--merge take each entry for an object and end in a traceback on one that is
not. And a `missing` that is a number ended --feed itself in one.

Every entry committed on 2026-10-06 is an object with a ticker and a reason,
both strings with something in them, and no writer here produces anything
else. So the rule is a FAIL, for every weekly and daily file, bases and
corrections, with no date before which a file is excused.

Pinned: what passes, what fails and how it is reported; that the writers'
own output passes; that one bad entry is one line across the gate's checks;
and that the weekly job's own command line stops on a typed-in entry
instead of passing it.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ROOT, SCRIPTS, weekly_doc

import daily_observe as do  # noqa: E402
import truth_check as tc  # noqa: E402
from scan_pipeline import snapshot  # noqa: E402

TRUTH = SCRIPTS / "truth_check.py"
WEEK = "2026-10-09"                     # a Friday
GOOD = {"ticker": "SPCX", "reason": "no bar dated %s in window" % WEEK}


def week(missing, as_of=WEEK, names=("SPY", "AAPL")):
    doc = weekly_doc(as_of, list(names))
    doc["missing"] = missing
    return doc


def file_gate(repo, subdir="weekly"):
    rep = tc.Report()
    tc.check_feed(Path(repo), rep, subdir=subdir,
                  require_friday=(subdir == "weekly"), label=subdir)
    return rep


def fails(rep):
    return [line for line in rep.lines if line.startswith("FAIL")]


def one(panel, doc):
    """The file gate's failures for a panel holding just this week."""
    return fails(file_gate(panel({doc["as_of"] + ".json": doc}).parents[1]))


# -- what passes -------------------------------------------------------------

def test_a_list_of_ticker_and_reason_passes(panel):
    """Names, instruments, and the wildcard the daily bootstrap writes for
    "no special instrument was asked for"."""
    doc = week([GOOD,
                {"ticker": "WTI", "reason": "CLX26.NYM: the bar is a quote "
                                            "until the settlement is loaded"},
                {"ticker": "*", "reason": "bootstrap backfill: special "
                                          "instruments not fetched"}])
    assert one(panel, doc) == []


def test_an_empty_list_passes(panel):
    assert one(panel, week([])) == []


def test_more_keys_than_the_two_are_not_this_rules_business(panel):
    doc = week([dict(GOOD, since="2026-06-12")])
    assert one(panel, doc) == []


# -- `missing` itself --------------------------------------------------------

@pytest.mark.parametrize("missing", [
    dict(GOOD),             # one entry, not in a list
    "none", "", 5, 0, None, True,
])
def test_a_missing_that_is_not_a_list_fails(panel, missing):
    got = one(panel, week(missing))
    assert len(got) == 1, got
    assert "FAIL: feed: %s.json `missing` is " % WEEK in got[0]
    assert "not a list of" in got[0]
    assert "commits an empty list" in got[0]


# -- an entry ----------------------------------------------------------------

BAD_ENTRIES = [
    "GLD",                                          # a bare name
    7, None, ["GLD", "no bar"],
    {},
    {"reason": "no bar for the week"},              # names nothing
    {"ticker": "GLD"},                              # gives no reason
    {"ticker": "GLD", "reason": None},
    {"ticker": "GLD", "reason": ""},
    {"ticker": "GLD", "reason": "   "},
    {"ticker": "GLD", "reason": 0},
    {"ticker": "GLD", "reason": {"why": "no bar"}},
    {"ticker": None, "reason": "no bar"},
    {"ticker": "", "reason": "no bar"},
    {"ticker": 5, "reason": "no bar"},
    {"ticker": ["GLD"], "reason": "no bar"},        # unhashable where a name goes
    {"ticker": "GLD", "reason": "None"},            # str(None), see below
    {"ticker": "None", "reason": "no bar"},
]


@pytest.mark.parametrize("entry", BAD_ENTRIES, ids=repr)
def test_an_entry_that_names_nothing_or_gives_no_reason_fails(panel, entry):
    got = one(panel, week([GOOD, entry]))
    assert len(got) == 1, got
    assert ("FAIL: feed: %s.json `missing` holds 1 entry that is not "
            '{"ticker": <name>, "reason": <why>}' % WEEK) in got[0]
    assert "entry 1 is " + tc._clip(entry) in got[0]
    assert "entry 0" not in got[0], "the well-formed entry is not accused"


def test_one_line_for_a_file_however_many_entries_are_wrong(panel):
    """A writer that lost the reason would lose it for every name. Three
    are quoted and the rest counted."""
    bad = [{"ticker": "N%02d" % i} for i in range(10)]
    got = one(panel, week(bad))
    assert len(got) == 1
    assert "`missing` holds 10 entries that are not" in got[0]
    for i in range(tc.MISSING_QUOTED):
        assert "entry %d is {'ticker': 'N%02d'}" % (i, i) in got[0]
    assert "N%02d" % tc.MISSING_QUOTED not in got[0]
    assert "and %d more" % (10 - tc.MISSING_QUOTED) in got[0]


def test_an_entry_of_any_size_makes_a_line_of_bounded_length(panel):
    """It is quoted so it can be found, not so it can be read back."""
    blob = {"ticker": "GLD", "note": "x" * 5000}
    got = one(panel, week([blob]))
    assert len(got) == 1 and len(got[0]) < 1500
    assert "..." in got[0]


def test_the_position_counts_from_the_top_of_the_list(panel):
    got = one(panel, week([GOOD, GOOD, GOOD, "GLD", GOOD, {"ticker": "BTC"}]))
    assert "entry 3 is 'GLD'" in got[0] and "entry 5 is" in got[0]
    assert "holds 2 entries that are not" in got[0]


# -- what the line tells its reader ------------------------------------------

def test_the_failure_says_to_look_at_main_before_the_file_is_removed(panel):
    """The same order as the names rule's line, for the same reason: the
    weekly job's check dir is the runner's copy of the panel, and a file
    there may be one main already holds. Told first to remove it, an agent
    would be on its way to rewriting a committed week."""
    msg = one(panel, week([{"ticker": "GLD"}]))[0]
    stop = msg.index("Do not push the file")
    look = msg.index("First see whether main already holds %s.json" % WEEK)
    kept = msg.index("it is committed and is not edited")
    remove = msg.index("remove the file from this copy of the panel")
    assert stop < look < kept < remove
    assert "do not repair it by hand" in msg
    assert "the owner's to decide" in msg


def test_the_line_for_a_missing_that_is_not_a_list_carries_the_same_cure(
        panel):
    msg = one(panel, week("none"))[0]
    assert msg.index("First see whether main already holds") < msg.index(
        "remove the file from this copy of the panel")


# -- every file, weekly and daily, bases and corrections ---------------------

def test_a_daily_file_is_held_the_same_way(tmp_path):
    doc = do.build_document(
        "2026-10-08", {"bars": {"SPY": {"close": 1.0, "volume": 1}},
                       "missing": []},
        {"rates": {}, "vol": {}, "commodities": {}, "fx": {}, "missing": []})
    doc["missing"] = [{"ticker": "DXY"}]
    d = tmp_path / "data" / "daily"
    d.mkdir(parents=True)
    (d / "2026-10-08.json").write_text(json.dumps(doc), encoding="utf-8",
                                       newline="\n")
    got = fails(file_gate(tmp_path, subdir="daily"))
    assert len(got) == 1
    assert "2026-10-08.json `missing` holds 1 entry that is not" in got[0]


def test_a_correction_is_held_too_under_its_own_name(panel):
    """Readers prefer the correction, so its list is the one they see."""
    base = week([GOOD])
    fixed = week([GOOD, "AVB"])
    fixed["corrects"], fixed["reason"] = WEEK + ".json", "dropped a bar"
    got = fails(file_gate(panel({WEEK + ".json": base,
                                 WEEK + ".corrected.json": fixed}).parents[1]))
    assert len(got) == 1
    assert WEEK + ".corrected.json `missing` holds 1 entry" in got[0]


def test_no_file_is_excused_by_its_date(panel):
    """The witness rule and the settlement rule each date from a day, for
    files that could not be edited. This has no such files: every entry
    already committed is well-formed."""
    old = week([{"ticker": "SPCX"}], as_of="2024-08-16")
    assert len(one(panel, old)) == 1


def test_a_file_with_no_missing_key_gets_the_line_it_always_got(panel):
    """One defect, one line: check_feed reports the absent key, and this
    adds nothing to it."""
    doc = week([])
    del doc["missing"]
    got = one(panel, doc)
    assert len(got) == 1 and "lacks required key 'missing'" in got[0]


# -- the writers' own output -------------------------------------------------

def test_what_the_weekly_writer_writes_passes(tmp_path):
    """Names it could not fetch and instruments that failed, deduped and
    sorted, exactly as write_weekly commits them."""
    path = snapshot.write_weekly(
        WEEK,
        {"bars": {"SPY": {"close": 668.0, "volume": 1}},
         "missing": [{"ticker": "SPCX", "reason": "no bar dated " + WEEK}]},
        {"rates": {}, "vol": {}, "commodities": {}, "fx": {},
         "missing": [{"ticker": "VIX", "reason": "no data returned"}]},
        out_dir=str(tmp_path / "data"))
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    assert [m["ticker"] for m in doc["missing"]] == ["SPCX", "VIX"]
    assert not [line for line in fails(file_gate(tmp_path))
                if "`missing`" in line]


def test_what_the_daily_writer_writes_passes(tmp_path):
    doc = do.build_document(
        "2026-10-08",
        {"bars": {"SPY": {"close": 1.0, "volume": 1}},
         "missing": [{"ticker": "EA", "reason": "no bar dated 2026-10-08"}]},
        None)                           # no special instruments asked for
    assert {"ticker": "*", "reason": "special instruments not requested "
                                     "(--no-special)"} in doc["missing"]
    do.write_document(doc, str(tmp_path / "data"))
    assert fails(file_gate(tmp_path, subdir="daily")) == []


@pytest.mark.parametrize("build", ["weekly", "daily"])
def test_a_reason_lost_on_the_way_to_a_writer_is_committed_as_None_and_fails(
        tmp_path, build):
    """Why the text "None" is no reason. Both writers pass the fields
    through str(), so an entry that reaches them without one is written as
    {"ticker": "VIX", "reason": "None"}: the right shape, and nothing in
    it. If a writer is ever changed to refuse such an entry instead, this
    fails, and the special case in _says_something can go with it."""
    lost = [{"ticker": "VIX"}]
    bars = {"bars": {"SPY": {"close": 1.0, "volume": 1}}, "missing": []}
    special = {"rates": {}, "vol": {}, "commodities": {}, "fx": {},
               "missing": lost}
    if build == "weekly":
        path = snapshot.write_weekly(WEEK, bars, special,
                                     out_dir=str(tmp_path / "data"))
        doc, subdir = json.loads(Path(path).read_text(encoding="utf-8")), \
            "weekly"
    else:
        doc, subdir = do.build_document("2026-10-08", bars, special), "daily"
        do.write_document(doc, str(tmp_path / "data"))
    assert doc["missing"] == [{"ticker": "VIX", "reason": "None"}]
    got = [line for line in fails(file_gate(tmp_path, subdir=subdir))
           if "`missing`" in line]
    assert len(got) == 1 and "'reason': 'None'" in got[0]


# -- one defect, one line ----------------------------------------------------

def test_a_name_listed_with_no_reason_is_one_finding_across_the_gate(panel):
    """GLD has no bar and an entry that gives no reason. The entry fails,
    here. The names rule still takes the ticker as a name accounted for and
    does not report GLD a second time, with a cure (sync, remove, write
    again) that is not the cure for a typed-in entry."""
    names = [n for n in tc.EQUITY_UNIVERSE if n != "GLD"]
    doc = week([{"ticker": "GLD"}], names=names)
    repo = panel({WEEK + ".json": doc}).parents[1]
    rep = file_gate(repo)
    tc.check_feed_names(repo, rep)
    tc.check_silent_absence(repo, rep)
    got = fails(rep)
    assert len(got) == 1, got
    assert "`missing` holds 1 entry that is not" in got[0]


# -- the command line --------------------------------------------------------

def check_dir(tmp_path, doc):
    """What the weekly job's step 6 assembles: its data, macro/facts.json
    and this script, and nothing beside the script to import."""
    root = tmp_path / "checkdir"
    (root / "data" / "weekly").mkdir(parents=True)
    (root / "macro").mkdir()
    (root / "scripts").mkdir()
    (root / "data" / "weekly" / (doc["as_of"] + ".json")).write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    (root / "macro" / "facts.json").write_text("{}\n", encoding="utf-8",
                                               newline="\n")
    shutil.copy(TRUTH, root / "scripts" / "truth_check.py")
    return root


def job_line(root):
    """The weekly job's gate line, the day after the week in the dir, with
    site-packages kept out."""
    newest = sorted(p.stem for p in (root / "data" / "weekly").glob("*.json"))
    today = dt.date.fromisoformat(newest[-1]) + dt.timedelta(days=1)
    return subprocess.run(
        [sys.executable, "-S", str(root / "scripts" / "truth_check.py"),
         "--repo", str(root), "--feed", "--derive", "--today",
         today.isoformat()], capture_output=True, text=True)


def test_the_weekly_jobs_line_stops_on_a_name_typed_into_missing(tmp_path):
    """The cheapest way past the names rule, which told its reader not to
    and could not stop it: a week with no GLD bar, and an entry that says
    only "GLD". This run used to exit 0."""
    names = [n for n in tc.EQUITY_UNIVERSE if n != "GLD"]
    r = job_line(check_dir(tmp_path, week([{"ticker": "GLD"}], names=names)))
    assert r.returncode == 1, r.stdout + r.stderr
    assert ("FAIL: feed: %s.json `missing` holds 1 entry that is not"
            % WEEK) in r.stdout
    assert "1 fail" in r.stdout


def test_the_same_week_with_the_writers_own_entry_passes(tmp_path):
    names = [n for n in tc.EQUITY_UNIVERSE if n != "GLD"]
    entry = {"ticker": "GLD", "reason": "no bar dated %s in window" % WEEK}
    r = job_line(check_dir(tmp_path, week([entry], names=names)))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 fail" in r.stdout


@pytest.mark.parametrize("missing", [5, "none", {"ticker": "SPY"}, None,
                                     ["SPY"], [{"ticker": ["SPY"]}]],
                         ids=repr)
def test_no_shape_of_missing_ends_the_gate_in_a_traceback(tmp_path, missing):
    """A gate that dies prints no FAIL. A week from before the witness rule
    with no SPY bar is the one that used to: the check that asks whether
    SPY is at least listed walked a `missing` that was not a list."""
    doc = week(missing, as_of="2024-08-09", names=("AAPL", "XLK"))
    r = job_line(check_dir(tmp_path, doc))
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode == 1 and "SUMMARY:" in r.stdout
    assert "FAIL: feed: 2024-08-09.json `missing` " in r.stdout


# -- the real panel ----------------------------------------------------------

@pytest.mark.parametrize("subdir", ["weekly", "daily"])
def test_every_committed_entry_is_a_ticker_and_a_reason(subdir):
    """The ground for making this a FAIL with no file excused. Each of
    these files went through --feed before it was committed, the runner's
    and the workflows' alike, so this fails on nothing a gate has not
    already refused."""
    files = sorted((ROOT / "data" / subdir).glob("*.json"))
    assert files
    entries = 0
    for f in files:
        doc = json.loads(f.read_text(encoding="utf-8"))
        rep = tc.Report()
        tc._feed_missing_check(f.name, doc, rep)
        assert rep.lines == [], rep.render()
        entries += len(doc["missing"])
    assert entries > 0, "nothing was looked at"
