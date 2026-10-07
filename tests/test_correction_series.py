"""A correction is its base with its recorded edits applied, and the gate
says so.

A correction is a full copy of its base, and readers prefer it. It goes
stale the moment the base takes a merge: the names the base gained are then
invisible for that week, with no error anywhere (CLAUDE.md, "The correction
trap"). Until 2026-10-07 the only thing that held a correction's `series`
to its base was a test, for data/weekly, in a suite the backfill workflow
does not run. `truth_check --feed` holds it now, for data/daily as well.

Three things are pinned here beside the rule. What a line says of a
difference: which side moved, where the two files can tell. What it says
after that, which is what a rebuild would do and not what to do: three
drafts chose for the reader, and each was shown a case where the choice
silently undid something a correction said. And where it is a FAIL and
where a WARN: a checkout, or a copy.

No network. The panels are synthetic except where a test says committed.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys

import pytest

from conftest import ROOT, SCRIPTS, weekly_doc

import rebuild_corrections as rc  # noqa: E402
import truth_check as tc  # noqa: E402

DROP = {"ticker": "AVB", "reason": "zero-volume bar dropped from series"}
NAMES = ["AAPL", "AVB", "MSFT", "SPY"]
FETCHED = "2026-08-22T13:10:30Z"        # the base's own fetch
FIRST_MERGE = {"source": "yahoo-backfill",
               "fetched_at": "2026-08-26T04:08:06Z"}
MERGED = {"source": "yahoo-backfill", "fetched_at": "2026-10-06T01:48:08Z"}
TREASURY = {"source": "treasury", "fetched_at": "2026-08-22T16:01:19Z"}
RESTATED = {"source": "yahoo-backfill", "fetched_at": "2026-10-05T04:40:45Z"}
COMMAND = "`python scripts/rebuild_corrections.py`"

# What a sentence says of a bar its base holds and the correction does not.
# Evidence, and said as evidence: a stamp can be typed, and a bar taken out
# with its label leaves none.
GAINED = ("name(s) its base holds are not in it, each labelled there later "
          "than any stamp this correction carries (merged in since, on that "
          "evidence): ")
REWRITTEN = ("name(s) its base holds are not in it, and its base was fetched "
             "later than it was (written again since, on that evidence): ")
BEFORE = ("bar(s) its base holds are not in it, none labelled there later "
          "than this correction's newest stamp (held when the two were last "
          "in step, on that evidence), and it records no zero-volume drop "
          "of them: ")


def base_week(as_of="2026-08-21"):
    """A week as the panel has them: written on the Saturday, with one name
    (MSFT) merged in four days later under its own stamp."""
    doc = weekly_doc(as_of, NAMES, fetched_at=FETCHED)
    doc["series"]["AVB"] = {"close": 65.9005, "volume": 0}
    doc["rates"] = {"US10Y": {"close": 4.672, "volume": None},
                    "US2Y": {"close": 4.17, "volume": None}}
    doc["missing"] = [{"ticker": "EQR", "reason": "no bar dated " + as_of}]
    doc["provenance"] = {"series": {"MSFT": dict(FIRST_MERGE)},
                         "rates": {"US2Y": dict(TREASURY)}}
    return doc


def correction_of(base):
    """What rebuild_corrections.py writes for the AVB drop."""
    doc = copy.deepcopy(base)
    del doc["series"]["AVB"]
    doc["missing"] = sorted(doc["missing"] + [dict(DROP)],
                            key=lambda m: m["ticker"])
    doc["corrects"] = base["as_of"] + ".json"
    doc["reason"] = "AVB carried a zero-volume close; it moves to missing."
    return doc


def restating(base):
    """What restate_instruments.py writes: one close, recorded and
    labelled."""
    doc = copy.deepcopy(base)
    doc["corrects"], doc["reason"] = base["as_of"] + ".json", "Thursday's"
    doc["rates"]["US10Y"]["close"] = 4.72
    doc["provenance"]["rates"]["US10Y"] = dict(RESTATED)
    doc["restated"] = [{"block": "rates", "ticker": "US10Y",
                        "was": {"close": 4.672, "volume": None}}]
    return doc


def merge_into(base, *names, label=MERGED):
    """A merge: a bar and its own stamp, as backfill_weekly.py --merge
    writes them."""
    for name in names:
        base["series"][name] = {"close": 50.0, "volume": 1000}
        base["provenance"]["series"][name] = dict(label)


def found(corr, base):
    return tc.correction_problems(corr, base)


def said(corr, base):
    return " | ".join(found(corr, base))


def put(tmp_path, base, corr, subdir="weekly", git=True, tool=True):
    """A tree with one week and its correction. A checkout has a .git and
    the rebuild beside its data; the weekly job's check dir has only the
    gate."""
    folder = tmp_path / "data" / subdir
    folder.mkdir(parents=True, exist_ok=True)
    for name, doc in ((base["as_of"] + ".json", base),
                      (base["as_of"] + ".corrected.json", corr)):
        (folder / name).write_text(json.dumps(doc, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir(exist_ok=True)
    script, dot_git = scripts / "rebuild_corrections.py", tmp_path / ".git"
    if tool:
        script.write_text("# the tool is at hand\n", encoding="ascii")
    elif script.exists():
        script.unlink()
    if git:
        dot_git.mkdir(exist_ok=True)
    elif dot_git.is_dir():
        dot_git.rmdir()
    return tmp_path


def lines(repo, level, subdir="weekly"):
    rep = tc.Report()
    tc.check_feed(repo, rep, subdir=subdir,
                  require_friday=(subdir == "weekly"), label=subdir)
    return [line for line in rep.lines if line.startswith(level)]


def fails(repo, subdir="weekly"):
    return lines(repo, "FAIL", subdir)


MARK = "is not its base with its recorded edits applied"


def about_its_base(found_lines):
    """This check's own lines, among whatever else a tree draws."""
    return [line for line in found_lines if MARK in line]


