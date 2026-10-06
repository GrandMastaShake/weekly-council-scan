"""The names a weekly file accounts for, held where the constants cannot be
asked.

`truth_check --config` fails when the newest weekly file has neither a bar
nor a `missing` entry for a name the writer fetches. It runs in CI and in
the daily job. It does not run where the week is written. The Saturday job
gates with `--feed --derive` from a check dir that holds a copy of the
runner's data, macro/facts.json and truth_check.py fetched fresh. There is
no scan_pipeline/ in it, so --config cannot import its constants there, and
the constants within reach are the runner's: the copy in doubt.

Nothing in that line knew which names a week should hold. The two builds
without BTC and GLD passed it and were pushed, and so would any week from a
runner whose only fault is its list of names. On main such a week fails
`--feed --config` and the real-panel tests, which is CI red and, through
daily-observe.yml, no daily session committed until the week is repaired.

So the gate carries the list itself (tc.EQUITY_UNIVERSE), and --feed holds
the newest week to it. But the job's check dir is the RUNNER's copy of the
data, synced by hand, and a name merged into a week on main does not reach
it. A short newest file there is either a week the stale writer has just
written, which must not be pushed, or the runner's copy of a week main
already holds whole, which must not be rewritten. The gate cannot see main.

The first draft of this failed every short newest file, with a line that
said to remove the file and write the week again. On the runner that day it
would have sent the job to rewrite 2026-10-02.json, a committed week, and
its prompt would have pushed the rewrite over main's. The second draft drew
the line at "the day the last name joined" and asked whoever next added a
name to move it, which would have turned the failure for every older name
into a warning. What is here: a fixed day, the one the rule began, read off
the file's own fetched_at; a line that tells the reader to look at main
before anything else; and no cause claimed that the gate cannot know.

Pinned: the list is the writer's; the rule fails, warns and stays quiet
where it should; the order of the sentences in its lines; and the job's own
command line, with one script and the standard library.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

from conftest import ROOT, SCRIPTS, weekly_doc

import truth_check as tc  # noqa: E402
from scan_pipeline import snapshot  # noqa: E402

TRUTH = SCRIPTS / "truth_check.py"
NAMES = list(tc.EQUITY_UNIVERSE)
SINCE = dt.date.fromisoformat(tc.NAMES_RULE_SINCE)


def friday_on_or_before(day):
    return day - dt.timedelta(days=(day.weekday() - 4) % 7)


# Every date below hangs off the rule's own day, so none of them has to be
# kept in step with it by hand. As the constant stands: a week written on
# 2026-10-10 for Friday the 9th, and the runner's copy of Friday the 2nd,
# fetched on the 3rd.
FRESH = (friday_on_or_before(SINCE + dt.timedelta(days=6))).isoformat()
COPY_DAY = friday_on_or_before(SINCE - dt.timedelta(days=2))
COPY = COPY_DAY.isoformat()
COPY_FETCHED = (COPY_DAY + dt.timedelta(days=1)).isoformat() + "T13:07:47Z"
DAY_BEFORE = (SINCE - dt.timedelta(days=1)).isoformat()


def literal(names) -> str:
    """The list as scripts/truth_check.py writes it."""
    body = textwrap.fill(", ".join('"%s"' % n for n in names) + ",",
                         width=79, initial_indent="    ",
                         subsequent_indent="    ", break_long_words=False,
                         break_on_hyphens=False)
    return "EQUITY_UNIVERSE = (\n" + body + "\n)"


def week(as_of, names=None, missing=(), fetched_at=None):
    """A weekly file with a bar for each of `names` (the whole list unless
    given) and a reason for each of `missing`. Fetched at 13:20 UTC the day
    after `as_of` unless told otherwise."""
    doc = weekly_doc(as_of, NAMES if names is None else names,
                     fetched_at=fetched_at)
    doc["missing"] = [{"ticker": t, "reason": "no bar dated %s" % as_of}
                      for t in missing]
    return doc


def without(*gone):
    return [n for n in NAMES if n not in gone]


def stale_copy():
    """The runner's own copy of the newest week on 2026-10-06: fetched
    before this check existed, and holding neither BTC nor GLD."""
    return week(COPY, without("BTC", "GLD"), fetched_at=COPY_FETCHED)


def names_gate(repo):
    rep = tc.Report()
    tc.check_feed_names(Path(repo), rep)
    return rep


def lines(rep, level):
    return [line for line in rep.lines if line.startswith(level)]


def one(panel, doc):
    """The report for a panel holding just this week."""
    return names_gate(panel({doc["as_of"] + ".json": doc}).parents[1])


def test_the_rules_day_does_not_move():
    """Every other date here is derived from it, so this is the one test
    that holds it to the day it was chosen for. Earlier, and the runner's
    copies of committed weeks fail again: the newest was fetched on
    2026-10-03, and a failure there sends the job to rewrite a committed
    week, which is what the first draft did. Later, and a short week
    written in between only warns. It is the day the rule began; a name
    that joins the feed afterwards does not change it."""
    assert tc.NAMES_RULE_SINCE == "2026-10-06"


def test_the_dates_these_tests_use_are_what_they_say():
    """Guards the arithmetic above, whatever the rule's day is."""
    assert dt.date.fromisoformat(FRESH).weekday() == 4
    assert COPY_DAY.weekday() == 4
    assert week(FRESH)["fetched_at"][:10] >= tc.NAMES_RULE_SINCE
    assert COPY_FETCHED[:10] < tc.NAMES_RULE_SINCE
    assert SINCE <= dt.date.today(), (
        "a day still to come would turn every failure into a warning")


