"""panel_guard is the gate that would have stopped the 2026-08-26 incident.

A targeted backfill replaced every weekly file with just its 44 --only
tickers -- 287 series became 44 across 107 files -- and the workflow reported
success, because the counts were printed with nothing to compare them to.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import SCRIPTS, weekly_doc

GUARD = SCRIPTS / "panel_guard.py"
TICKERS = ["SPY", "AAPL", "MSFT", "XOM", "JNJ"]


def run(*args):
    return subprocess.run([sys.executable, str(GUARD), *args],
                          capture_output=True, text=True)


def snapshot(weekly: Path, out: Path):
    return run("--snapshot", str(out), "--weekly-dir", str(weekly))


def compare(weekly: Path, before: Path):
    return run("--compare", str(before), "--weekly-dir", str(weekly))


def rewrite(weekly: Path, name: str, tickers):
    doc = json.loads((weekly / name).read_text(encoding="utf-8"))
    doc["series"] = {t: v for t, v in doc["series"].items() if t in tickers}
    (weekly / name).write_text(json.dumps(doc), encoding="utf-8")


def test_unchanged_panel_passes(panel, tmp_path):
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    before = tmp_path / "before.json"
    assert snapshot(w, before).returncode == 0
    r = compare(w, before)
    assert r.returncode == 0
    assert "no file lost series" in r.stdout


def test_growth_passes_because_that_is_what_a_backfill_is_for(panel, tmp_path):
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    before = tmp_path / "before.json"
    snapshot(w, before)

    doc = json.loads((w / "2026-08-21.json").read_text(encoding="utf-8"))
    doc["series"]["PLTR"] = {"close": 1.0, "volume": 1}
    (w / "2026-08-21.json").write_text(json.dumps(doc), encoding="utf-8")

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
    assert "2026-08-21.json" in r.stdout
    assert "-4" in r.stdout          # 5 -> 1
    assert "2026-08-14.json" not in r.stdout.split("FAILED")[1]


def test_a_vanished_file_fails_too(panel, tmp_path):
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    before = tmp_path / "before.json"
    snapshot(w, before)
    (w / "2026-08-21.json").unlink()

    r = compare(w, before)
    assert r.returncode == 1
    assert "FILE GONE" in r.stdout


def test_a_file_shape_it_does_not_recognise_is_refused(panel, tmp_path):
    w = panel({"2026-08-21.json": weekly_doc("2026-08-21", TICKERS)})
    before = tmp_path / "before.json"
    snapshot(w, before)
    (w / "2026-08-21.json").write_text(json.dumps({"as_of": "2026-08-21"}),
                                       encoding="utf-8")

    r = compare(w, before)
    assert r.returncode != 0
    assert "no 'series' object" in (r.stdout + r.stderr)


def test_snapshot_counts_every_file_not_just_one_month(panel, tmp_path):
    """The step this replaced globbed data/weekly/2026-08-*.json, so 103 of
    the 107 files it was meant to protect were never looked at."""
    w = panel({
        "2024-09-06.json": weekly_doc("2024-09-06", TICKERS),
        "2026-08-21.json": weekly_doc("2026-08-21", TICKERS),
    })
    before = tmp_path / "before.json"
    snapshot(w, before)
    counts = json.loads(before.read_text(encoding="utf-8"))
    assert set(counts) == {"2024-09-06.json", "2026-08-21.json"}

    rewrite(w, "2024-09-06.json", {"AAPL"})
    assert compare(w, before).returncode == 1