def kept_by(rebuilt, corr):
    """Does a rebuilt correction still hold everything the correction held:
    every bar, every `missing` entry, every label, every stamp?"""
    return (all(rebuilt["series"].get(t) == bar
                for t, bar in corr["series"].items())
            and all(m in rebuilt["missing"] for m in corr["missing"])
            and all(rebuilt.get("provenance", {}).get(block, {}).get(t)
                    == label
                    for block, labels in corr.get("provenance", {}).items()
                    for t, label in labels.items())
            and all(rebuilt.get(k) == corr.get(k)
                    for k in tc.CORRECTION_STAMPS)
            and all(k in rebuilt for k in corr))


# -- a correction that is its base ---------------------------------------------

def test_a_drop_on_record_is_the_one_difference_allowed(tmp_path):
    base = base_week()
    corr = correction_of(base)
    assert found(corr, base) == []
    assert fails(put(tmp_path, base, corr)) == []


def test_a_correction_that_restates_an_instrument_keeps_its_own_label(
        tmp_path):
    """2026-08-28.corrected.json: a close changed, recorded in `restated`,
    and labelled with its own fetch. That label is the correction's, and
    not held to the base's."""
    base = base_week()
    corr = restating(base)
    assert found(corr, base) == []
    assert fails(put(tmp_path, base, corr)) == []


def test_the_committed_corrections_are_their_bases():
    weekly = ROOT / "data" / "weekly"
    for path in sorted(weekly.glob("*.corrected.json")):
        corr = json.loads(path.read_text(encoding="utf-8"))
        base = json.loads((weekly / (corr["as_of"] + ".json")).read_text(
            encoding="utf-8"))
        assert found(corr, base) == [], path.name


# -- which side moved, where the two files can say -----------------------------

def test_a_base_that_gained_names_leaves_the_correction_stale(tmp_path):
    """A merge adds BTC and GLD to the base, stamps them, and nobody
    rebuilds the correction. Readers prefer the correction, so for that
    week the two names do not exist. This is the case the gate is for."""
    base = base_week()
    corr = correction_of(base)
    merge_into(base, "BTC", "GLD")
    got = fails(put(tmp_path, base, corr))
    assert len(got) == 1, "said once: the names, not their labels as well"
    assert ("2026-08-21.corrected.json is not its base with its recorded "
            "edits applied: 2 " + GAINED + "BTC, GLD. Readers prefer the "
            "correction") in got[0]
    rebuilt = rc.apply_edits(base, corr)
    assert found(rebuilt, base) == [] and kept_by(rebuilt, corr)


def test_a_name_merged_in_before_the_correction_was_written_is_not_gained(
        tmp_path):
    """5,419 of the panel's 38,080 bars carry a label, in every base week:
    the 44 merged on 2026-08-26, the ETFs of the first week, the names of
    2026-10-06. A label alone does not say a bar came after the correction.
    PLTR, labelled in August, deleted in October from a correction that
    carries October's labels: it was there when the correction was last in
    step, and somebody took it out. Read as "gained since", the line sent
    its reader to the command that puts it back."""
    base = base_week()
    merge_into(base, "PLTR", label=FIRST_MERGE)
    merge_into(base, "BTC")
    corr = correction_of(base)                  # in step: holds both
    del corr["series"]["PLTR"]
    del corr["provenance"]["series"]["PLTR"]
    assert found(corr, base) == ["1 " + BEFORE + "PLTR"]

    # ... and the same bar missing from a correction that carries nothing
    # so late reads as merged in since.
    base = base_week()
    corr = correction_of(base)
    merge_into(base, "BTC")
    assert "1 " + GAINED + "BTC" in said(corr, base)

    # A bar with no label at all has been in the file since it was written.
    base = base_week()
    corr = correction_of(base)
    del corr["series"]["AAPL"]
    assert found(corr, base) == ["1 " + BEFORE + "AAPL"]


def test_a_name_from_the_same_merge_as_one_it_carries_is_not_gained_since():
    """One run stamps every name it merges with one fetched_at. BTC and
    GLD went in together; a correction that carries GLD's label was in
    step after that run, so BTC missing from it was taken out. Later, not
    later or equal."""
    base = base_week()
    merge_into(base, "BTC", "GLD")
    corr = correction_of(base)
    del corr["series"]["BTC"]
    del corr["provenance"]["series"]["BTC"]
    assert found(corr, base) == ["1 " + BEFORE + "BTC"]


