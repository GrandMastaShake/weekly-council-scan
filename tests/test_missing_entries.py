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
corrections, with no date before which a file is excused. And an entry that
fails it accounts for no name: the three checks read it as no entry.

Pinned: what passes, what fails and how it is reported; what the line tells
its reader to do, in which order and in which directory; that the writers'
own output passes; that a name typed in with no reason is still a name the
week does not account for; and that the weekly job's own command line stops
on it, on a console of any encoding.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ROOT, SCRIPTS, weekly_doc

import backfill_weekly as bf  # noqa: E402  (conftest stubs the provider)
import daily_observe as do  # noqa: E402
import truth_check as tc  # noqa: E402
from scan_pipeline import snapshot  # noqa: E402

TRUTH = SCRIPTS / "truth_check.py"
WEEK = "2026-10-09"                     # a Friday
GOOD = {"ticker": "SPCX", "reason": "no bar dated %s in window" % WEEK}
ARROW = chr(0x2192)                     # a character cp1252 cannot encode


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


def warns(rep):
    return [line for line in rep.lines if line.startswith("WARN")]


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
    assert ("FAIL: feed: %s.json `missing` is %s, not a list of"
            % (WEEK, tc._clip(missing))) in got[0]
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
        assert 'entry %d is {"ticker": "N%02d"}' % (i, i) in got[0]
    assert "N%02d" % tc.MISSING_QUOTED not in got[0]
    assert "and %d more" % (10 - tc.MISSING_QUOTED) in got[0]


def test_an_entry_of_any_size_makes_a_line_of_bounded_length(panel):
    """It is quoted so it can be found, not so it can be read back."""
    blob = {"ticker": "GLD", "note": "x" * 5000}
    short = one(panel, week([{"ticker": "GLD"}]))[0]
    got = one(panel, week([blob]))
    assert len(got) == 1 and "..." in got[0]
    assert len(got[0]) <= len(short) + 80


def test_the_position_counts_from_the_top_of_the_list(panel):
    got = one(panel, week([GOOD, GOOD, GOOD, "GLD", GOOD, {"ticker": "BTC"}]))
    assert 'entry 3 is "GLD"' in got[0] and "entry 5 is" in got[0]
    assert "holds 2 entries that are not" in got[0]


def test_an_entry_is_quoted_as_the_file_holds_it(panel):
    """As JSON, in the file's key order. Python's None for a null would
    read like the text "None", which is refused for another reason."""
    got = one(panel, week([None, {"ticker": "GLD", "reason": None}]))[0]
    assert "entry 0 is null;" in got
    assert 'entry 1 is {"ticker": "GLD", "reason": null}' in got
    assert "`missing` is null, not a list of" in one(panel, week(None))[0]


def test_a_quoted_entry_is_ascii_whatever_the_file_decodes_to(panel):
    """The files are ASCII on disk, and a \\u escape in one decodes to a
    character that output which is not UTF-8 has no byte for. Quoted with
    repr(), as the first cut of this check did, it takes the whole report
    down where the output is cp1252, which is the runner's when piped."""
    entry = {"ticker": "GLD", "why": "no bar " + ARROW + " not fetched"}
    got = one(panel, week([entry]))[0]
    assert got.isascii()
    assert "no bar \\u2192 not fetched" in got


# -- what the line tells its reader ------------------------------------------

REWRITES = ("remove", "delete", "write the week", "writes it again")


def test_the_failure_says_to_look_at_main_before_the_file_is_removed(panel):
    """The same order as the names rule's line, for the same reason: the
    weekly job's check dir is a copy of the runner's panel, and a file
    there may be one main already holds. Told first to remove it, an agent
    would be on its way to rewriting a committed week. Nothing that reads
    as an instruction to rewrite comes before the sentence that sets the
    committed file aside, whatever its wording."""
    msg = one(panel, week([{"ticker": "GLD"}]))[0]
    low = msg.lower()
    stop = low.index("do not push the file")
    look = low.index("first see whether main already holds "
                     "data/weekly/%s.json" % WEEK)
    kept = low.index("a committed file is not edited")
    fresh = low.index("if main does not hold it")
    assert stop < look < kept < fresh
    for word in REWRITES:
        assert word not in low[:fresh], word
    assert "remove" in low[fresh:] and "write the week again" in low[fresh:]
    assert "do not edit the list by hand" in low
    assert "stop and tell the owner" in low
    assert "until the owner decides the repair" in low


