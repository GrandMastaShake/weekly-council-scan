"""panel_guard: what a panel file held, it still holds.

Two failures are behind it. On 2026-08-26 a targeted backfill replaced every
weekly file with just its 44 --only tickers -- 287 series became 44 across
107 files -- and the workflow reported success, because the counts were
printed with nothing to compare them to. The guard written for that counted
series per file. A count does not move when a bar is written over: rehearsed
on a copy of the panel on 2026-10-06, a merge that rewrote 4,612 committed
bars got "0 grew, 0 added; OK" from it, and CI carried the same count.

So the guard compares bars now, and CI and the daily job run the same
comparison against a commit. The last third of this file runs the workflow
steps themselves, because a guard nobody calls, or whose exit code a shell
line swallows, has not guarded anything.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest
import yaml

import panel_guard
from conftest import ROOT, SCRIPTS, weekly_doc

GUARD = SCRIPTS / "panel_guard.py"
TICKERS = ["SPY", "AAPL", "MSFT", "XOM", "JNJ"]
STAMP = {"source": "yahoo-backfill", "fetched_at": "2026-10-06T04:08:06Z"}


def cli(*args, cwd=None, env=None):
    """The guard as the workflows run it: its own process."""
    return subprocess.run([sys.executable, str(GUARD), *args],
                          capture_output=True, text=True, cwd=cwd, env=env)


def run(*args):
    """The same command line, in this process: what main() returns or exits
    with, and what it printed. A process per case is most of a minute on
    Windows; the cases that are about the process use cli()."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = panel_guard.main(list(args))
        except SystemExit as exit_:
            code = exit_.code
            if not isinstance(code, int):       # None, or a message
                if code is not None:
                    print(code, file=sys.stderr)
                code = 0 if code is None else 1
    return types.SimpleNamespace(returncode=code, stdout=out.getvalue(),
                                 stderr=err.getvalue())


def snapshot(weekly: Path, out: Path):
    return run("--snapshot", str(out), "--weekly-dir", str(weekly))


def compare(weekly: Path, before: Path, *extra):
    return run("--compare", str(before), "--weekly-dir", str(weekly), *extra)


def edit(directory: Path, name: str, change):
    """Rewrite one file through change(doc), as a writer would."""
    path = directory / name
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def rewrite(weekly: Path, name: str, tickers):
    edit(weekly, name, lambda doc: doc.update(
        series={t: v for t, v in doc["series"].items() if t in tickers}))


def week(as_of: str) -> dict:
    """A weekly file as the Saturday job writes one: the instruments, and a
    label on the two that are not the file's own provider's bar."""
    doc = weekly_doc(as_of, TICKERS)
    doc["rates"] = {"US10Y": {"close": 4.672, "volume": None},
                    "US2Y": {"close": 4.17, "volume": None}}
    doc["vol"] = {"VIX": {"close": 14.51, "volume": None}}
    doc["commodities"] = {"WTI": {"close": 91.11, "volume": 337181}}
    doc["fx"] = {"DXY": {"close": 99.16, "volume": None}}
    doc["provenance"] = {
        "rates": {"US2Y": {"source": "treasury",
                           "fetched_at": doc["fetched_at"]}},
        "commodities": {"WTI": {"source": "yahoo", "contract": "CLX26",
                                "fetched_at": doc["fetched_at"]}},
    }
    return doc


def guarded(panel, tmp_path, files=None):
    """A panel with a snapshot taken: (weekly directory, snapshot path)."""
    w = panel(files or {"2026-08-21.json": week("2026-08-21"),
                        "2026-08-14.json": week("2026-08-14")})
    before = tmp_path / "before.json"
    assert snapshot(w, before).returncode == 0
    return w, before


# -- what it has always done ---------------------------------------------------

def test_unchanged_panel_passes(panel, tmp_path):
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    before = tmp_path / "before.json"
    assert snapshot(w, before).returncode == 0
    r = compare(w, before)
    assert r.returncode == 0
    assert "every one of the 5 entries the panel held is still there" \
        in r.stdout


def test_growth_passes_because_that_is_what_a_backfill_is_for(panel, tmp_path):
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    before = tmp_path / "before.json"
    snapshot(w, before)

    edit(w, "2026-08-21.json", lambda doc: doc["series"].update(
        PLTR={"close": 1.0, "volume": 1}))

    r = compare(w, before)
    assert r.returncode == 0
    assert "1 grew" in r.stdout


def test_series_loss_fails_the_run(panel, tmp_path):
    """The incident, in miniature."""
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS),
               "2026-08-14.json": weekly_doc("2026-08-14", TICKERS)})
    before = tmp_path / "before.json"
    snapshot(w, before)

    rewrite(w, "2026-08-21.json", {"AAPL"})

    r = compare(w, before)
    assert r.returncode == 1
    assert "PANEL GUARD FAILED" in r.stdout
    assert "weekly/2026-08-21.json" in r.stdout
    assert "4 gone: series.JNJ, series.MSFT, series.SPY, series.XOM" \
        in r.stdout                  # 5 -> 1
    assert "2026-08-14.json" not in r.stdout.split("FAILED")[1]
    assert "Nothing has been committed" in r.stdout


def test_a_vanished_file_fails_too(panel, tmp_path):
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS),
               "2026-08-14.json": weekly_doc("2026-08-14", TICKERS)})
    before = tmp_path / "before.json"
    snapshot(w, before)
    (w / "2026-08-21.json").unlink()

    r = compare(w, before)
    assert r.returncode == 1
    assert "weekly/2026-08-21.json" in r.stdout
    assert "FILE GONE (5 entries)" in r.stdout


def test_a_file_shape_it_does_not_recognise_is_refused(panel, tmp_path):
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    before = tmp_path / "before.json"
    snapshot(w, before)
    (w / "2026-08-21.json").write_text(json.dumps({"as_of": "2026-08-21"}),
                                       encoding="utf-8")

    r = compare(w, before)
    assert r.returncode != 0
    assert "no 'series' object" in (r.stdout + r.stderr)


@pytest.mark.parametrize("content", [b"{", b"\xff\xfe{}"],
                         ids=["cut short", "not UTF-8"])
def test_a_file_that_does_not_parse_is_refused_not_a_traceback(
        panel, tmp_path, content):
    w, before = guarded(panel, tmp_path)
    (w / "2026-08-21.json").write_bytes(content)

    r = compare(w, before)
    assert r.returncode != 0
    assert "does not parse as JSON" in r.stderr
    assert "Traceback" not in r.stderr


def test_snapshot_covers_every_file_not_just_one_month(panel, tmp_path):
    """The step this replaced globbed data/weekly/2026-08-*.json, so 103 of
    the 107 files it was meant to protect were never looked at."""
    w = panel({
        "2024-09-06.json": weekly_doc("2024-09-06", TICKERS),
        "2026-08-21.json": weekly_doc("2026-08-21", TICKERS),
    })
    before = tmp_path / "before.json"
    snapshot(w, before)
    held = json.loads(before.read_text(encoding="utf-8"))["files"]
    assert set(held) == {"weekly/2024-09-06.json", "weekly/2026-08-21.json"}

    rewrite(w, "2024-09-06.json", {"AAPL"})
    assert compare(w, before).returncode == 1


# -- what a count cannot see ---------------------------------------------------