def test_every_stamp_the_correction_carries_counts_an_instruments_too():
    """A correction restate_instruments.py wrote on the 7th, after the merge
    of the 6th, says when it was written in its instrument's label and
    nowhere else. BTC taken out of it read "gained since"."""
    base = base_week()
    merge_into(base, "BTC")
    corr = restating(base)
    corr["provenance"]["rates"]["US10Y"] = {
        "source": "yahoo-backfill", "fetched_at": "2026-10-07T10:00:00Z"}
    del corr["series"]["BTC"]
    del corr["provenance"]["series"]["BTC"]
    assert found(corr, base) == ["1 " + BEFORE + "BTC"]


def test_a_correction_with_no_stamp_that_reads_is_given_nothing():
    """Nothing says when it was last in step, so nothing says a name came
    after."""
    base = base_week()
    corr = correction_of(base)
    merge_into(base, "BTC")
    corr["fetched_at"], corr["provenance"] = None, {}
    text = said(corr, base)
    assert "1 " + BEFORE + "BTC" in text and "merged in since" not in text


def test_the_newest_name_taken_out_with_its_label_reads_as_never_there():
    """What two files cannot say, pinned so that nobody takes the sentence
    for more than it is. BTC is all the base gained in its last merge. Out
    of the correction with its label, what is left is byte for byte the
    correction as it stood before that merge, and it reads "merged in
    since". The line names the tool that can tell: the history."""
    base = base_week()
    stale = correction_of(base)
    merge_into(base, "BTC")
    in_step = rc.apply_edits(base, stale)
    assert found(in_step, base) == []
    by_hand = copy.deepcopy(in_step)
    del by_hand["series"]["BTC"]
    del by_hand["provenance"]["series"]["BTC"]
    assert by_hand == stale
    assert found(by_hand, base) == ["1 " + GAINED + "BTC. Readers prefer "
                                    "the correction, so to them those bars "
                                    "are not in the week"]
    assert ("`python scripts/panel_guard.py --against <commit>` says whether "
            "a correction has lost or changed anything it held at that "
            "commit") in tc.CORRECTION_NEXT


def test_a_base_written_again_is_told_from_a_stamp_changed_by_hand():
    """A declared rewrite restamps the base with a later fetch, and then
    every difference is the base having moved: names it has that the
    correction lacks were gained, whatever their labels. A correction whose
    own `fetched_at` was typed forward is not that, and one changed stamp
    used to excuse every other difference in the file."""
    base = base_week()
    corr = correction_of(base)
    base["fetched_at"] = "2026-10-06T02:00:00Z"
    base["series"]["NVDA"] = {"close": 223.96, "volume": 5}
    text = said(corr, base)
    assert "(its base's is the later, as after a rewrite)" in text
    assert "1 " + REWRITTEN + "NVDA" in text

    base = base_week()
    corr = correction_of(base)
    del corr["series"]["AAPL"]
    corr["fetched_at"] = "2026-10-06T02:00:00Z"     # the correction's own
    text = said(corr, base)
    assert "as after a rewrite" not in text
    assert "1 " + BEFORE + "AAPL" in text
    assert "written again since" not in text and "merged in since" not in text
    for stamp in ("the 6th", None, 20261006):
        corr["fetched_at"] = stamp
        text = said(corr, base)
        assert "since, on that evidence" not in text, stamp


def test_a_merge_that_filled_a_missing_name_leaves_it_stale_too():
    """EQR had no bar and was listed; a merge finds one. The base loses the
    entry and gains the bar, and the correction still lists it."""
    base = base_week()
    corr = correction_of(base)
    merge_into(base, "EQR")
    base["missing"] = []
    got = found(corr, base)
    assert any("1 " + GAINED + "EQR" in line for line in got)
    assert any('entries only here for "EQR", only in the base for none'
               in line for line in got)
    rebuilt = rc.apply_edits(base, corr)
    assert found(rebuilt, base) == []


# -- every way it can differ ---------------------------------------------------

def test_a_label_changed_or_kept_for_a_dropped_bar():
    base = base_week()
    base["provenance"]["series"]["AVB"] = dict(MERGED)
    corr = correction_of(base)                  # keeps AVB's label
    corr["provenance"]["series"]["MSFT"]["fetched_at"] = "2026-10-06T00:00:00Z"
    assert found(corr, base) == [
        "2 `provenance.series` label(s) are not its base's: AVB, MSFT. The "
        "label is the bar's own fetch, and a correction does not change "
        "when a bar was fetched"]
    assert found(rc.apply_edits(base, corr), base) == []


def test_an_instruments_label_is_held_to_the_base():
    """The label is what tells the Treasury 2-year from the futures mark
    every earlier file holds under the same key. A correction that lost it
    drew no line from the gate."""
    base = base_week()
    corr = correction_of(base)
    del corr["provenance"]["rates"]
    assert found(corr, base) == [
        "1 `provenance.rates` label(s) are not its base's, on an instrument "
        "`restated` does not name: US2Y. The label says whose number it is "
        "and for which session or contract, and readers go by it"]
    corr = correction_of(base)
    corr["provenance"]["rates"]["US2Y"]["source"] = "yahoo"
    assert "`provenance.rates`" in said(corr, base)