def test_the_weekly_cure_names_the_directory_the_writer_wrote_to(panel):
    """The gate runs on a check dir. The writer wrote, and the job pushes,
    from the runner's data/weekly: removed from the check dir alone, the
    week is still on file there, and the writer refuses a week on file.
    And the state derived from the discarded week goes with it."""
    msg = one(panel, week([{"ticker": "GLD"}]))[0]
    assert "the check dir is only a copy" in msg
    assert "remove it from the runner's data/weekly" in msg
    assert msg.index("remove it from the runner's data/weekly") < msg.index(
        "snapshot.write_market_state_chain")
    assert "this copy of the panel" not in msg


def test_the_line_for_a_missing_that_is_not_a_list_carries_the_same_cure(
        panel):
    entries = one(panel, week([{"ticker": "GLD"}]))[0]
    msg = one(panel, week("none"))[0]
    cure = entries[entries.index("Do not push the file"):]
    assert msg.endswith(cure)


def test_a_reason_that_is_the_text_None_is_told_what_it_is(panel):
    """It has the right shape, so the line has to say why it is refused,
    and that writing the file again will not help by itself."""
    lost = one(panel, week([{"ticker": "VIX", "reason": "None"}]))[0]
    assert "The text None is not a name or a reason" in lost
    assert "writing the file again repeats it" in lost
    plain = one(panel, week([{"ticker": "VIX"}]))[0]
    assert "The text None" not in plain


def test_the_line_says_the_entry_counts_as_no_entry(panel):
    """What ties this line to the names rule's, when both fail."""
    msg = one(panel, week([{"ticker": "GLD"}]))[0]
    assert ("the checks that ask whether a name has a bar or an entry "
            "count it as no entry") in msg


# -- every file, weekly and daily, bases and corrections ---------------------

def daily_with(tmp_path, missing):
    doc = do.build_document(
        "2026-10-08", {"bars": {"SPY": {"close": 1.0, "volume": 1}},
                       "missing": []},
        {"rates": {}, "vol": {}, "commodities": {}, "fx": {}, "missing": []})
    doc["missing"] = missing
    d = tmp_path / "data" / "daily"
    d.mkdir(parents=True)
    (d / "2026-10-08.json").write_text(json.dumps(doc), encoding="utf-8",
                                       newline="\n")
    return fails(file_gate(tmp_path, subdir="daily"))


def test_a_daily_file_is_held_the_same_way(tmp_path):
    got = daily_with(tmp_path, [{"ticker": "DXY"}])
    assert len(got) == 1
    assert "2026-10-08.json `missing` holds 1 entry that is not" in got[0]


def test_a_daily_files_line_is_about_the_daily_file(tmp_path):
    """A Friday has a weekly and a daily file of one name, so the line says
    which it means where it sends its reader to main. And nothing in it is
    the weekly job's: no runner, no chain."""
    msg = daily_with(tmp_path, [{"ticker": "DXY"}])[0]
    low = msg.lower()
    look = low.index("first see whether main already holds "
                     "data/daily/2026-10-08.json")
    fresh = low.index("if main does not hold it")
    assert look < low.index("a committed file is not edited") < fresh
    assert "the daily job stops here and commits nothing" in low[fresh:]
    assert "a later run writes the session again" in low[fresh:]
    for word in ("data/weekly", "market_state", "remove", "delete"):
        assert word not in low, word