@pytest.mark.parametrize("field, value, said", [
    ("close", 101.25, "series.XOM close 100.0 -> 101.25"),
    ("volume", 0, "series.XOM volume 1000000 -> 0"),
])
def test_a_changed_bar_fails_the_run(panel, tmp_path, field, value, said):
    """One ticker's bar is written over between the snapshot and the
    compare: five series before, five after. Until 2026-10-06 this printed
    "0 grew, 0 added" and "OK -- no file lost series", and exited 0."""
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS),
               "2026-08-14.json": weekly_doc("2026-08-14", TICKERS)})
    before = tmp_path / "before.json"
    snapshot(w, before)

    edit(w, "2026-08-21.json",
         lambda doc: doc["series"]["XOM"].update({field: value}))

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "PANEL GUARD FAILED" in r.stdout
    assert "1 changed: " + said in r.stdout
    assert "2026-08-14.json" not in r.stdout.split("FAILED")[1]


@pytest.mark.parametrize("block, ticker", [
    ("rates", "US10Y"), ("vol", "VIX"), ("commodities", "WTI"),
    ("fx", "DXY")])
def test_a_changed_instrument_close_fails_the_run(panel, tmp_path, block,
                                                  ticker):
    """market_state derives from these directly, and the count never looked
    at them at all."""
    w, before = guarded(panel, tmp_path)
    edit(w, "2026-08-21.json",
         lambda doc: doc[block][ticker].update(close=9.99))

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "1 changed: %s.%s close" % (block, ticker) in r.stdout


def test_an_instrument_that_vanished_fails_the_run(panel, tmp_path):
    """What a rewrite of an old week does to its commodities: the contract
    has expired, the writer lists it in `missing`, and the close is gone."""
    w, before = guarded(panel, tmp_path)

    def expire(doc):
        doc["commodities"].pop("WTI")
        doc["provenance"]["commodities"].pop("WTI")
        doc["missing"].append({"ticker": "WTI", "reason": "CLX26.NYM: no bar"})
    edit(w, "2026-08-21.json", expire)

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "1 gone: commodities.WTI" in r.stdout


def test_a_name_swapped_for_another_fails_although_the_count_did_not_move(
        panel, tmp_path):
    """Five series before and five after. A whole-universe rewrite today
    would drop AVB, EA and EQR from every week, which the writer no longer
    fetches, and add the names that joined since."""
    w, before = guarded(panel, tmp_path)

    def swap(doc):
        doc["series"]["VMRK"] = doc["series"].pop("XOM")
    edit(w, "2026-08-21.json", swap)

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "1 gone: series.XOM" in r.stdout
    assert "1 grew" in r.stdout


@pytest.mark.parametrize("field, value", [
    ("fetched_at", "2026-10-06T04:08:06Z"),
    ("source", "yahoo-backfill"),
    ("session_note", "Friday holiday; bars from 2026-08-20"),
])
def test_a_restamped_file_fails_although_no_bar_changed(panel, tmp_path,
                                                        field, value):
    """The file-level stamp is the label of every entry with none of its
    own, and fetched_at is the date their closes are adjusted to. Restamped,
    every one of them says it was fetched when it was not."""
    w, before = guarded(panel, tmp_path)
    edit(w, "2026-08-21.json", lambda doc: doc.update({field: value}))

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "file stamp: %s " % field in r.stdout
    assert json.dumps(value) in r.stdout
    assert "0 bar(s) changed" in r.stdout


def test_a_stamp_that_was_removed_fails_too(panel, tmp_path):
    """A holiday week says which session its bars are from. Without the
    note, every one of them reads as the Friday's."""
    holiday = week("2026-07-03")
    holiday["session_note"] = "Friday holiday; bars from 2026-07-02"
    w, before = guarded(panel, tmp_path, {"2026-07-03.json": holiday})
    edit(w, "2026-07-03.json", lambda doc: doc.pop("session_note"))

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert ('file stamp: session_note "Friday holiday; bars from 2026-07-02" '
            "-> null") in r.stdout


def test_values_are_compared_as_json_values():
    """One number written two ways is one number. A NaN is the NaN it was,
    where == would call it changed on every run. And true is not 1."""
    same = panel_guard.same
    nan = float("nan")
    assert same(100, 100.0) and same(1000000, 1e6)
    assert same(nan, nan) and same({"close": nan}, {"close": nan})
    assert same(None, None) and same([1, {"a": 2}], [1, {"a": 2.0}])
    assert not same(True, 1) and not same(0, False) and not same(1, "1")
    assert not same(nan, 1.0) and not same(None, 0)
    assert not same({"close": 1}, {"close": 1, "volume": None})
    assert not same([1], [1, 2]) and not same({"a": 1}, {"b": 1})


def test_a_bar_that_is_not_a_number_is_held_like_any_other(panel, tmp_path):
    """The feed gate's to refuse, not this one's. What the guard owes such a
    file is not to call it changed when nothing touched it."""
    odd = weekly_doc("2026-08-21", TICKERS)
    odd["series"]["XOM"] = {"close": float("nan"), "volume": True}
    w = panel({"2026-08-21.json": odd})
    before = tmp_path / "before.json"
    snapshot(w, before)
    assert compare(w, before).returncode == 0

    edit(w, "2026-08-21.json",
         lambda doc: doc["series"]["XOM"].update(volume=1))
    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "1 changed: series.XOM volume true -> 1" in r.stdout


def test_a_bar_given_a_label_it_did_not_have_fails(panel, tmp_path):
    """The runner's mirror of the backfill script still fetches a named
    ticker over the bar a week holds and stamps it in provenance.series. For
    a name that has paid no dividend since, the fresh close is the committed
    one, and the stamp is the only thing that moved."""
    w, before = guarded(panel, tmp_path)
    edit(w, "2026-08-21.json", lambda doc: doc["provenance"].update(
        series={"XOM": dict(STAMP)}))

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "1 relabelled: series.XOM label none -> " in r.stdout
    assert "0 bar(s) changed, 1 label(s) changed" in r.stdout


def test_the_mirrors_merge_is_reported_as_both_a_bar_and_a_label(
        panel, tmp_path):
    w, before = guarded(panel, tmp_path)

    def overwrite(doc):
        doc["series"]["XOM"] = {"close": 99.4012, "volume": 1000000}
        doc["provenance"]["series"] = {"XOM": dict(STAMP)}
    edit(w, "2026-08-21.json", overwrite)

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "1 changed: series.XOM close 100.0 -> 99.4012" in r.stdout
    assert "1 relabelled: series.XOM" in r.stdout


@pytest.mark.parametrize("change, said", [
    (lambda p: p["commodities"]["WTI"].update(contract="CLZ26"),
     "commodities.WTI label"),
    (lambda p: p["rates"].pop("US2Y"), "rates.US2Y label"),
    (lambda p: p["rates"]["US2Y"].update(source="yahoo"), "rates.US2Y label"),
], ids=["another contract month", "label removed", "another publisher"])
def test_a_changed_instrument_label_fails(panel, tmp_path, change, said):
    """These two labels are load-bearing: one says the 2-year is Treasury's
    and not the future, the other which contract month a close is
    (DATA_FEED.md sec.1a, sec.1d)."""
    w, before = guarded(panel, tmp_path)
    edit(w, "2026-08-21.json", lambda doc: change(doc["provenance"]))

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "1 relabelled: " + said in r.stdout