# -- the list ----------------------------------------------------------------

def test_the_gates_list_is_the_writers():
    """The one thing that keeps a copy honest. When the feed changes, this
    fails and says what to put in scripts/truth_check.py."""
    want = tuple(snapshot.equity_universe())
    assert tc.EQUITY_UNIVERSE == want, (
        "EQUITY_UNIVERSE in scripts/truth_check.py is not "
        "snapshot.equity_universe(). The weekly job's gate holds its week "
        "to that list and nothing else. Replace it with the lines below "
        "(`python tests/test_feed_names.py` prints them without this "
        "gutter):\n\n" + literal(want) + "\n")
    assert len(set(want)) == len(want)


def test_the_script_writes_the_list_the_way_this_prints_it():
    """So the replacement can be pasted, and a paste that changes nothing
    leaves no diff."""
    assert literal(tc.EQUITY_UNIVERSE) in TRUTH.read_text(encoding="utf-8")


def test_the_list_is_the_feed_and_the_sixteen_etfs():
    """Stated without the writer in between: every feed name, BTC and GLD
    among them, and the index and sector ETFs no ticker list carries."""
    from scan_pipeline.config import tickers as t
    held = set(tc.EQUITY_UNIVERSE)
    assert set(t.PRICE_FEED_UNIVERSE) <= held
    assert {"BTC", "GLD", "SPY", "XLK"} <= held
    assert len(held - set(t.PRICE_FEED_UNIVERSE)) == 16


# -- a week written since the rule began -------------------------------------

def test_a_week_with_a_bar_for_every_name_passes(panel):
    rep = one(panel, week(FRESH))
    assert lines(rep, "FAIL") == [] and lines(rep, "WARN") == []
    assert lines(rep, "OK") == [
        "OK: feed: %s.json has a bar or a `missing` entry for each of the "
        "%d names the weekly writer fetches" % (FRESH, len(NAMES))]


def test_a_week_written_without_a_name_fails(panel):
    """BTC and GLD as the runner's writer leaves them out: in neither
    `series` nor `missing`, in a file fetched since the rule began."""
    doc = week(FRESH, without("BTC", "GLD"))
    got = lines(one(panel, doc), "FAIL")
    assert len(got) == 1
    assert ("FAIL: feed: %s.json has no bar and no `missing` entry for "
            "['BTC', 'GLD']" % FRESH) in got[0]
    assert "It was fetched %s." % doc["fetched_at"] in got[0]


def test_no_ok_and_no_warning_beside_the_failure(panel):
    rep = one(panel, week(FRESH, without("GLD")))
    assert lines(rep, "OK") == [], "an OK next to a FAIL reads as a pass"
    assert lines(rep, "WARN") == []