def test_a_correction_is_held_too_under_its_own_name(panel):
    """Readers prefer the correction, so its list is the one they see."""
    base = week([GOOD])
    fixed = week([GOOD, "AVB"])
    fixed["corrects"], fixed["reason"] = WEEK + ".json", "dropped a bar"
    got = fails(file_gate(panel({WEEK + ".json": base,
                                 WEEK + ".corrected.json": fixed}).parents[1]))
    assert len(got) == 1
    assert WEEK + ".corrected.json `missing` holds 1 entry" in got[0]


def test_a_corrections_line_does_not_send_it_to_a_writer_it_does_not_have(
        panel):
    """A correction is not the weekly job's to write again, and the entry
    for a bar it dropped is written by whoever makes the correction, so
    "do not edit the list by hand" would be false of it. Its list is its
    base's with those entries, which is what the line says."""
    base = week([GOOD])
    fixed = week([GOOD, {"ticker": "AVB"}])
    fixed["corrects"], fixed["reason"] = WEEK + ".json", "dropped a bar"
    msg = fails(file_gate(panel({WEEK + ".json": base,
                                 WEEK + ".corrected.json": fixed
                                 }).parents[1]))[0]
    low = msg.lower()
    assert low.index("do not push the file") < low.index(
        "first see whether main already holds data/weekly/%s.corrected.json"
        % WEEK) < low.index("a correction's list is its base's")
    assert "rebuild_corrections.py reads it" in msg
    assert "the base's own line says what to do" in msg
    for word in REWRITES + ("by hand", "runner's data/weekly",
                            "market_state"):
        assert word not in low, word


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
    assert len(got) == 1
    assert '"reason": "None"' in got[0] and '"ticker": "VIX"' in got[0]
    assert "The text None is not a name or a reason" in got[0]


# -- an entry that says nothing accounts for no name -------------------------

@pytest.mark.parametrize("entry", BAD_ENTRIES, ids=repr)
def test_no_entry_that_fails_accounts_for_a_name(entry):
    assert not tc._accounts(entry)
    assert tc._unaccounted({"series": {}, "missing": [entry]},
                           ["GLD", "None", ""]) == {"GLD", "None", ""}


def test_an_entry_with_a_ticker_and_a_reason_accounts_for_its_name():
    assert tc._accounts(GOOD)
    assert tc._unaccounted({"series": {}, "missing": [GOOD]},
                           ["SPCX", "GLD"]) == {"GLD"}


def test_a_name_listed_with_no_reason_is_still_a_name_the_week_lacks(panel):
    """GLD has no bar and an entry that gives no reason. The entry fails.
    The names rule fails too, and has to: its line is the one that says why
    a week comes out without a name (a scan_pipeline/ behind the repo's)
    and what to do. When it took the ticker as a name accounted for, the
    report for this week was the entry's FAIL beside "has a bar or a
    `missing` entry for each of the 336 names", and the entry's own cure
    ran the same writer again."""
    names = [n for n in tc.EQUITY_UNIVERSE if n != "GLD"]
    repo = panel({WEEK + ".json": week([{"ticker": "GLD"}], names=names)
                  }).parents[1]
    rep = file_gate(repo)
    tc.check_feed_names(repo, rep)
    got = fails(rep)
    assert len(got) == 2, got
    assert "`missing` holds 1 entry that is not" in got[0]
    assert ("%s.json has no bar and no `missing` entry for ['GLD']" % WEEK
            ) in got[1]
    assert "Sync it" in got[1]
    assert not [line for line in rep.lines
                if "has a bar or a `missing` entry for each" in line]


def test_the_same_name_with_a_reason_is_accounted_for(panel):
    names = [n for n in tc.EQUITY_UNIVERSE if n != "GLD"]
    entry = {"ticker": "GLD", "reason": "no bar dated %s in window" % WEEK}
    repo = panel({WEEK + ".json": week([entry], names=names)}).parents[1]
    rep = file_gate(repo)
    tc.check_feed_names(repo, rep)
    assert fails(rep) == []
    assert [line for line in rep.lines
            if "has a bar or a `missing` entry for each" in line]