def test_a_label_only_the_correction_has_is_asked_about():
    """VIX's close and its label typed into a correction with the
    `restated` entry left out, which is where restate_instruments.py sends
    whoever wants a second restatement in a week. The label is all this
    check sees of it, and the close is _feed_restated_check's."""
    base = base_week()
    corr = correction_of(base)
    corr["provenance"]["rates"]["US10Y"] = dict(RESTATED)
    assert "1 `provenance.rates` label(s) are not its base's" in \
        said(corr, base)
    assert "US10Y" in said(corr, base)
    assert found(restating(base), base) == [], "recorded, it is its own"

    # ... and recording one restatement does not excuse the other labels
    corr = restating(base)
    del corr["provenance"]["rates"]["US2Y"]
    assert found(corr, base) == [
        "1 `provenance.rates` label(s) are not its base's, on an instrument "
        "`restated` does not name: US2Y. The label says whose number it is "
        "and for which session or contract, and readers go by it"]


@pytest.mark.parametrize("key, value", [
    ("source", "yahoo-backfill"), ("fetched_at", "2026-10-06T00:00:00Z"),
    ("session_note", "Friday holiday; bars from 2026-08-20")])
def test_a_correction_carries_its_bases_stamps(key, value):
    """fetched_at is the adjustment anchor of every close under it. A
    correction is a copy: its bars were fetched when its base's were."""
    base = base_week()
    corr = correction_of(base)
    corr[key] = value
    assert len(found(corr, base)) == 1
    assert "its `%s` is" % key in said(corr, base)
    assert "as after a rewrite" not in said(corr, base)


def test_what_else_a_file_says_of_itself_is_copied_too():
    """A daily correction that lacked `cadence`, or changed it, drew
    nothing."""
    base = base_week("2026-08-20")
    base["cadence"], base["source"] = "daily", "yahoo-daily"
    corr = correction_of(base)
    assert found(corr, base) == []
    del corr["cadence"]
    assert found(corr, base) == [
        'its `cadence` is null where its base\'s is "daily"; a correction '
        "is a copy of its base and says the same of itself"]
    corr["cadence"] = "weekly"
    assert "its `cadence` is \"weekly\"" in said(corr, base)
    assert found(rc.apply_edits(base, corr), base) == []


def test_the_avb_drop_with_its_reason_blanked(tmp_path):
    """Rehearsed on the committed week: blank the reason and the record of
    the drop is gone. Two lines, the bar and the entry that no longer
    records its drop.

    What a rebuild does with it is why no line tells its reader to run
    one. With nothing else on record it skips the file. With a restated
    instrument beside the drop it goes ahead, and the zero-volume print is
    back in every reader's panel with nothing left for this check to
    say."""
    base = base_week()
    corr = correction_of(base)
    corr["missing"] = [m if m["ticker"] != "AVB"
                       else {"ticker": "AVB", "reason": "see above"}
                       for m in corr["missing"]]
    got = found(corr, base)
    assert len(got) == 2
    assert "no zero-volume drop of them: AVB" in got[0]
    assert 'entries only here for "AVB"' in got[1]

    repo = put(tmp_path, base, corr)
    path = repo / "data" / "weekly" / "2026-08-21.corrected.json"
    before = path.read_bytes()
    assert rc.rebuild(path) == "skip"
    assert path.read_bytes() == before

    corr = restating(base)
    del corr["series"]["AVB"]
    corr["missing"].append({"ticker": "AVB", "reason": "see above"})
    assert len(found(corr, base)) == 2
    put(tmp_path, base, corr)
    assert rc.rebuild(path) == "rebuilt"
    rebuilt = json.loads(path.read_text(encoding="utf-8"))
    assert rebuilt["series"]["AVB"] == {"close": 65.9005, "volume": 0}
    assert found(rebuilt, base) == [] and not kept_by(rebuilt, corr)


@pytest.mark.parametrize("volume", [1_875_900, None])
def test_a_drop_of_a_bar_that_is_not_on_volume_0(volume):
    """rebuild_corrections.py prints ABORT for this and leaves the file.
    A null volume is not 0: AVB in 2026-08-28.json is such a print, and no
    correction drops it."""
    base = base_week()
    corr = correction_of(base)
    base["series"]["AVB"]["volume"] = volume
    got = found(corr, base)
    assert len(got) == 1, "said once: the drop, not its entry as well"
    assert "it records a zero-volume drop of AVB" in got[0]
    assert "which is not a bar on volume 0" in got[0]
    with pytest.raises(rc.BaseMoved):
        rc.apply_edits(base, corr)


def test_a_bar_typed_into_a_correction():
    base = base_week()
    corr = correction_of(base)
    corr["series"]["NVDA"] = {"close": 223.96, "volume": 105_669_400}
    assert found(corr, base) == [
        "1 name(s) are in it and not in its base: NVDA. A correction holds "
        "no bar its base does not"]
    assert "NVDA" not in rc.apply_edits(base, corr)["series"]


def test_an_equity_close_changed_in_a_correction():
    base = base_week()
    corr = correction_of(base)
    corr["series"]["AAPL"]["close"] = 99.5
    text = said(corr, base)
    assert "1 bar(s) differ from its base's: AAPL" in text
    assert '"close": 99.5' in text and '"close": 100.0' in text
    assert "a rebuild writes the base's bar back" in text
    assert rc.apply_edits(base, corr)["series"]["AAPL"]["close"] == 100.0