def test_the_failure_says_to_look_at_main_before_anything_is_removed(panel):
    """The line is the only instruction the job's agent gets, and it is
    read in order. Told first to remove the file and write the week again,
    an agent holding the runner's copy of a committed week would rewrite
    that week and push it over main's."""
    msg = lines(one(panel, week(FRESH, without("GLD"))), "FAIL")[0]
    stop = msg.index("Do not push this file")
    look = msg.index("First see whether main already holds %s.json" % FRESH)
    committed = msg.index("it is a committed week and is never written again")
    remove = msg.index("remove the file from the runner's data/weekly")
    assert stop < look < committed < remove


def test_the_failure_does_not_say_which_of_the_two_it_is_looking_at(panel):
    """It cannot know. The stale writer is named only on the branch where
    main does not hold the week, which is the only place it is true."""
    msg = lines(one(panel, week(FRESH, without("GLD"))), "FAIL")[0]
    absent_on_main = msg.index("If main does not hold it")
    assert msg.index("was not asking for them") > absent_on_main
    assert msg.index("a scan_pipeline/ behind the repo's") > absent_on_main
    held = msg[msg.index("If it does, it is a committed week"):absent_on_main]
    assert "the runner's is behind and main's replaces it" in held
    assert "where main's lacks them too" in held


def test_the_failure_rules_out_the_cheap_ways_past_it(panel):
    """Pushing it anyway, and a `missing` entry typed in to make the line
    go away: the gate cannot tell that entry from the writer's own."""
    msg = lines(one(panel, week(FRESH, without("GLD"))), "FAIL")[0]
    assert "Do not push this file" in msg
    assert "do not add the names to `missing` by hand" in msg
    assert "the writer's record that it asked" in msg


def test_the_failure_carries_the_whole_cure(panel):
    """Which copy is behind, how the week is written again, and that the
    state is re-derived through the chain: the discarded week has already
    overwritten the runner's market_state.json, and a deriver handed that
    as last week's takes corr_prev from the wrong week."""
    msg = lines(one(panel, week(FRESH, without("GLD"))), "FAIL")[0]
    assert "config/tickers.py" in msg and "snapshot.py" in msg
    assert "Sync it, remove the file" in msg
    assert "write the week again with the job's own calls" in msg
    assert "snapshot.write_market_state_chain" in msg
    assert "--only <names> --merge" in msg


def test_a_reason_is_as_good_as_a_bar(panel):
    """SPCX before it listed is the standing case: no bar, and a `missing`
    entry that says so."""
    rep = one(panel, week(FRESH, without("SPCX", "GLD"),
                          missing=("SPCX", "GLD")))
    assert lines(rep, "FAIL") == []
    assert len(lines(rep, "OK")) == 1


def test_names_the_list_does_not_hold_are_not_its_business(panel):
    """A week may hold more: a name since dropped from the feed. Only
    absence is judged."""
    assert lines(one(panel, week(FRESH, NAMES + ["EA", "HES"])), "FAIL") == []


def test_the_newest_week_and_no_other(panel):
    """An older week without a name is a name that joined later, and those
    weeks are not edited."""
    repo = panel({COPY + ".json": week(COPY, without("AAPL")),
                  FRESH + ".json": week(FRESH)}).parents[1]
    rep = names_gate(repo)
    assert lines(rep, "FAIL") == [] and lines(rep, "WARN") == []


def test_the_newest_week_is_the_one_that_fails(panel):
    repo = panel({COPY + ".json": week(COPY),
                  FRESH + ".json": week(FRESH, without("AAPL"))}).parents[1]
    got = lines(names_gate(repo), "FAIL")
    assert len(got) == 1 and (FRESH + ".json has no bar") in got[0]
    assert "['AAPL']" in got[0]


def test_a_file_that_is_not_a_week_is_not_the_newest_week(panel):
    """A stray name sorts after every date. check_feed refuses it under its
    own name; it is not what the writer last wrote, and is not judged as if
    it were."""
    stray = week(FRESH, without("GLD"))
    repo = panel({FRESH + ".json": week(FRESH),
                  "notes.json": stray, "zzz.json": stray}).parents[1]
    rep = names_gate(repo)
    assert lines(rep, "FAIL") == [], rep.render()
    assert lines(rep, "OK") == [
        "OK: feed: %s.json has a bar or a `missing` entry for each of the "
        "%d names the weekly writer fetches" % (FRESH, len(NAMES))]