@pytest.mark.parametrize("entry, absent", [
    ({"ticker": "AAPL"}, True),
    ({"ticker": "AAPL", "reason": "None"}, True),
    ({"ticker": "AAPL", "reason": "no bar dated 2026-10-02"}, False),
])
def test_the_panel_check_reads_an_entry_with_no_reason_as_no_entry(
        panel, entry, absent):
    """AAPL has a bar the week before and the week after. Its --merge
    command is in the warning, and a merge that finds the bar puts it in
    the entry's place: the one repair there is for such an entry once the
    week is committed."""
    etfs = list(tc.INDEX_AND_SECTOR_ETFS)
    files = {day + ".json": weekly_doc(day, etfs + ["AAPL"])
             for day in ("2026-09-25", "2026-10-09")}
    files["2026-10-02.json"] = week([entry], as_of="2026-10-02", names=etfs)
    rep = tc.Report()
    tc.check_silent_absence(panel(files).parents[1], rep)
    got = [line for line in warns(rep) if "2026-10-02.json" in line]
    assert bool(got) is absent, rep.render()
    if absent:
        assert "for 1 name(s): AAPL" in got[0]
        assert "--only AAPL --merge" in got[0]


@pytest.mark.parametrize("entry, listed", [
    ({"ticker": "SPY"}, False),
    ({"ticker": "SPY", "reason": "no bar dated 2024-08-09"}, True),
])
def test_the_witness_warning_reads_it_the_same_way(panel, entry, listed):
    """A week from before the witness rule with no SPY bar is warned about,
    and the warning says whether SPY is at least listed. Listed with no
    reason, it is not."""
    doc = week([entry], as_of="2024-08-09", names=("AAPL", "XLK"))
    rep = file_gate(panel({"2024-08-09.json": doc}).parents[1])
    got = [line for line in warns(rep) if "no SPY bar" in line]
    assert len(got) == 1
    assert ("does not list it in 'missing'" in got[0]) is not listed


# -- what clears one, once the week is committed -----------------------------

def typed_in(tmp_path):
    """A week on file with GLD typed into `missing` and nothing beside it."""
    d = tmp_path / "data" / "weekly"
    d.mkdir(parents=True)
    p = d / (WEEK + ".json")
    p.write_text(json.dumps(week([GOOD, {"ticker": "GLD"}]), indent=2) + "\n",
                 encoding="utf-8", newline="\n")
    assert len(fails(file_gate(tmp_path))) == 1
    return p, dt.date.fromisoformat(WEEK)


def test_a_merge_that_finds_the_bar_puts_it_in_the_entrys_place(tmp_path):
    """The one repair inside the contract. The base is never edited, but a
    --merge backfill adds, and what it adds is no longer missing. The panel
    check prints its command."""
    p, friday = typed_in(tmp_path)
    rec = bf.merge_into_existing(friday, ["GLD"],
                                 {"GLD": ([friday], [50.0], [1000])}, str(p))
    assert rec["added"] == ["GLD"]
    after = json.loads(p.read_text(encoding="utf-8"))
    assert after["missing"] == [GOOD] and "GLD" in after["series"]
    assert fails(file_gate(tmp_path)) == []


def test_a_merge_that_finds_no_bar_leaves_the_entry_as_it_is(tmp_path):
    """And that is all there is. The name is in the list, so the merge
    gives it no reason and does not write the file. From there the repair
    is the owner's to decide, which is what the line says."""
    p, friday = typed_in(tmp_path)
    before = p.read_bytes()
    rec = bf.merge_into_existing(friday, ["GLD"], {}, str(p))
    assert rec["changed"] is False and p.read_bytes() == before
    assert len(fails(file_gate(tmp_path))) == 1


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