def test_a_key_of_its_own():
    """A rebuild copies the base and adds three keys. A fourth is gone
    after it, and nothing said so."""
    base = base_week()
    corr = correction_of(base)
    corr["note"] = "AVB was acquired on the 18th"
    assert found(corr, base) == [
        "1 key(s) of its own that its base does not have: note. A "
        "correction adds `corrects`, `reason` and `restated` to its base "
        "and nothing else"]
    assert "note" not in rc.apply_edits(base, corr)
    assert found(restating(base), base) == []
    # ... and `provenance` is not one: a base with no label of any kind
    # gets its first from the restatement.
    bare = base_week()
    del bare["provenance"]
    corr = copy.deepcopy(bare)
    corr["corrects"], corr["reason"] = "2026-08-21.json", "Thursday's"
    corr["rates"]["US10Y"]["close"] = 4.72
    corr["provenance"] = {"rates": {"US10Y": dict(RESTATED)}}
    corr["restated"] = [{"block": "rates", "ticker": "US10Y",
                         "was": {"close": 4.672, "volume": None}}]
    assert found(corr, bare) == []
    assert rc.apply_edits(bare, corr) == corr


# -- `missing` ----------------------------------------------------------------

def test_a_missing_entry_only_one_of_them_has():
    base = base_week()
    corr = correction_of(base)
    corr["missing"].append({"ticker": "HES", "reason": "delisted"})
    assert 'only here for "HES", only in the base for none' in said(corr, base)

    corr = correction_of(base)
    corr["missing"] = [m for m in corr["missing"] if m["ticker"] != "EQR"]
    assert 'only here for none, only in the base for "EQR"' in \
        said(corr, base)


def test_missing_is_compared_entry_by_entry_and_not_by_name():
    """The same name with another reason is another entry, and the same
    entry twice is not the same as once."""
    base = base_week()
    corr = correction_of(base)
    for m in corr["missing"]:
        if m["ticker"] == "EQR":
            m["reason"] = "likely pre-IPO or not trading"
    assert 'only here for "EQR", only in the base for "EQR"' in \
        said(corr, base)

    corr = correction_of(base)
    corr["missing"].append(dict(base["missing"][0]))
    assert 'only here for "EQR", only in the base for none' in said(corr, base)
    assert "counted as often as it is there" in said(corr, base)

    # an entry for a bar the correction holds as well
    corr = correction_of(base)
    corr["missing"].append({"ticker": "SPY", "reason": "halted"})
    assert 'only here for "SPY"' in said(corr, base)


def test_one_entry_stands_for_a_drop_and_it_is_the_last():
    """Two entries with the word for one name: the rebuild keeps the last
    and writes it once."""
    base = base_week()
    corr = correction_of(base)
    corr["missing"].append({"ticker": "AVB", "reason": "zero-volume, again"})
    assert 'only here for "AVB"' in said(corr, base)
    rebuilt = rc.apply_edits(base, corr)
    assert [m["reason"] for m in rebuilt["missing"]
            if m["ticker"] == "AVB"] == ["zero-volume, again"]
    assert found(rebuilt, base) == []


def test_a_drop_entry_for_a_bar_the_base_never_held_is_not_a_drop():
    """The word in a reason is a record only of a bar the base holds."""
    base = base_week()
    corr = correction_of(base)
    corr["missing"].append({"ticker": "GHOST",
                            "reason": "zero-volume, they say"})
    assert 'only here for "GHOST"' in said(corr, base)


def test_two_shapes_a_rebuild_leaves_alone_are_not_findings():
    """What a rebuild writes is never a finding. A base that lists the
    dropped name in its own `missing`, with the word, and still holds the
    bar: the rebuild adds the entry again and the correction has it twice.
    And a base with a label for a name it does not hold, which fails under
    the base's own name and is copied as it stands."""
    base = base_week()
    base["missing"].append(dict(DROP))
    corr = rc.apply_edits(base, correction_of(base))
    assert [m["ticker"] for m in corr["missing"]].count("AVB") == 2
    assert found(corr, base) == []

    # ... and where the base lists it in other words, the rebuild writes
    # the correction's own entry beside the base's: the last it has.
    base = base_week()
    base["missing"].append({"ticker": "AVB",
                            "reason": "zero-volume, as the base has it"})
    corr = rc.apply_edits(base, correction_of(base))
    assert sorted(m["reason"] for m in corr["missing"]
                  if m["ticker"] == "AVB") == [
        "zero-volume bar dropped from series",
        "zero-volume, as the base has it"]
    assert found(corr, base) == []

    base = base_week()
    base["provenance"]["series"]["GHOST"] = dict(MERGED)
    corr = rc.apply_edits(base, correction_of(base))
    assert "GHOST" in corr["provenance"]["series"]
    assert found(corr, base) == []
    del corr["provenance"]["series"]["GHOST"]
    assert "`provenance.series` label(s) are not its base's: GHOST" in \
        said(corr, base)