# -- what still passes ---------------------------------------------------------

def test_a_merge_that_only_adds_passes(panel, tmp_path):
    """backfill_weekly.py --merge: a new name, its stamp, and `missing`
    brought up to date. Nothing the week held is touched."""
    w, before = guarded(panel, tmp_path)

    def merge(doc):
        doc["series"]["PLTR"] = {"close": 157.75, "volume": 45000000}
        doc["provenance"].setdefault("series", {})["PLTR"] = dict(STAMP)
        doc["missing"] = [{"ticker": "SPCX", "reason": "no bar for week"}]
    for name in ("2026-08-14.json", "2026-08-21.json"):
        edit(w, name, merge)

    r = compare(w, before)
    assert r.returncode == 0, r.stdout
    assert "2 grew, 0 added" in r.stdout


def test_a_new_week_passes_whatever_it_holds(panel, tmp_path):
    w, before = guarded(panel, tmp_path)
    (w / "2026-08-28.json").write_text(
        json.dumps(weekly_doc("2026-08-28", ["SPY"])), encoding="utf-8")

    r = compare(w, before)
    assert r.returncode == 0, r.stdout
    assert "0 grew, 1 added" in r.stdout


def test_a_file_that_was_only_reserialised_passes(panel, tmp_path):
    """Values are compared, not bytes. Another indent, another key order,
    CRLF, a volume written as a float: the same observation."""
    w, before = guarded(panel, tmp_path)
    path = w / "2026-08-21.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    for bar in doc["series"].values():
        bar["volume"] = float(bar["volume"])
        bar["close"] = int(bar["close"])
    text = json.dumps(doc, sort_keys=True, separators=(",", ": "), indent=1)
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

    r = compare(w, before)
    assert r.returncode == 0, r.stdout


# -- corrections ---------------------------------------------------------------

def correction(base: dict, name: str) -> dict:
    """What restate_instruments.py writes for rates.US10Y."""
    doc = copy.deepcopy(base)
    doc["rates"]["US10Y"] = {"close": 4.72, "volume": None}
    doc["provenance"]["rates"]["US10Y"] = {
        "source": "yahoo-backfill", "fetched_at": "2026-10-05T04:27:45Z"}
    doc["restated"] = [{"block": "rates", "ticker": "US10Y",
                        "was": {"close": 4.672, "volume": None}}]
    doc["corrects"] = name
    doc["reason"] = "the 10-year was Thursday's"
    return doc


def corrected(panel, tmp_path):
    base = week("2026-08-28")
    return guarded(panel, tmp_path, {
        "2026-08-28.json": base,
        "2026-08-28.corrected.json": correction(base, "2026-08-28.json")})


def test_a_rebuilt_correction_that_gained_the_new_names_passes(
        panel, tmp_path):
    """rebuild_corrections.py after a merge: the correction is a fresh copy
    of its base with the recorded edits re-applied."""
    w, before = corrected(panel, tmp_path)

    def merge(doc):
        doc["series"]["PLTR"] = {"close": 157.75, "volume": 45000000}
        doc["provenance"].setdefault("series", {})["PLTR"] = dict(STAMP)
    edit(w, "2026-08-28.json", merge)
    edit(w, "2026-08-28.corrected.json", merge)

    r = compare(w, before)
    assert r.returncode == 0, r.stdout
    assert "2 grew" in r.stdout


def test_a_correction_may_restate_an_instrument_it_puts_on_record(
        panel, tmp_path):
    """A second restatement added to a correction that exists, which
    restate_instruments.py leaves to be done by hand: the close, its label,
    and the `restated` entry. The entry is what lets the close change."""
    w, before = corrected(panel, tmp_path)

    def restate_vix(doc):
        doc["vol"]["VIX"] = {"close": 14.43, "volume": None}
        doc["provenance"]["vol"] = {"VIX": {
            "source": "yahoo-backfill", "fetched_at": "2026-10-07T01:00:00Z"}}
        doc["restated"].append({"block": "vol", "ticker": "VIX",
                                "was": {"close": 14.51, "volume": None}})
    edit(w, "2026-08-28.corrected.json", restate_vix)

    r = compare(w, before)
    assert r.returncode == 0, r.stdout
    assert ("weekly/2026-08-28.corrected.json restates vol.VIX, close "
            "14.51 -> 14.43") in r.stdout


def test_a_restated_close_changed_afterwards_fails(panel, tmp_path):
    """Nothing else holds this one. The correction still differs from its
    base and still has its `restated` entry and label, so the feed gate
    passes it; a rebuild copies the value from the correction itself."""
    w, before = corrected(panel, tmp_path)
    edit(w, "2026-08-28.corrected.json",
         lambda doc: doc["rates"]["US10Y"].update(close=4.70))

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "weekly/2026-08-28.corrected.json" in r.stdout
    assert "1 changed: rates.US10Y close 4.72 -> 4.7" in r.stdout


def test_an_unrecorded_change_to_a_correction_fails(panel, tmp_path):
    w, before = corrected(panel, tmp_path)
    edit(w, "2026-08-28.corrected.json",
         lambda doc: doc["fx"]["DXY"].update(close=99.70))

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "1 changed: fx.DXY close 99.16 -> 99.7" in r.stdout


def test_a_restated_entry_does_not_let_a_series_bar_change(panel, tmp_path):
    """Only an instrument is restated. A correction's series are its
    base's, and no tool restates an equity bar."""
    w, before = corrected(panel, tmp_path)

    def restate_xom(doc):
        doc["series"]["XOM"]["close"] = 101.25
        doc["restated"].append({"block": "series", "ticker": "XOM",
                                "was": {"close": 100.0, "volume": 1000000}})
    edit(w, "2026-08-28.corrected.json", restate_xom)

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "1 changed: series.XOM close 100.0 -> 101.25" in r.stdout


def test_a_restated_entry_frees_only_the_instrument_it_names(panel, tmp_path):
    w, before = corrected(panel, tmp_path)

    def restate_vix_and_move_the_dollar(doc):
        doc["vol"]["VIX"] = {"close": 14.43, "volume": None}
        doc["restated"].append({"block": "vol", "ticker": "VIX",
                                "was": {"close": 14.51, "volume": None}})
        doc["fx"]["DXY"]["close"] = 99.70
    edit(w, "2026-08-28.corrected.json", restate_vix_and_move_the_dollar)

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "restates vol.VIX" in r.stdout
    assert "1 changed: fx.DXY close 99.16 -> 99.7" in r.stdout
    assert "vol.VIX" not in r.stdout.split("FAILED")[1]


def test_a_restated_instrument_that_vanished_still_fails(panel, tmp_path):
    """A record of a restatement is not a way to drop the instrument."""
    w, before = corrected(panel, tmp_path)

    def record_and_drop(doc):
        doc["vol"].pop("VIX")
        doc["restated"].append({"block": "vol", "ticker": "VIX",
                                "was": {"close": 14.51, "volume": None}})
    edit(w, "2026-08-28.corrected.json", record_and_drop)

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "1 gone: vol.VIX" in r.stdout


