"""The correction trap, and the feed gate that validates per-series anchors.

A correction is a full copy of its base, so it goes stale the moment the base
changes: backfilled names become silently invisible for that week, forever,
with no error anywhere.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import SCRIPTS, weekly_doc

REBUILD = SCRIPTS / "rebuild_corrections.py"
TRUTH = SCRIPTS / "truth_check.py"
TICKERS = ["SPY", "AAPL", "AVB", "JNJ"]
ANCHOR = {"source": "yahoo-backfill", "fetched_at": "2026-08-26T04:08:06Z"}


def base_and_correction(tmp_path, base_extra=None, prov=None):
    """A week where AVB printed a close behind zero volume, plus its correction."""
    d = tmp_path / "data" / "weekly"
    d.mkdir(parents=True, exist_ok=True)

    base = weekly_doc("2026-08-21", TICKERS)
    base["series"]["AVB"] = {"close": 65.9005, "volume": 0}

    # The correction is written FIRST, from the base as it stood before any
    # backfill. That is what makes it stale: it is a full copy, and readers
    # prefer it, so names added to the base afterwards are invisible until it
    # is rebuilt. Building it after the extras would test nothing.
    corrected = json.loads(json.dumps(base))
    corrected["series"].pop("AVB")
    corrected["missing"] = [{"ticker": "AVB",
                             "reason": "zero-volume bar, close 65.9005"}]
    corrected["corrects"] = "2026-08-21.json"
    corrected["reason"] = "AVB printed behind zero volume"
    corrected.pop("provenance", None)
    (d / "2026-08-21.corrected.json").write_text(
        json.dumps(corrected, indent=2), encoding="utf-8")

    # now the backfill lands in the base, behind the correction's back
    for ticker in (base_extra or []):
        base["series"][ticker] = {"close": 10.0, "volume": 5}
    if prov:
        base["provenance"] = {"series": dict(prov)}
    (d / "2026-08-21.json").write_text(json.dumps(base, indent=2), encoding="utf-8")
    return d


def rebuild(weekly: Path):
    return subprocess.run([sys.executable, str(REBUILD), "--dir", str(weekly)],
                          capture_output=True, text=True)


def feed(repo: Path):
    return subprocess.run([sys.executable, str(TRUTH), "--repo", str(repo), "--feed"],
                          capture_output=True, text=True)


def test_rebuild_carries_backfilled_names_into_the_correction(tmp_path):
    """The trap: without this the new names are invisible for that week."""
    weekly = base_and_correction(tmp_path, base_extra=["PLTR", "VST"])
    before = json.loads((weekly / "2026-08-21.corrected.json").read_text(encoding="utf-8"))
    assert "PLTR" not in before["series"]

    assert rebuild(weekly).returncode == 0

    after = json.loads((weekly / "2026-08-21.corrected.json").read_text(encoding="utf-8"))
    assert {"PLTR", "VST"} <= set(after["series"])
    assert "AVB" not in after["series"], "the zero-volume drop must survive"
    assert after["corrects"] == "2026-08-21.json"


def test_rebuild_drops_the_anchor_of_a_series_it_removes(tmp_path):
    """An anchor for a series that is not there describes nothing, and the
    feed gate refuses it."""
    weekly = base_and_correction(tmp_path, prov={"AVB": ANCHOR, "PLTR": ANCHOR},
                                 base_extra=["PLTR"])
    assert rebuild(weekly).returncode == 0

    after = json.loads((weekly / "2026-08-21.corrected.json").read_text(encoding="utf-8"))
    prov = after.get("provenance", {}).get("series", {})
    assert "AVB" not in prov
    assert "PLTR" in prov


def test_rebuild_removes_an_emptied_provenance_block(tmp_path):
    weekly = base_and_correction(tmp_path, prov={"AVB": ANCHOR})
    assert rebuild(weekly).returncode == 0
    after = json.loads((weekly / "2026-08-21.corrected.json").read_text(encoding="utf-8"))
    assert "provenance" not in after


def test_rebuild_aborts_rather_than_guessing_when_the_provider_restated(tmp_path):
    weekly = base_and_correction(tmp_path)
    base_path = weekly / "2026-08-21.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    base["series"]["AVB"] = {"close": 184.06, "volume": 2_000_000}
    base_path.write_text(json.dumps(base), encoding="utf-8")

    r = rebuild(weekly)
    assert "ABORT" in r.stdout
    after = json.loads((weekly / "2026-08-21.corrected.json").read_text(encoding="utf-8"))
    assert "AVB" not in after["series"], "the correction was left alone"


def test_rebuild_no_longer_ignores_the_directory_it_is_given(tmp_path):
    """It took no arguments and read the live panel unconditionally, so a
    command naming another directory was accepted in silence."""
    r = subprocess.run([sys.executable, str(REBUILD), "--bogus", "x"],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "unrecognized arguments" in r.stderr


# --- the feed gate on per-series anchors
def test_feed_gate_accepts_a_merged_week(tmp_path):
    base_and_correction(tmp_path, base_extra=["PLTR"], prov={"PLTR": ANCHOR})
    r = feed(tmp_path)
    assert r.returncode == 0
    assert "0 fail" in r.stdout


def test_feed_gate_refuses_an_anchor_for_a_series_that_is_not_there(tmp_path):
    base_and_correction(tmp_path, prov={"GHOST": ANCHOR})
    r = feed(tmp_path)
    assert r.returncode == 1
    assert "provenance names 'GHOST'" in r.stdout


def test_feed_gate_refuses_a_bad_timestamp(tmp_path):
    base_and_correction(tmp_path, base_extra=["PLTR"],
                        prov={"PLTR": {"source": "yahoo-backfill",
                                       "fetched_at": "2026-08-26"}})
    r = feed(tmp_path)
    assert r.returncode == 1
    assert "not a UTC" in r.stdout


def test_feed_gate_refuses_a_missing_source(tmp_path):
    base_and_correction(tmp_path, base_extra=["PLTR"],
                        prov={"PLTR": {"fetched_at": "2026-08-26T04:08:06Z"}})
    r = feed(tmp_path)
    assert r.returncode == 1
    assert "non-empty 'source'" in r.stdout


def test_feed_gate_refuses_an_unknown_provenance_key(tmp_path):
    weekly = base_and_correction(tmp_path, base_extra=["PLTR"], prov={"PLTR": ANCHOR})
    p = weekly / "2026-08-21.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["provenance"]["default"] = {"source": "yahoo"}
    p.write_text(json.dumps(doc), encoding="utf-8")

    r = feed(tmp_path)
    assert r.returncode == 1
    assert "unknown key" in r.stdout


# --- the diverged mirror
def test_nothing_invokes_the_mirror_backfill_script():
    """scan_pipeline/scripts/backfill_weekly.py is a faithful mirror of the
    external runner and predates merge semantics: run against this repo's
    data/weekly it would replace whole weekly files. Nothing may call it.
    """
    root = Path(__file__).resolve().parents[1]
    hits = []
    for pattern in ("*.py", "*.yml", "*.yaml", "*.sh", "*.md"):
        for path in root.rglob(pattern):
            if ".git" in path.parts or path.name == Path(__file__).name:
                continue
            if path == root / "scan_pipeline" / "scripts" / "backfill_weekly.py":
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in ("scan_pipeline/scripts/backfill_weekly",
                           "scan_pipeline\\scripts\\backfill_weekly",
                           "scan_pipeline.scripts.backfill_weekly"):
                if needle in text:
                    hits.append(str(path.relative_to(root)))
    assert not hits, "something now invokes the mirror backfill: " + ", ".join(hits)