def test_an_entry_that_is_not_an_entry_does_not_break_the_check():
    """`missing` holding anything else is another check's to fail, under
    its own line and not twice. This one must still answer for the bars."""
    base = base_week()
    corr = correction_of(base)
    corr["missing"] += [None, "AVB", {"ticker": ["A"], "reason": 3},
                        {"ticker": "X"}]
    assert found(corr, base) == []
    corr["missing"] = "none"
    assert "AVB" in said(corr, base)
    for junk in ({}, {"series": []}, {"series": {"SPY": 3}, "provenance": 7,
                                      "restated": "no", "missing": {},
                                      "fetched_at": 9}):
        assert isinstance(found(junk, base), list)
        assert isinstance(found(corr, junk), list)


@pytest.mark.parametrize("reason, is_a_drop", [
    ("zero-volume bar dropped from series", True),
    ("a print on zero-volume, moved here", True),
    ("Zero-Volume bar", False),
    ("ZERO-VOLUME", False),
    ("zero volume", False),
    ("no bar", False),
])
def test_the_two_scripts_read_a_drop_off_the_same_word(reason, is_a_drop):
    """Anywhere in the reason, and as it is spelled. The rebuild reads its
    record of a drop off this word; a gate that read it another way would
    pass a correction the rebuild writes differently."""
    base = base_week()
    corr = correction_of(base)
    corr["missing"] = [m if m["ticker"] != "AVB"
                       else {"ticker": "AVB", "reason": reason}
                       for m in corr["missing"]]
    assert (list(rc.recorded_edits(corr)[0]) == ["AVB"]) == is_a_drop
    assert (found(corr, base) == []) == is_a_drop
    assert tc.ZERO_VOLUME_DROP in DROP["reason"]


# -- which week a correction is held to ----------------------------------------

@pytest.mark.parametrize("corrects", [
    "2026-08-21.corrected.json", "", ".", "2026-08-14.json", "../weekly",
    None, 7])
def test_a_correction_is_held_to_the_week_it_is_named_for(tmp_path, corrects):
    """Readers pair the two files by name and never read `corrects`. Found
    through `corrects`, a correction that named itself was compared with
    itself, and one that named "" passed on the directory: ten series for a
    week of 336, through the gate, the guard and both tests."""
    base = base_week()
    corr = correction_of(base)
    corr["series"] = {"SPY": dict(base["series"]["SPY"])}
    corr["corrects"] = corrects
    got = fails(put(tmp_path, base, corr))
    assert any("'corrects'" in line for line in got)
    assert any("are not in it" in line and "AAPL" in line for line in got), \
        "still held to 2026-08-21.json, whatever it says it corrects"


def test_the_rebuild_pairs_them_by_name_as_well(tmp_path, capsys):
    """It paired by `corrects`: 2026-08-28.corrected.json saying
    2026-08-21.json was written again as a copy of the other week, as_of
    2026-08-21, under a line of this gate that named the command."""
    other = base_week("2026-08-21")
    base = base_week("2026-08-28")
    corr = correction_of(base)
    corr["corrects"] = "2026-08-21.json"
    put(tmp_path, other, correction_of(other))
    repo = put(tmp_path, base, corr)
    path = repo / "data" / "weekly" / "2026-08-28.corrected.json"
    before = path.read_bytes()
    assert rc.rebuild(path) == "abort"
    assert path.read_bytes() == before
    out = capsys.readouterr().out
    assert ("ABORT 2026-08-28.corrected.json: its 'corrects' is "
            "'2026-08-21.json', and the week it is named for is "
            "2026-08-28.json") in out
    said_here = [line for line in fails(repo) if "2026-08-28.corr" in line]
    assert any("scripts/rebuild_corrections.py leaves it alone until "
               "`corrects` says so" in line for line in said_here)

    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "rebuild_corrections.py"), "--dir",
         str(repo / "data" / "weekly")], capture_output=True, text=True)
    assert done.returncode == 1, "the backfill workflow stops on it"
    assert "rebuilt 2026-08-21.corrected.json" in done.stdout


def test_a_correction_with_no_week_beside_it_says_so(tmp_path):
    base = base_week()
    corr = correction_of(base)
    repo = put(tmp_path, base, corr)
    (repo / "data" / "weekly" / "2026-08-21.json").unlink()
    got = [line for line in fails(repo) if "2026-08-21.corrected" in line]
    assert any("lacks 'corrects' pointing at an existing original" in line
               for line in got)


# -- what the line says after that, and where it stops anything ----------------