def test_a_record_the_guard_cannot_read_excuses_nothing_and_breaks_nothing(
        panel, tmp_path):
    w, before = corrected(panel, tmp_path)

    def scribble(doc):
        doc["restated"] += [{"block": ["vol"], "ticker": {"VIX": 1}}, "VIX",
                            {"ticker": "VIX"}]
        doc["vol"]["VIX"]["close"] = 14.43
    edit(w, "2026-08-28.corrected.json", scribble)

    r = compare(w, before)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "1 changed: vol.VIX close 14.51 -> 14.43" in r.stdout
    assert "Traceback" not in r.stderr


def test_a_base_file_cannot_restate_itself(panel, tmp_path):
    """`restated` is a correction's record. In a base file it excuses
    nothing: the base is the observation."""
    w, before = corrected(panel, tmp_path)

    def edit_base(doc):
        doc["vol"]["VIX"]["close"] = 14.43
        doc["restated"] = [{"block": "vol", "ticker": "VIX",
                            "was": {"close": 14.51, "volume": None}}]
    edit(w, "2026-08-28.json", edit_base)

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "weekly/2026-08-28.json" in r.stdout
    assert "1 changed: vol.VIX close 14.51 -> 14.43" in r.stdout


# -- the declared rewrite ------------------------------------------------------

def refetch(doc):
    """A whole-universe --force rewrite of one week: every bar fetched
    again, on another adjustment anchor, under the run's own stamp."""
    for bar in doc["series"].values():
        bar["close"] = round(bar["close"] * 0.994, 4)
    doc["source"] = "yahoo-backfill"
    doc["fetched_at"] = "2026-10-06T04:08:06Z"


def test_a_rewrite_that_was_not_declared_fails(panel, tmp_path):
    w, before = guarded(panel, tmp_path)
    edit(w, "2026-08-21.json", refetch)

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "5 changed: " in r.stdout
    assert "5 bar(s) changed, 0 label(s) changed, 2 file stamp(s) changed" \
        in r.stdout


def test_a_declared_rewrite_may_change_the_weeks_it_names(panel, tmp_path):
    w, before = guarded(panel, tmp_path)
    edit(w, "2026-08-21.json", refetch)

    r = compare(w, before, "--rewrite", "2026-08-21", "2026-08-21")
    assert r.returncode == 0, r.stdout
    assert "DECLARED REWRITE of the weekly files 2026-08-21..2026-08-21" \
        in r.stdout
    assert ("1 file(s) on file in that range, 1 rewritten: 5 bar(s) changed, "
            "0 label(s) changed, 2 file stamp(s) changed") in r.stdout
    assert "unchanged outside the declared rewrite" in r.stdout


def test_a_declared_rewrite_does_not_cover_a_week_outside_its_range(
        panel, tmp_path):
    w, before = guarded(panel, tmp_path)
    edit(w, "2026-08-21.json", refetch)
    edit(w, "2026-08-14.json", refetch)

    r = compare(w, before, "--rewrite", "2026-08-21", "2026-08-21")
    assert r.returncode == 1, r.stdout
    failed = r.stdout.split("FAILED")[1]
    assert "weekly/2026-08-14.json" in failed
    assert "weekly/2026-08-21.json" not in failed


def test_a_declared_rewrite_may_not_remove_a_bar(panel, tmp_path):
    """The loss check is the one the guard began with, and a declaration
    does not buy a way round it. AVB, EA and EQR are no longer fetched, so a
    rewrite of the history would drop all three from every week."""
    w, before = guarded(panel, tmp_path)

    def refetch_and_drop(doc):
        refetch(doc)
        doc["series"].pop("JNJ")
    edit(w, "2026-08-21.json", refetch_and_drop)

    r = compare(w, before, "--rewrite", "2026-08-14", "2026-08-21")
    assert r.returncode == 1, r.stdout
    assert "DECLARED REWRITE" in r.stdout
    assert "1 gone: series.JNJ" in r.stdout
    assert "changed: " not in r.stdout.split("FAILED")[1].split("TOTAL")[0]


def test_a_declared_rewrite_covers_the_correction_of_a_week_it_names(
        panel, tmp_path):
    """A correction is rebuilt from its base, so it follows it."""
    w, before = corrected(panel, tmp_path)
    edit(w, "2026-08-28.json", refetch)
    edit(w, "2026-08-28.corrected.json", refetch)

    r = compare(w, before, "--rewrite", "2026-08-28", "2026-08-28")
    assert r.returncode == 0, r.stdout
    assert "2 file(s) on file in that range, 2 rewritten" in r.stdout


def test_a_declared_rewrite_may_not_remove_a_file(panel, tmp_path):
    w, before = guarded(panel, tmp_path)
    (w / "2026-08-21.json").unlink()

    r = compare(w, before, "--rewrite", "2026-08-14", "2026-08-21")
    assert r.returncode == 1, r.stdout
    assert "weekly/2026-08-21.json" in r.stdout and "FILE GONE" in r.stdout


def test_a_declared_rewrite_holds_a_correction_outside_its_range(
        panel, tmp_path):
    w, before = corrected(panel, tmp_path)
    edit(w, "2026-08-28.corrected.json", refetch)

    r = compare(w, before, "--rewrite", "2026-08-14", "2026-08-21")
    assert r.returncode == 1, r.stdout
    assert "weekly/2026-08-28.corrected.json" in r.stdout.split("FAILED")[1]
    assert "0 file(s) on file in that range" in r.stdout


def test_a_correction_inside_a_declared_rewrite_may_not_lose_an_entry(
        panel, tmp_path):
    """Rebuilt from a rewritten base, a correction follows it. It does not
    get to drop a bar on the way."""
    w, before = corrected(panel, tmp_path)

    def refetch_and_drop(doc):
        refetch(doc)
        doc["series"].pop("JNJ")
    edit(w, "2026-08-28.json", refetch)
    edit(w, "2026-08-28.corrected.json", refetch_and_drop)

    r = compare(w, before, "--rewrite", "2026-08-28", "2026-08-28")
    assert r.returncode == 1, r.stdout
    failed = r.stdout.split("FAILED")[1]
    assert "weekly/2026-08-28.corrected.json" in failed
    assert "1 gone: series.JNJ" in failed
    assert "weekly/2026-08-28.json\n" not in failed


def test_a_file_whose_name_is_no_date_is_guarded_and_in_no_rewrite(
        panel, tmp_path):
    """Every .json in the directory is the panel's as far as the guard
    knows. One that names no week cannot be inside a range of weeks."""
    w, before = guarded(panel, tmp_path, {
        "2026-08-21.json": week("2026-08-21"),
        "latest.json": week("2026-08-21")})
    edit(w, "latest.json", refetch)

    r = compare(w, before, "--rewrite", "0001-01-01", "9999-12-31")
    assert r.returncode == 1, r.stdout
    assert "weekly/latest.json" in r.stdout.split("FAILED")[1]
    assert "1 file(s) on file in that range" in r.stdout


def test_a_declared_rewrite_never_covers_a_daily_file(panel, tmp_path):
    """The backfill writes weekly files. A daily file dated inside the
    range is no part of what was declared."""
    w = panel({"2026-08-21.json": week("2026-08-21")})
    daily = w.parent / "daily"
    daily.mkdir()
    (daily / "2026-08-21.json").write_text(
        json.dumps(weekly_doc("2026-08-21", TICKERS)), encoding="utf-8")
    before = tmp_path / "before.json"
    snapshot(w, before)
    edit(daily, "2026-08-21.json", refetch)

    r = compare(w, before, "--rewrite", "2026-08-21", "2026-08-21")
    assert r.returncode == 1, r.stdout
    assert "daily/2026-08-21.json" in r.stdout.split("FAILED")[1]