def test_the_base_file_is_read_and_not_its_correction(panel):
    """The question is what the writer was asked to fetch. A correction is
    a copy made afterwards, and whether it is stale is another test's
    business (tests/test_instrument_sessions.py)."""
    fixed = week(FRESH)
    fixed["corrects"], fixed["reason"] = FRESH + ".json", "restated"
    repo = panel({FRESH + ".json": week(FRESH, without("GLD")),
                  FRESH + ".corrected.json": fixed}).parents[1]
    got = lines(names_gate(repo), "FAIL")
    assert len(got) == 1 and (FRESH + ".json has no bar") in got[0]


def test_a_correction_short_of_a_name_is_not_this_rules_finding(panel):
    short = week(FRESH, without("GLD"))
    short["corrects"], short["reason"] = FRESH + ".json", "restated"
    repo = panel({FRESH + ".json": week(FRESH),
                  FRESH + ".corrected.json": short}).parents[1]
    rep = names_gate(repo)
    assert lines(rep, "FAIL") == [] and len(lines(rep, "OK")) == 1


# -- a file from before the rule ---------------------------------------------

def test_the_runners_copy_of_a_committed_week_only_warns(panel):
    """The state on the runner on 2026-10-06, and on any run that writes no
    week before its copies are replaced. Nothing is wrong with the week,
    and failing it would send the job to fix a committed file."""
    rep = one(panel, stale_copy())
    assert lines(rep, "FAIL") == []
    assert lines(rep, "OK") == [], "the file is short, and is not called whole"
    got = lines(rep, "WARN")
    assert len(got) == 1
    assert ("WARN: feed: %s.json has no bar and no `missing` entry for "
            "['BTC', 'GLD']" % COPY) in got[0]
    assert ("It was fetched %s, before this check existed (%s)"
            % (COPY_FETCHED, tc.NAMES_RULE_SINCE)) in got[0]


def test_the_warning_says_which_copy_wins_and_what_never_happens(panel):
    msg = lines(one(panel, stale_copy()), "WARN")[0]
    assert ("where main holds %s.json with those names, main's copy "
            "replaces it" % COPY) in msg
    assert "Never write a committed week again" in msg
    assert "--config fails until" in msg
    for cure in ("remove", "write the week again", "Sync"):
        assert cure not in msg, (
            "what to do with a week that was never pushed has no place in "
            "front of a reader who is holding a committed one: " + cure)


def test_the_warning_claims_no_more_than_the_date(panel):
    """A file from before the rule may be short of a name that WAS being
    asked for. The line does not say nothing had asked: it says when the
    file was fetched, and that no run with this check wrote it."""
    doc = week(COPY, without("AAPL"), fetched_at=COPY_FETCHED)
    msg = lines(one(panel, doc), "WARN")[0]
    assert "['AAPL']" in msg
    assert "no run that had it wrote this file" in msg
    assert "nothing had asked" not in msg and "joined" not in msg


@pytest.mark.parametrize("stamp,level", [
    (tc.NAMES_RULE_SINCE + "T00:00:00Z", "FAIL"),   # the first second of it
    (DAY_BEFORE + "T23:59:59Z", "WARN"),            # the last second before
])
def test_the_line_between_them_is_the_day_the_rule_began(panel, stamp,
                                                         level):
    rep = one(panel, week(COPY, without("GLD"), fetched_at=stamp))
    other = "WARN" if level == "FAIL" else "FAIL"
    assert len(lines(rep, level)) == 1 and lines(rep, other) == []


def test_it_is_when_the_file_was_fetched_not_which_week_it_is(panel):
    """A holiday week is written a week late, and a week refused once is
    written by a later run. An old Friday in a fresh file was written by
    today's writer and is held like any other."""
    late = week(COPY, without("GLD"), fetched_at=week(FRESH)["fetched_at"])
    assert len(lines(one(panel, late), "FAIL")) == 1


@pytest.mark.parametrize("stamp", [None, "", "yesterday", 20261003,
                                   "03/10/2026 13:07"])