def every_kind():
    """One correction for each sentence the check can say, and whether a
    rebuild keeps what that correction holds."""
    def gained(base, corr):
        merge_into(base, "BTC")

    def rewritten(base, corr):
        base["fetched_at"] = "2026-10-06T02:00:00Z"
        base["series"]["AAPL"]["close"] = 99.4

    def label_lost(base, corr):
        del corr["provenance"]["rates"]

    def entry_lost(base, corr):
        corr["missing"] = [m for m in corr["missing"]
                           if m["ticker"] != "EQR"]

    def dropped_without_a_record(base, corr):
        del corr["series"]["AAPL"]

    def a_drop_the_base_does_not_bear_out(base, corr):
        base["series"]["AVB"]["volume"] = 9

    def a_bar_of_its_own(base, corr):
        corr["series"]["NVDA"] = {"close": 1.0, "volume": 1}

    def a_close_changed(base, corr):
        corr["series"]["SPY"]["volume"] = 7

    def a_stamp_changed(base, corr):
        corr["source"] = "yahoo-backfill"

    def a_label_changed(base, corr):
        corr["provenance"]["series"]["MSFT"]["source"] = "yahoo"

    def a_label_of_its_own(base, corr):
        corr["provenance"]["rates"]["US10Y"] = dict(RESTATED)

    def an_entry_of_its_own(base, corr):
        corr["missing"].append({"ticker": "HES", "reason": "delisted"})

    def a_key_of_its_own(base, corr):
        corr["note"] = "x"

    mends = [gained, label_lost, entry_lost]
    takes_out = [rewritten, dropped_without_a_record,
                 a_drop_the_base_does_not_bear_out, a_bar_of_its_own,
                 a_close_changed, a_stamp_changed, a_label_changed,
                 a_label_of_its_own, an_entry_of_its_own, a_key_of_its_own]
    return [(kind, True) for kind in mends] + [
        (kind, False) for kind in takes_out]


KINDS = pytest.mark.parametrize(
    "mutate, mended", every_kind(), ids=lambda v: getattr(v, "__name__", ""))


@KINDS
def test_a_rebuild_mends_some_of_these_and_takes_the_rest_out(mutate, mended):
    """Why the line says what a rebuild would do and stops there. For some
    of these a rebuild writes a correction that holds everything this one
    does, and more. For the rest it refuses, or what comes out no longer
    holds something this one said: a bar back that was dropped, a bar or
    an entry or a key gone, a close or a label or a stamp reverted. (After
    a rewrite of the base that is right, and the base's doing. The check
    cannot always tell, and three drafts that tried were each shown a case
    they got wrong.) Either way the check has nothing left to say."""
    base = base_week()
    corr = correction_of(base)
    mutate(base, corr)
    assert found(corr, base), "this kind is one the check says something of"
    was = copy.deepcopy(corr)
    try:
        rebuilt = rc.apply_edits(base, corr)
    except rc.BaseMoved:
        assert not mended
        return
    assert found(rebuilt, base) == []
    lost = not kept_by(rebuilt, was) or (
        set(rebuilt["series"]) - set(was["series"]) - {"BTC"} != set())
    assert lost == (not mended)


@KINDS
def test_in_a_checkout_each_is_a_fail_that_says_what_a_rebuild_would_do(
        tmp_path, mutate, mended):
    """One ending, whatever was found. It names the command once, as what
    would be run and not as what to run; it says to read every line about
    the directory first; and it says when to leave the files alone."""
    base = base_week()
    corr = correction_of(base)
    mutate(base, corr)
    sentences = found(corr, base)
    got = about_its_base(fails(put(tmp_path, base, corr)))
    assert len(got) == len(sentences)
    for sentence, line in zip(sentences, got):
        assert line.isascii()
        assert line == ("FAIL: feed: 2026-08-21.corrected.json is not its "
                        "base with its recorded edits applied: " + sentence
                        + "." + tc.CORRECTION_NEXT % "")
        assert COMMAND not in sentence and "rebuild" not in sentence.replace(
            "a rebuild writes the base's bar back", "")
    ending = tc.CORRECTION_NEXT % ""
    assert ending.count(COMMAND) == 1
    assert ending.startswith(" What a rebuild would do: " + COMMAND)
    assert "run " not in ending and "Run " not in ending
    assert "It also takes out, silently, anything the correction says " \
           "without a record" in ending
    assert "or the rebuild skips or stops at a file this check still " \
           "fails" in ending
    assert "So read every line about this directory's corrections first" \
        in ending
    assert "leave the files as they are and take it to whoever wrote the " \
           "correction, or to the owner" in ending
    for word in ("main", "level it", "sync_feed_copy"):
        assert word not in ending, word


@KINDS
@pytest.mark.parametrize("subdir", ["weekly", "daily"])
def test_in_a_copy_each_is_a_warning_and_names_no_command(
        tmp_path, subdir, mutate, mended):
    """The weekly job's check dir: a copy of the runner's data and this one
    script. Nothing there can rebuild a correction or may write one, and a
    FAIL the job cannot clear ends in a week that is not pushed. The stale
    correction check_silent_absence reports is a WARN there for the same
    reason (#139). Every kind, in both directories."""
    base = base_week("2026-08-21")
    if subdir == "daily":
        base["cadence"], base["source"] = "daily", "yahoo-daily"
    corr = correction_of(base)
    mutate(base, corr)
    sentences = found(corr, base)
    repo = put(tmp_path, base, corr, subdir, git=False, tool=False)
    assert about_its_base(fails(repo, subdir)) == []
    got = about_its_base(lines(repo, "WARN", subdir))
    assert len(got) == len(sentences)
    for line in got:
        assert line.endswith(tc.CORRECTION_ON_A_COPY)
        assert "`python" not in line and "run " not in line
        assert "it is a copy" in line and "It stops nothing here." in line
        assert ("Nothing here writes or rebuilds a correction, and nothing "
                "here should change either file or push one") in line