@pytest.mark.parametrize("extra, said", [
    (("--rewrite", "2026-08-21", "2026-08-14"), "ends before it starts"),
    (("--rewrite", "2026-08-21", "20260828"), "YYYY-MM-DD"),
    (("--rewrite", "2026-02-30", "2026-08-28"), "YYYY-MM-DD"),
])
def test_a_rewrite_range_that_makes_no_sense_is_refused(panel, tmp_path,
                                                        extra, said):
    w, before = guarded(panel, tmp_path)
    r = compare(w, before, *extra)
    assert r.returncode == 2
    assert said in r.stderr


def test_rewrite_is_refused_anywhere_but_with_compare(panel, tmp_path):
    """A commit that changes what the panel held fails CI whatever it says
    about itself, so --against takes no declaration."""
    w, before = guarded(panel, tmp_path)
    for mode in (("--snapshot", str(tmp_path / "again.json")),
                 ("--against", "HEAD")):
        r = run(*mode, "--weekly-dir", str(w),
                "--rewrite", "2026-08-14", "2026-08-21")
        assert r.returncode == 2
        assert "--rewrite goes with --compare" in r.stderr


# -- the snapshot --------------------------------------------------------------

def test_a_count_only_snapshot_is_refused(panel, tmp_path):
    """What the guard wrote until 2026-10-06. Read as if it recorded bars,
    it would pass anything."""
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    before = tmp_path / "before.json"
    before.write_text(json.dumps({"2026-08-21.json": 5}), encoding="utf-8")

    r = compare(w, before)
    assert r.returncode != 0
    assert "is not a panel-guard/2 snapshot" in r.stderr


def test_a_snapshot_that_is_not_there_is_refused_not_a_traceback(
        panel, tmp_path):
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    r = compare(w, tmp_path / "never_taken.json")
    assert r.returncode != 0
    assert "cannot read the snapshot" in r.stderr
    assert "Traceback" not in r.stderr


def test_a_before_with_nothing_in_it_is_refused_not_passed(panel, tmp_path):
    """"0 file(s) before ... OK" is what a comparison against nothing says
    of any write at all, and it is what a mistake looks like: the wrong
    directory, or a snapshot that recorded none."""
    empty = tmp_path / "data" / "weekly"
    empty.mkdir(parents=True)
    taken = snapshot(empty, tmp_path / "before.json")
    assert taken.returncode != 0
    assert "nothing to record" in taken.stderr
    assert not (tmp_path / "before.json").exists()

    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    before = tmp_path / "hollow.json"
    before.write_text(json.dumps({"schema": "panel-guard/2", "files": {}}),
                      encoding="utf-8")
    r = compare(w, before)
    assert r.returncode != 0
    assert "records no panel file" in r.stderr
    assert "OK" not in r.stdout


def test_a_directory_where_a_file_should_be_is_refused_not_a_traceback(
        panel, tmp_path):
    w, before = guarded(panel, tmp_path)
    (w / "2026-08-21.json").unlink()
    (w / "2026-08-21.json").mkdir()

    r = compare(w, before)
    assert r.returncode != 0
    assert "cannot read weekly/2026-08-21.json" in r.stderr
    assert "Traceback" not in r.stderr


def test_the_daily_directory_beside_the_weekly_one_is_guarded(
        panel, tmp_path):
    """Same append-only contract, same hazard (DATA_FEED.md sec.4)."""
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    daily = w.parent / "daily"
    daily.mkdir()
    (daily / "2026-08-24.json").write_text(
        json.dumps(weekly_doc("2026-08-24", TICKERS)), encoding="utf-8")
    before = tmp_path / "before.json"
    assert "snapshot 2 file(s), 10 entries" in snapshot(w, before).stdout

    edit(daily, "2026-08-24.json",
         lambda doc: doc["series"]["XOM"].update(close=101.25))

    r = compare(w, before)
    assert r.returncode == 1, r.stdout
    assert "daily/2026-08-24.json" in r.stdout
    assert "weekly/2026-08-21.json" not in r.stdout.split("FAILED")[1]


def test_the_guard_reads_every_committed_panel_file(tmp_path):
    """Every shape the live panel has: bootstrap daily files with empty
    instrument blocks, merged weeks, both corrections. A guard that refused
    one of them would fail every run. Run as the workflows run it, as a
    process and from the repository root with no directory named."""
    weekly = ROOT / "data" / "weekly"
    on_file = len(list(weekly.glob("*.json"))) \
        + len(list((ROOT / "data" / "daily").glob("*.json")))
    before = tmp_path / "before.json"

    taken = cli("--snapshot", str(before), cwd=str(ROOT))
    assert taken.returncode == 0, taken.stderr
    assert "snapshot %d file(s)" % on_file in taken.stdout
    r = cli("--compare", str(before), cwd=str(ROOT))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "%d file(s) before, %d after" % (on_file, on_file) in r.stdout


# -- against a commit ----------------------------------------------------------

class Repo:
    """A throwaway git repository with a panel in it."""

    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True)
        self.git("init", "-q")
        # For the git commands a workflow step runs here by itself. On
        # Windows a temp root deep enough puts .git past 260 characters.
        self.git("config", "core.longpaths", "true")

    def git(self, *args) -> str:
        r = subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=t",
             "-c", "user.email=t@example.invalid", "-c", "core.autocrlf=false",
             "-c", "commit.gpgsign=false", "-c", "core.longpaths=true",
             *args],
            capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout.strip()

    def write(self, files: dict):
        """{path: document, text or None}; None removes the file."""
        for rel, content in files.items():
            path = self.root / rel
            if content is None:
                path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            if not isinstance(content, str):
                content = json.dumps(content, indent=2) + "\n"
            path.write_text(content, encoding="utf-8", newline="\n")

    def commit(self, files: dict, message: str = "c") -> str:
        self.write(files)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    @property
    def weekly(self) -> Path:
        return self.root / "data" / "weekly"


W14, W21, D24 = ("data/weekly/2026-08-14.json", "data/weekly/2026-08-21.json",
                 "data/daily/2026-08-24.json")


def changed(doc: dict, ticker: str = "XOM", close: float = 101.25) -> dict:
    out = copy.deepcopy(doc)
    out["series"][ticker]["close"] = close
    return out


