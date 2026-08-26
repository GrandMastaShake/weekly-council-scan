"""Merge semantics: adding tickers to a week without disturbing it.

Adding a ticker to a past week and rewriting that week are different
operations. The script only had the second one, so `--only <44> --force`
deleted 243 names from 107 files and the job reported success.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from conftest import SCRIPTS, weekly_doc

import backfill_weekly as bf  # noqa: E402  (conftest stubs the provider)

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