def test_a_stamp_that_says_nothing_excuses_nothing(panel, stamp):
    """"Fetched before" is the claim that lets a short file through with a
    warning. A stamp that cannot be read does not make it."""
    doc = week(COPY, without("GLD"))
    doc["fetched_at"] = stamp
    rep = one(panel, doc)
    got = lines(rep, "FAIL")
    assert len(got) == 1 and lines(rep, "WARN") == []
    assert "which does not show it was written before" in got[0]
    assert "It was fetched" not in got[0]


def test_a_file_with_no_stamp_at_all_fails(panel):
    doc = week(COPY, without("GLD"))
    del doc["fetched_at"]
    assert len(lines(one(panel, doc), "FAIL")) == 1


# -- what it leaves alone, and what must not break it ------------------------

@pytest.mark.parametrize("body", ["{ this is not json", "[1, 2, 3]"])
def test_a_file_it_cannot_read_is_the_file_gates_to_report(tmp_path, body):
    """One defect, one line. check_feed runs in the same mode and has
    already failed the file under its own name."""
    d = tmp_path / "data" / "weekly"
    d.mkdir(parents=True)
    (d / (FRESH + ".json")).write_text(body, encoding="utf-8", newline="\n")
    assert names_gate(tmp_path).lines == []
    rep = tc.Report()
    tc.check_feed(tmp_path, rep)
    assert len(lines(rep, "FAIL")) == 1


@pytest.mark.parametrize("junk", [
    "GLD",                                   # a bare string
    {"ticker": ["GLD"], "reason": "x"},      # unhashable where the name goes
    {"ticker": None, "reason": "x"},
    {"reason": "no ticker at all"},
    ["GLD"], 7, None,
])
def test_an_entry_that_names_no_ticker_hides_nothing_and_breaks_nothing(
        panel, junk):
    """Only an entry that names a ticker accounts for one. The unhashable
    one used to end the run with a traceback and no report."""
    doc = week(FRESH, without("BTC", "GLD"))
    doc["missing"] = [junk, {"ticker": "BTC", "reason": "no bar"}]
    got = lines(one(panel, doc), "FAIL")
    assert len(got) == 1 and "for ['GLD']" in got[0]


@pytest.mark.parametrize("missing", ["GLD", {"ticker": "GLD"}, 5, None])
def test_a_missing_that_is_not_a_list_accounts_for_nothing(panel, missing):
    doc = week(FRESH, without("GLD"))
    doc["missing"] = missing
    got = lines(one(panel, doc), "FAIL")
    assert len(got) == 1 and "for ['GLD']" in got[0]


def test_a_week_short_of_a_whole_set_does_not_print_three_hundred(panel):
    msg = lines(one(panel, week(FRESH, NAMES[:300])), "FAIL")[0]
    absent = sorted(NAMES[300:])
    assert "and %d more" % (len(absent) - 12) in msg
    assert "'%s'" % absent[11] in msg and "'%s'" % absent[12] not in msg


def test_nothing_to_say_where_there_is_no_weekly_panel(tmp_path):
    assert names_gate(tmp_path).lines == []
    (tmp_path / "data" / "weekly").mkdir(parents=True)
    assert names_gate(tmp_path).lines == []


# -- the weekly job's own line -----------------------------------------------

def check_dir(tmp_path, doc):
    """What step 6 of the weekly job assembles: its data, macro/facts.json
    and this script. No scan_pipeline/, no CLAUDE.md, nothing beside the
    script to import."""
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


def job_line(root, *modes):
    """`python <checkdir>/scripts/truth_check.py --repo <checkdir> --feed
    --derive`, as the prompt and the task card have it, run the day after
    the newest week in the dir. -S keeps site-packages out: the job's
    interpreter has pandas and yfinance, and this must not need them.
    (--derive has no market_state.json to judge in this dir and says so; it
    is on the line because the job's has it.)"""
    newest = sorted(p.stem for p in (root / "data" / "weekly").glob("*.json"))
    today = dt.date.fromisoformat(newest[-1]) + dt.timedelta(days=1)
    return subprocess.run(
        [sys.executable, "-S", str(root / "scripts" / "truth_check.py"),
         "--repo", str(root), *(modes or ("--feed", "--derive")),
         "--today", today.isoformat()],
        capture_output=True, text=True)