@pytest.fixture
def repo(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git not available")
    r = Repo(tmp_path / "repo")
    r.first = r.commit({W14: week("2026-08-14"), W21: week("2026-08-21"),
                        D24: weekly_doc("2026-08-24", TICKERS)}, "the panel")
    return r


def against(repo: Repo, commit: str, cwd=None):
    args = ("--against", commit, "--weekly-dir", str(repo.weekly))
    return cli(*args, cwd=cwd) if cwd else run(*args)


def test_against_a_commit_passes_new_files_and_new_names(repo):
    grown = week("2026-08-21")
    grown["series"]["PLTR"] = {"close": 157.75, "volume": 45000000}
    grown["provenance"]["series"] = {"PLTR": dict(STAMP)}
    repo.commit({W21: grown,
                 "data/weekly/2026-08-28.json": week("2026-08-28"),
                 "data/daily/2026-08-25.json":
                     weekly_doc("2026-08-25", TICKERS)})

    r = against(repo, "HEAD^")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "3 file(s) before, 5 after; 1 grew, 2 added" in r.stdout


@pytest.mark.parametrize("path, key", [
    (W21, "weekly/2026-08-21.json"), (D24, "daily/2026-08-24.json")])
def test_against_a_commit_fails_a_changed_bar(repo, path, key):
    """What CI's own copy of the count passed: a commit that moved a close
    in a weekly file and in a daily one printed "panel intact"."""
    doc = json.loads((repo.root / path).read_text(encoding="utf-8"))
    repo.commit({path: changed(doc)})

    r = against(repo, "HEAD^")
    assert r.returncode == 1, r.stdout + r.stderr
    assert key in r.stdout
    assert "1 changed: series.XOM close 100.0 -> 101.25" in r.stdout
    assert "Compared: the panel at HEAD^, with the files on disk." in r.stdout


@pytest.mark.parametrize("path, key", [
    (W21, "weekly/2026-08-21.json"), (D24, "daily/2026-08-24.json")])
def test_against_a_commit_fails_a_deleted_file(repo, path, key):
    """CI's copy looped over the files that exist now, so a commit that
    deleted one printed "panel intact" as well."""
    repo.commit({path: None})

    r = against(repo, "HEAD^")
    assert r.returncode == 1, r.stdout + r.stderr
    assert key in r.stdout and "FILE GONE" in r.stdout


def test_against_a_commit_that_deleted_the_daily_directory_fails(repo):
    """A fresh checkout of such a commit has no data/daily at all, and the
    directory beside the weekly one is guarded only "when it exists"."""
    repo.commit({D24: None})
    (repo.root / "data" / "daily").rmdir()

    r = against(repo, "HEAD^")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "daily/2026-08-24.json" in r.stdout


def test_the_tip_a_push_replaced_sees_the_first_of_three_commits(repo):
    """2026-10-03: the runner pushed the weekly file, market_state.json and
    universe.json as three commits. CI ran on the third and compared it with
    the second. Nothing compared the weekly file with anything."""
    repo.commit({W21: changed(week("2026-08-21"))}, "the weekly file")
    repo.commit({"data/market_state.json": {"as_of": "2026-08-21"}})
    repo.commit({"data/universe.json": {"as_of": "2026-08-22"}})

    assert against(repo, "HEAD^").returncode == 0
    r = against(repo, repo.first)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "1 changed: series.XOM close 100.0 -> 101.25" in r.stdout


def test_against_reads_the_files_on_disk_not_the_last_commit(repo):
    """The daily job runs it before it commits: a new session is there and
    untracked, and passes; a file the commit holds, rewritten on disk,
    fails."""
    repo.write({"data/daily/2026-08-25.json":
                weekly_doc("2026-08-25", TICKERS)})
    r = against(repo, "HEAD")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 grew, 1 added" in r.stdout

    repo.write({D24: changed(weekly_doc("2026-08-24", TICKERS))})
    r = against(repo, "HEAD")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "daily/2026-08-24.json" in r.stdout


def test_against_does_not_depend_on_where_it_is_run_from(repo, tmp_path):
    repo.commit({W21: changed(week("2026-08-21"))})
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    for cwd in (elsewhere, repo.root, repo.weekly):
        r = against(repo, "HEAD^", cwd=str(cwd))
        assert r.returncode == 1, r.stdout + r.stderr
        assert "weekly/2026-08-21.json" in r.stdout


def test_against_a_commit_that_does_not_exist_is_refused(repo):
    """A check that cannot find its "before" has not passed."""
    for commit in ("HEAD^", "0123456789abcdef0123456789abcdef01234567",
                   "no-such-branch"):
        r = against(repo, commit)
        assert r.returncode != 0
        assert "is not a commit" in r.stderr
        assert "OK" not in r.stdout


def test_against_a_copy_the_commit_does_not_track_is_refused(repo):
    """A rehearsal copy inside the repository, compared with a commit that
    never held it: nothing before, so nothing was compared. It used to
    print "0 file(s) before, 2 after" and OK."""
    copy_of = repo.root / "scratch" / "data" / "weekly"
    shutil.copytree(repo.weekly, copy_of)
    edit(copy_of, "2026-08-21.json",
         lambda doc: doc["series"]["XOM"].update(close=101.25))

    r = run("--against", "HEAD", "--weekly-dir", str(copy_of))
    assert r.returncode != 0
    assert "HEAD holds no panel file under" in r.stderr
    assert "OK" not in r.stdout


def test_against_asks_the_repository_the_directory_is_in(repo, tmp_path,
                                                         monkeypatch):
    """git hands a hook, and a command run by `rebase --exec`, the
    repository it is working on as GIT_DIR, with no work tree. The guard
    took that for the place to look, found no panel at the commit, and
    printed OK over three changed bars."""
    repo.commit({W21: changed(week("2026-08-21"))})
    other = Repo(tmp_path / "other")
    other.commit({"keep.txt": "not a panel\n"})

    monkeypatch.setenv("GIT_DIR", str(other.root / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(other.root / ".git" / "index"))
    monkeypatch.setenv("GIT_PREFIX", "")
    for call in (against, lambda r, c: against(r, c, cwd=str(tmp_path))):
        r = call(repo, "HEAD^")
        assert r.returncode == 1, r.stdout + r.stderr
        assert "3 file(s) before, 3 after" in r.stdout
        assert "1 changed: series.XOM close 100.0 -> 101.25" in r.stdout


def test_the_suite_does_not_inherit_a_repository_from_git(tmp_path):
    """The other half of the same hazard. These tests run `git init`,
    `git add -A` and `git commit` in tmp directories; with GIT_DIR inherited
    they did it to the repository being rebased. conftest drops what git
    calls repository-local before any test can spawn anything."""
    probe = ("import os, conftest; "
             "print(sorted(n for n in os.environ if n.startswith('GIT_')))")
    env = dict(os.environ, GIT_DIR=str(tmp_path / "x.git"),
               GIT_WORK_TREE=str(tmp_path), GIT_INDEX_FILE="x", GIT_PREFIX="")
    env = {name: value for name, value in env.items()
           if not name.startswith("GIT_") or name in (
               "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX")}
    r = subprocess.run([sys.executable, "-c", probe], capture_output=True,
                       text=True, env=env, cwd=str(ROOT / "tests"))
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "[]"


def test_against_is_refused_outside_a_repository(panel, tmp_path):
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(tmp_path.parent))
    r = cli("--against", "HEAD", "--weekly-dir", str(w), env=env)
    assert r.returncode != 0
    assert "not inside a git repository" in r.stderr


# -- the workflows that call it ------------------------------------------------

def workflow(name: str) -> dict:
    return yaml.safe_load((ROOT / ".github" / "workflows" / name)
                          .read_text(encoding="utf-8"))


def step(steps: list, name: str) -> dict:
    found = [s for s in steps if str(s.get("name", "")).startswith(name)]
    assert len(found) == 1, "expected one step named %r" % name
    return found[0]


def bash():
    """The shell the workflow steps are written for. On Windows that is Git
    for Windows' own; `bash` on PATH there can be the WSL launcher."""
    if os.name != "nt":
        return shutil.which("bash")
    git = shutil.which("git")
    for up in (1, 2):       # <Git>/cmd/git.exe, <Git>/mingw64/bin/git.exe
        if git and len(Path(git).resolve().parents) > up:
            found = Path(git).resolve().parents[up] / "bin" / "bash.exe"
            if found.is_file():
                return str(found)
    return None


REAL_PYTHON = "python() { '%s' \"$@\"; }\n" % sys.executable.replace("\\", "/")
ECHO_PYTHON = "python() { echo \"RUN python $*\"; }\n"


def run_step(script: str, tmp_path: Path, cwd: Path,
             python: str = REAL_PYTHON, **env):
    """One workflow step's script, under the flags Actions runs it with.
    `python` is a shell function, so no PATH has to be trusted to find it.
    The script is written under tmp_path and nowhere else."""
    shell = bash()
    if shell is None:
        pytest.skip("no bash to run a workflow step with")
    path = tmp_path / "step.sh"
    path.write_text(python + script, encoding="utf-8", newline="\n")
    return subprocess.run(
        [shell, "--noprofile", "--norc", "-eo", "pipefail", path.as_posix()],
        cwd=str(cwd), env=dict(os.environ, **env), capture_output=True,
        text=True)


def render(script: str, **inputs) -> str:
    """Fill in ${{ inputs.<name> }}, and ${{ inputs.<name> || '<text>' }},
    as Actions would."""
    def value(match):
        given = inputs[match.group(1)]
        if match.group(2) is not None and not given:
            return match.group(2)
        return str(given).lower() if isinstance(given, bool) else str(given)
    rendered = re.sub(
        r"\$\{\{\s*inputs\.(\w+)\s*(?:\|\|\s*'([^']*)'\s*)?\}\}", value,
        script)
    assert "${{" not in rendered, "an expression this cannot fill in"
    return rendered


def no_step_is_let_off(steps: list) -> bool:
    """No step may fail without failing its job."""
    return not any("continue-on-error" in s for s in steps)


# CI ---------------------------------------------------------------------------

def test_ci_runs_the_guard_against_the_tip_a_push_replaced():
    steps = workflow("ci.yml")["jobs"]["test"]["steps"]
    panel_step = step(steps, "Panel is intact")
    assert 'python scripts/panel_guard.py --against "$base"' \
        in panel_step["run"]
    assert "github.event.before" in panel_step["env"]["PUSH_BEFORE"]
    assert "--rewrite" not in panel_step["run"], (
        "CI takes no declaration: a commit that changes what the panel held "
        "fails whatever it says about itself")
    checkout = [s for s in steps
                if str(s.get("uses", "")).startswith("actions/checkout")][0]
    depth = checkout["with"]["fetch-depth"]
    assert depth == 0 or depth >= 2, (
        "HEAD^ is what a pull request is compared with; a depth-1 checkout "
        "has none")


def test_ci_compares_the_panel_even_when_the_tests_before_it_failed():
    """A push is compared once, by its own run, and the next push starts
    from the new tip. On 2026-09-25 the push of that week's file failed at
    Tests; the feed gate and the panel step were skipped, and nothing came
    back for it. The step is last and must not wait on the ones before."""
    steps = workflow("ci.yml")["jobs"]["test"]["steps"]
    panel_step = step(steps, "Panel is intact")
    assert panel_step["if"] == "${{ !cancelled() }}"
    assert steps[-1] is panel_step
    assert no_step_is_let_off(steps)


HISTORY = "data/us2y_treasury.json"


def pushed(tmp_path, commits: list, depth: int = 2,
           first_message: str = "the panel"):
    """An origin holding a panel and then `commits`, and the checkout CI
    would have of its tip. Returns (clone directory, sha of the panel)."""
    if shutil.which("git") is None:
        pytest.skip("git not available")
    if os.name == "nt" and len(str(tmp_path / "origin" / ".git")) > 215:
        # git on Windows will not have a GIT_DIR longer than 220 characters
        # ("'$GIT_DIR' too big"), whatever core.longpaths says, and a clone
        # sets one. pytest's own temp root is nowhere near it.
        pytest.skip("temp root too deep for git on Windows")
    origin = Repo(tmp_path / "origin")
    # GitHub serves a commit asked for by its id. A bare local repository
    # does not unless told to.
    origin.git("config", "uploadpack.allowAnySHA1InWant", "true")
    first = origin.commit({
        W14: week("2026-08-14"), W21: week("2026-08-21"),
        D24: weekly_doc("2026-08-24", TICKERS),
        HISTORY: {"series": {"2026-08-14": {"close": 4.17}}},
        "scripts/panel_guard.py": GUARD.read_text(encoding="utf-8"),
    }, first_message)
    for n, files in enumerate(commits):
        origin.commit(files, "commit %d of the push" % (n + 1))
    clone = tmp_path / "clone"
    for command in (
            ["clone", "-q", "--depth", str(depth), origin.root.as_uri(),
             str(clone)],
            ["-C", str(clone), "config", "core.longpaths", "true"]):
        made = subprocess.run(["git", "-c", "core.longpaths=true"] + command,
                              capture_output=True, text=True)
        assert made.returncode == 0, made.stderr
    return clone, first


def ci_step(clone: Path, before: str = ""):
    script = step(workflow("ci.yml")["jobs"]["test"]["steps"],
                  "Panel is intact")["run"]
    return run_step(script, clone.parent, clone, PUSH_BEFORE=before)


UNRELATED = [{"data/market_state.json": {"as_of": "2026-08-21"}},
             {"data/universe.json": {"as_of": "2026-08-22"}}]


def test_the_ci_step_fails_a_push_whose_first_commit_rewrote_a_bar(tmp_path):
    clone, first = pushed(
        tmp_path, [{W21: changed(week("2026-08-21"))}] + UNRELATED)

    r = ci_step(clone, before=first)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "Comparing with " + first[:7] in r.stdout
    assert "PANEL GUARD FAILED" in r.stdout
    assert "1 changed: series.XOM close 100.0 -> 101.25" in r.stdout
    # The other check in the step ran all the same, and passed.
    assert "us2y history intact: 1 week(s) unchanged, 0 added" in r.stdout

    # Without the push's previous tip the step has only the last commit's
    # parent, which is all it ever had: this is what ran on 2026-10-03.
    r = ci_step(clone)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PANEL GUARD FAILED" not in r.stdout


def test_the_ci_step_passes_a_push_that_only_adds(tmp_path):
    clone, first = pushed(tmp_path, [
        {"data/weekly/2026-08-28.json": week("2026-08-28")}] + UNRELATED)

    r = ci_step(clone, before=first)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "3 file(s) before, 4 after; 0 grew, 1 added" in r.stdout
    assert "panel_guard: OK" in r.stdout


def test_the_ci_step_holds_the_history_files_to_the_same_before(tmp_path):
    """The Treasury and settlement histories are checked in the same step,
    and had the same blind spot. A failure there fails the step although
    the panel passed."""
    clone, first = pushed(tmp_path, [
        {HISTORY: {"series": {"2026-08-14": {"close": 4.76}}}}] + UNRELATED)

    r = ci_step(clone, before=first)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "panel_guard: OK" in r.stdout
    assert "US2Y HISTORY REGRESSION" in r.stdout

    assert ci_step(clone).returncode == 0


def test_the_ci_step_falls_back_to_the_last_commits_parent(tmp_path):
    clone, _first = pushed(tmp_path, UNRELATED)

    # A previous tip the remote will not serve: said out loud, because the
    # push's earlier commits are then not looked at.
    r = ci_step(clone, before="0123456789abcdef0123456789abcdef01234567")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "::warning title=Panel check::Could not fetch" in r.stdout
    assert "panel_guard: OK" in r.stdout

    # A branch that did not exist before the push has none to fetch.
    r = ci_step(clone, before="0" * 40)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "::warning" not in r.stdout
    assert "panel_guard: OK" in r.stdout


def test_the_ci_step_fails_a_checkout_too_shallow_to_have_a_parent(tmp_path):
    """It used to print "No parent commit; skipping." and exit 0, so a
    fetch-depth of 1 would have turned the check off for good."""
    clone, _first = pushed(tmp_path, UNRELATED, depth=1)

    r = ci_step(clone)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "::error title=Panel check::HEAD has a parent" in r.stdout
    assert "panel_guard: OK" not in r.stdout


def test_the_ci_step_has_nothing_to_compare_a_first_commit_with(tmp_path):
    """And it is the commit's header that says so. A message may have a
    line that begins "parent " as well; that is not a parent."""
    clone, _first = pushed(tmp_path, [], first_message=(
        "the panel\n\nparent of every commit after it"))

    r = ci_step(clone)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "No parent commit; nothing to compare with." in r.stdout


# the backfill -----------------------------------------------------------------

def backfill_step(tmp_path: Path, name: str, preamble: str = "",
                  GITHUB_REF_NAME: str = "", **inputs):
    given = dict(tickers="", start="2026-08-14", end="2026-08-21",
                 rewrite=False, dry_run=False)
    given.update(inputs)
    script = step(workflow("backfill.yml")["jobs"]["backfill"]["steps"],
                  name)["run"]
    # An empty directory: a step that got past the stub would find no
    # script to run and no data to write.
    empty = tmp_path / "nowhere"
    empty.mkdir(exist_ok=True)
    return run_step(render(script, **given), tmp_path, empty,
                    python=ECHO_PYTHON + preamble,
                    GITHUB_REF_NAME=GITHUB_REF_NAME)


def test_the_backfill_declares_a_rewrite_with_an_input_that_is_off():
    inputs = workflow("backfill.yml")[True]["workflow_dispatch"]["inputs"]
    assert inputs["rewrite"]["type"] == "boolean"
    assert inputs["rewrite"]["default"] is False
    assert inputs["dry_run"]["default"] is True


BACKFILL = ("RUN python scripts/backfill_weekly.py --out data "
            "--start 2026-08-14 --end 2026-08-21")


def test_a_blank_ticker_list_no_longer_means_force(tmp_path):
    """Until 2026-10-06 it did, so the one way to write a week that had no
    file was also the way to rewrite all the others."""
    r = backfill_step(tmp_path, "Backfill")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == BACKFILL


def test_force_is_passed_only_when_a_rewrite_is_declared(tmp_path):
    r = backfill_step(tmp_path, "Backfill", rewrite=True)
    assert r.returncode == 0, r.stderr
    assert "REWRITE DECLARED" in r.stdout
    assert r.stdout.strip().endswith(BACKFILL + " --force")

    r = backfill_step(tmp_path, "Backfill", rewrite=True, dry_run=True)
    assert r.stdout.strip().endswith(BACKFILL + " --force --dry-run")


def test_named_tickers_are_merged_and_never_forced(tmp_path):
    r = backfill_step(tmp_path, "Backfill", tickers="PLTR,VST")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == BACKFILL + " --only PLTR,VST --merge"


def test_named_tickers_with_a_rewrite_are_refused_before_anything_runs(
        tmp_path):
    validate = "Validate inputs"
    r = backfill_step(tmp_path, validate, tickers="PLTR,VST", rewrite=True)
    assert r.returncode == 1
    assert "rewrite is for the whole universe" in r.stdout

    assert backfill_step(tmp_path, validate, tickers="PLTR").returncode == 0
    assert backfill_step(tmp_path, validate, rewrite=True).returncode == 0


def test_the_backfills_guard_is_told_of_a_rewrite_and_of_nothing_else(
        tmp_path):
    compare_line = "RUN python scripts/panel_guard.py --compare " \
                   "/tmp/panel_before.json"
    guard = "Guard what the panel held"
    r = backfill_step(tmp_path, guard)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == compare_line

    r = backfill_step(tmp_path, guard, tickers="PLTR,VST")
    assert r.stdout.strip() == compare_line

    r = backfill_step(tmp_path, guard, rewrite=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == compare_line \
        + " --rewrite 2026-08-14 2026-08-21"


def test_the_backfill_guards_between_its_write_and_its_commit():
    steps = workflow("backfill.yml")["jobs"]["backfill"]["steps"]
    names = [str(s.get("name", "")) for s in steps]
    order = [names.index(n) for n in (
        "Snapshot the panel before", "Backfill", "Rebuild corrections",
        "Guard what the panel held", "Commit")]
    assert order == sorted(order), names

    # A failed guard stops the commit only while the commit waits on it:
    # no step is let off, and neither condition says "whatever happened".
    assert no_step_is_let_off(steps)
    for name in ("Guard what the panel held", "Commit"):
        assert step(steps, name)["if"] == "inputs.dry_run == false", name


GIT_STUB = ('git() { if [ "$1" = diff ]; then return 1; fi; '
            'echo "RUN git $*"; }\n')


def test_a_rewrite_says_so_in_its_commit(tmp_path):
    """No CI run looks at the backfill's commit, so the subject is the one
    place a rewrite stays visible."""
    def commit(**inputs):
        r = backfill_step(tmp_path, "Commit", preamble=GIT_STUB,
                          GITHUB_REF_NAME="main", **inputs)
        assert r.returncode == 0, r.stdout + r.stderr
        return r.stdout

    said = commit(rewrite=True)
    assert ("RUN git commit -m REWRITE weekly panel 2026-08-14 to 2026-08-21 "
            "(declared, whole universe) -m Weeks already on file were "
            "written again whole (--force)") in said
    assert "RUN git push" in said

    said = commit()
    assert ("RUN git commit -m Backfill weekly panel 2026-08-14 to "
            "2026-08-21 -m Tickers: entire universe, weeks with no file "
            "only.") in said
    assert "REWRITE" not in said

    assert "-m Tickers: PLTR,VST." in commit(tickers="PLTR,VST")


# the daily job ----------------------------------------------------------------

def test_the_daily_job_guards_the_panel_before_it_commits():
    """CI never sees this job's commit, so the job compares its own write
    with the commit it started from."""
    steps = workflow("daily-observe.yml")["jobs"]["observe"]["steps"]
    guard = step(steps, "Guard what the panel held")
    assert guard["run"].strip() == "python scripts/panel_guard.py --against HEAD"

    commit = step(steps, "Commit the session")
    observe = step(steps, "Observe the session")
    assert steps.index(observe) < steps.index(guard) < steps.index(commit)
    # Under the condition the commit runs under: a refused run wrote
    # nothing, and a dry run writes nothing. Neither says "whatever
    # happened before", so a failed guard is a commit that does not run.
    assert guard["if"] == commit["if"] == (
        "steps.observe.outputs.refused != 'true' && !inputs.dry_run")
    assert no_step_is_let_off(steps)