@pytest.mark.parametrize("git, tool, checkout", [
    (True, True, True), (False, True, False), (True, False, False),
    (False, False, False)])
def test_a_checkout_has_a_dot_git_and_the_rebuild_beside_its_data(
        tmp_path, git, tool, checkout):
    """Both. The runner holds check dirs filled with the whole of scripts/,
    the rebuild among them (auditor_2026-09-19/checkdir): run there, it
    would mend a copy. And an export of the repository has the script and
    no .git."""
    base = base_week()
    corr = correction_of(base)
    merge_into(base, "BTC")
    repo = put(tmp_path, base, corr, git=git, tool=tool)
    assert (len(fails(repo)) == 1) == checkout
    assert (len([line for line in lines(repo, "WARN")
                 if "it is a copy" in line]) == 1) == (not checkout)


def test_a_linked_worktrees_dot_git_is_a_file(tmp_path):
    base = base_week()
    corr = correction_of(base)
    merge_into(base, "BTC")
    repo = put(tmp_path, base, corr, git=False)
    (repo / ".git").write_text("gitdir: elsewhere\n", encoding="ascii")
    assert len(fails(repo)) == 1
    (repo / ".git").unlink()


def test_a_daily_correction_is_held_the_same_way(tmp_path):
    """No correction of a daily file exists and no tool writes one. The
    first is held to its base from the day it is written, and its line
    names the rebuild for its own directory."""
    base = base_week("2026-08-20")
    base["cadence"], base["source"] = "daily", "yahoo-daily"
    corr = correction_of(base)
    assert fails(put(tmp_path, base, corr, "daily"), "daily") == []
    merge_into(base, "BTC")
    got = fails(put(tmp_path, base, corr, "daily"), "daily")
    assert len(got) == 1 and "1 " + GAINED + "BTC" in got[0]
    assert got[0].endswith(tc.CORRECTION_NEXT % " --dir data/daily")
    assert "`python scripts/rebuild_corrections.py --dir data/daily`" in got[0]


def test_a_stale_correction_that_restates_is_held_like_any_other(tmp_path):
    """2026-08-28.corrected.json is this kind, and the only tool that
    writes a correction writes this kind."""
    base = base_week()
    corr = restating(base)
    merge_into(base, "BTC")
    got = fails(put(tmp_path, base, corr))
    assert len(got) == 1 and "1 " + GAINED + "BTC" in got[0]
    assert found(rc.apply_edits(base, corr), base) == []


def test_what_the_line_says_of_the_rebuild_is_what_it_does(tmp_path):
    """It "writes every correction in the directory again" was not so, and
    a reader told a rebuild mends a line watched it skip the file and exit
    0. Three corrections in one directory: one behind its base with an edit
    on record, one that records nothing, one whose record its base no
    longer bears out."""
    behind = base_week("2026-08-14")
    behind_corr = correction_of(behind)
    merge_into(behind, "BTC")
    nothing = base_week("2026-08-21")
    nothing_corr = correction_of(nothing)
    nothing_corr["missing"] = [m for m in nothing_corr["missing"]
                               if m["ticker"] != "AVB"]
    refuted = base_week("2026-08-28")
    refuted_corr = correction_of(refuted)
    refuted["series"]["AVB"]["volume"] = 9
    for base, corr in ((behind, behind_corr), (nothing, nothing_corr),
                       (refuted, refuted_corr)):
        repo = put(tmp_path, base, corr)
    weekly = repo / "data" / "weekly"
    before = {p.name: p.read_bytes() for p in weekly.glob("*.corrected.json")}

    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "rebuild_corrections.py"), "--dir",
         str(weekly)], capture_output=True, text=True)
    assert done.returncode == 1
    assert "rebuilt 2026-08-14.corrected.json" in done.stdout
    assert "skip 2026-08-21.corrected.json" in done.stdout
    assert "ABORT 2026-08-28.corrected.json" in done.stdout
    after = {p.name: p.read_bytes() for p in weekly.glob("*.corrected.json")}
    assert after["2026-08-14.corrected.json"] != \
        before["2026-08-14.corrected.json"], "written again"
    for name in ("2026-08-21.corrected.json", "2026-08-28.corrected.json"):
        assert after[name] == before[name], "left as it was"
    # ... and the two it did not write are still said, which is where the
    # line tells its reader to stop.
    still = about_its_base(fails(repo))
    assert {line.split()[2] for line in still} == {
        "2026-08-21.corrected.json", "2026-08-28.corrected.json"}
    ending = tc.CORRECTION_NEXT % ""
    for claim in (
            "goes through every correction in the directory",
            "One with an edit on record it writes again from its base as it "
            "is now, one with none it skips, and one whose record the base "
            "no longer bears out it leaves alone, printing ABORT and "
            "exiting 1 once the others are written"):
        assert claim in ending


def test_one_instrument_is_restated_once(tmp_path):
    """Named twice in `restated`, the rebuild re-applies the first and
    then finds the base's close is not what the second replaced. The gate
    was silent."""
    base = base_week()
    corr = restating(base)
    corr["restated"].append(copy.deepcopy(corr["restated"][0]))
    got = fails(put(tmp_path, base, corr))
    assert len(got) == 1
    assert "'restated' names rates.US10Y twice" in got[0]