def test_the_weekly_jobs_line_stops_on_a_week_it_wrote_short(tmp_path):
    """The run that used to exit 0. What is left out here is a name the
    runner's own constants would not have either, so nothing on the runner
    could have said so."""
    r = job_line(check_dir(tmp_path, week(FRESH, without("GLD"))))
    assert r.returncode == 1, r.stdout + r.stderr
    assert ("FAIL: feed: %s.json has no bar and no `missing` entry for "
            "['GLD']" % FRESH) in r.stdout
    assert "1 fail" in r.stdout


def test_the_weekly_jobs_line_passes_a_whole_week(tmp_path):
    r = job_line(check_dir(tmp_path, week(FRESH)))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 fail" in r.stdout
    assert "for each of the %d names" % len(NAMES) in r.stdout


def test_the_weekly_jobs_line_does_not_stop_on_a_run_that_wrote_nothing(
        tmp_path):
    """Started before 13:00 UTC, or a Friday the writer refused: no new
    week, and the newest file in the check dir is the runner's copy of last
    week's, short of two names main's copy has had merged in. The job has
    nothing of its own to hold back, and must not be sent after that file."""
    r = job_line(check_dir(tmp_path, stale_copy()))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 fail" in r.stdout
    assert ("WARN: feed: %s.json has no bar and no `missing` entry for "
            "['BTC', 'GLD']" % COPY) in r.stdout


def test_config_is_no_use_in_that_directory(tmp_path):
    """The premise, not the rule: the mode that reads the constants cannot
    import them where the job runs its gate, which is why the list has to
    travel. If this ever passes, the reason for the list has changed."""
    r = job_line(check_dir(tmp_path, week(FRESH)), "--config")
    assert r.returncode == 1
    assert "cannot import scan_pipeline.config.tickers" in r.stdout


def test_an_unhashable_ticker_does_not_take_the_report_down(tmp_path):
    """From the command line, where it ended in a traceback: in this check
    as first written, and in check_silent_absence on main before it. A gate
    that dies prints no FAIL, and a job that reads the last line for the
    summary finds none. (Whether such an entry should itself fail the file
    is check_feed's question, and is not answered here.)"""
    doc = week(FRESH)
    doc["missing"] = [{"ticker": ["GLD"], "reason": "x"}]
    r = job_line(check_dir(tmp_path, doc), "--feed")
    assert "Traceback" not in r.stderr, r.stderr
    assert "SUMMARY:" in r.stdout


# -- where the rule runs -----------------------------------------------------

@pytest.mark.parametrize("workflow", ["ci.yml", "daily-observe.yml",
                                      "backfill.yml"])
def test_every_workflow_that_gates_the_panel_runs_the_feed_gate(workflow):
    """The rule lives under --feed so that every gate that has the panel in
    front of it asks. This guards the workflows, not the rule: a gate line
    that loses --feed loses it."""
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / workflow)
                         .read_text(encoding="utf-8"))
    runs = [str(step.get("run", "")) for job in doc["jobs"].values()
            for step in job["steps"]]
    gates = [r for r in runs if "truth_check.py" in r and "--feed" in r]
    assert gates, workflow + " no longer runs truth_check --feed"


def test_the_feed_mode_runs_the_rule():
    """A check nothing calls is decoration."""
    src = TRUTH.read_text(encoding="utf-8")
    feed_block = src.split("if run_all or args.feed:")[1].split(
        "if run_all or args.config:")[0]
    assert "check_feed_names(repo, rep)" in feed_block


# -- the real panel ----------------------------------------------------------

def test_the_newest_week_on_file_accounts_for_every_name():
    """The committed panel. This fails on the same week, and for the same
    reason, as the two real-panel tests in tests/test_config_gate.py, and
    clears when they do; it adds no new way for a push to turn the suite
    red."""
    rep = names_gate(ROOT)
    assert lines(rep, "FAIL") == [] and lines(rep, "WARN") == [], rep.render()
    assert len(lines(rep, "OK")) == 1


if __name__ == "__main__":
    # The list as the script should hold it, for pasting over the one there.
    print(literal(snapshot.equity_universe()))