def job_line(root, console=None):
    """The weekly job's gate line, the day after the week in the dir, with
    site-packages kept out. `console` is the encoding of the terminal it
    prints to."""
    newest = sorted(p.stem for p in (root / "data" / "weekly").glob("*.json"))
    today = dt.date.fromisoformat(newest[-1]) + dt.timedelta(days=1)
    env = dict(os.environ)
    if console:
        env["PYTHONIOENCODING"] = console
    return subprocess.run(
        [sys.executable, "-S", str(root / "scripts" / "truth_check.py"),
         "--repo", str(root), "--feed", "--derive", "--today",
         today.isoformat()], capture_output=True, text=True, env=env)


def test_the_weekly_jobs_line_stops_on_a_name_typed_into_missing(tmp_path):
    """The cheapest way past the names rule, which told its reader not to
    and could not stop it: a week with no GLD bar, and an entry that says
    only "GLD". This run used to exit 0. It fails twice now, and the second
    line is the names rule's, unmoved by the entry."""
    names = [n for n in tc.EQUITY_UNIVERSE if n != "GLD"]
    r = job_line(check_dir(tmp_path, week([{"ticker": "GLD"}], names=names)))
    assert r.returncode == 1, r.stdout + r.stderr
    entry = r.stdout.index("FAIL: feed: %s.json `missing` holds 1 entry "
                           "that is not" % WEEK)
    name = r.stdout.index("FAIL: feed: %s.json has no bar and no `missing` "
                          "entry for ['GLD']" % WEEK)
    assert entry < name
    assert "2 fail" in r.stdout
    assert "has a bar or a `missing` entry for each" not in r.stdout


def test_the_same_week_with_the_writers_own_entry_passes(tmp_path):
    names = [n for n in tc.EQUITY_UNIVERSE if n != "GLD"]
    entry = {"ticker": "GLD", "reason": "no bar dated %s in window" % WEEK}
    r = job_line(check_dir(tmp_path, week([entry], names=names)))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 fail" in r.stdout


@pytest.mark.parametrize("missing", [5, True, "none", {"ticker": "SPY"},
                                     None, ["SPY"], [{"ticker": ["SPY"]}]],
                         ids=repr)
def test_no_shape_of_missing_ends_the_gate_in_a_traceback(tmp_path, missing):
    """A gate that dies prints no FAIL. In a week from before the witness
    rule with no SPY bar, the check that asks whether SPY is at least
    listed walked `missing` whatever it was: a number or `true` there
    ended the run in a TypeError, and a string, an object or null was
    walked, or skipped, in silence."""
    doc = week(missing, as_of="2024-08-09", names=("AAPL", "XLK"))
    r = job_line(check_dir(tmp_path, doc))
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode == 1 and "SUMMARY:" in r.stdout
    assert "FAIL: feed: 2024-08-09.json `missing` " in r.stdout


def test_a_console_that_is_not_utf8_still_gets_the_report(tmp_path):
    """Other lines quote what a file holds with repr(), which keeps a
    character the output may have no byte for. Piped on Windows it is
    cp1252, which is the runner, and the whole report went with a
    UnicodeEncodeError: the lines are printed in one write. Nothing
    committed holds such a character, so it has not happened. The
    character is escaped now."""
    doc = week([{"ticker": "GLD", "why": "no bar " + ARROW + " not fetched"}])
    doc["session_note"] = "Friday holiday " + ARROW + " bars from 2026-10-08"
    r = job_line(check_dir(tmp_path, doc), console="cp1252")
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode == 1 and "SUMMARY:" in r.stdout
    assert "FAIL: feed: %s.json `missing` holds 1 entry" % WEEK in r.stdout
    assert "no bar \\u2192 not fetched" in r.stdout
    assert "session_note 'Friday holiday \\u2192 bars from" in r.stdout


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
        tc._feed_missing_check(f.name, doc, subdir, rep)
        assert rep.lines == [], rep.render()
        assert all(tc._accounts(m) for m in doc["missing"])
        entries += len(doc["missing"])
    assert entries > 0, "nothing was looked at"
