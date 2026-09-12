"""The corporate-action discontinuity detector.

Adjusted closes are anchored to the fetch date, so a panel straddling a split
shows the ratio rather than a market move. APH did this on 2026-09-03 and MNST
on 2026-08-11; neither is in the 110-name analysis set, which is exactly why
nothing caught them -- the heatmap's extreme-move flag only covers names
inside a scored basket.

The discriminating test here is the false-positive one. The first draft of
this check flagged SOUN, IONQ and QUBT for the same week of 2025-01-10, which
was the quantum-stock selloff, not three simultaneous 3:2 splits. A ratio
match is a candidate; only the provider's split history confirms one.

No network: yahoo_splits is stubbed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import truth_check as tc  # noqa: E402


def panel(tmp_path, closes_by_date, subdir="weekly"):
    """closes_by_date: {as_of: {ticker: close}}."""
    d = tmp_path / "data" / subdir
    d.mkdir(parents=True, exist_ok=True)
    for as_of, closes in closes_by_date.items():
        (d / (as_of + ".json")).write_text(json.dumps({
            "as_of": as_of, "source": "yahoo",
            "fetched_at": as_of + "T21:00:00Z", "session": "close",
            "series": {t: {"close": c, "volume": 1000}
                       for t, c in closes.items()},
            "missing": [],
        }), encoding="utf-8", newline="\n")
    return tmp_path


def run(tmp_path, monkeypatch, split_history):
    """split_history: {ticker: [(iso_date, ratio)]} or {ticker: None}."""
    monkeypatch.setattr(tc, "yahoo_splits",
                        lambda sym, start="2015-01-01":
                        split_history.get(sym, []))
    rep = tc.Report()
    tc.check_splits(tmp_path, rep)
    return rep


# -- confirmation ------------------------------------------------------------

def test_confirms_a_split_the_panel_straddles(tmp_path, monkeypatch):
    p = panel(tmp_path, {"2026-08-28": {"APH": 200.0},
                         "2026-09-04": {"APH": 105.0}})
    rep = run(p, monkeypatch, {"APH": [("2026-09-03", "2.0:1.0")]})
    out = rep.render()
    assert rep.counts["WARN"] == 1
    assert "APH split 2.0:1.0 on 2026-09-03" in out
    assert "the ratio, not a market move" in out


def test_dismisses_a_real_crash_that_lands_on_a_ratio(tmp_path, monkeypatch):
    """The quantum selloff: -33% is a 3:2 split AND an ordinary crash."""
    p = panel(tmp_path, {"2025-01-03": {"SOUN": 20.0},
                         "2025-01-10": {"SOUN": 13.4}})
    rep = run(p, monkeypatch, {"SOUN": []})
    assert rep.counts["WARN"] == 0
    assert "0 confirmed" in rep.render()


def test_dismisses_a_split_outside_the_flagged_window(tmp_path, monkeypatch):
    """SMCI split in 2024 and crashed in 2026. Different events."""
    p = panel(tmp_path, {"2026-03-13": {"SMCI": 60.0},
                         "2026-03-20": {"SMCI": 40.0}})
    rep = run(p, monkeypatch, {"SMCI": [("2024-10-01", "10.0:1.0")]})
    assert rep.counts["WARN"] == 0


def test_a_failed_fetch_is_unverified_not_dismissed(tmp_path, monkeypatch):
    """'No split' dismisses a candidate. A network failure must not."""
    p = panel(tmp_path, {"2026-08-28": {"APH": 200.0},
                         "2026-09-04": {"APH": 105.0}})
    rep = run(p, monkeypatch, {"APH": None})
    out = rep.render()
    assert rep.counts["WARN"] == 1
    assert "UNVERIFIED" in out


# -- thresholds --------------------------------------------------------------

def test_ordinary_moves_are_not_candidates(tmp_path, monkeypatch):
    p = panel(tmp_path, {"2026-08-28": {"AAA": 100.0},
                         "2026-09-04": {"AAA": 92.0}})
    rep = run(p, monkeypatch, {})
    assert rep.counts["WARN"] == 0
    assert "0 ratio candidate(s)" in rep.render()


def test_a_large_move_far_from_any_ratio_is_not_a_candidate(tmp_path,
                                                            monkeypatch):
    """-40% is large but matches no split ratio. Not this check's business."""
    p = panel(tmp_path, {"2026-08-28": {"AAA": 100.0},
                         "2026-09-04": {"AAA": 60.0}})
    rep = run(p, monkeypatch, {})
    assert "0 ratio candidate(s)" in rep.render()


def test_reverse_splits_are_detected(tmp_path, monkeypatch):
    p = panel(tmp_path, {"2026-08-28": {"AAA": 1.0},
                         "2026-09-04": {"AAA": 2.0}})
    rep = run(p, monkeypatch, {"AAA": [("2026-09-01", "1.0:2.0")]})
    assert rep.counts["WARN"] == 1


# -- acknowledgement ---------------------------------------------------------

def test_an_acknowledged_action_goes_quiet(tmp_path, monkeypatch):
    p = panel(tmp_path, {"2026-08-28": {"APH": 200.0},
                         "2026-09-04": {"APH": 105.0}})
    (p / "macro").mkdir(parents=True, exist_ok=True)
    (p / "macro" / "known_corporate_actions.json").write_text(json.dumps({
        "actions": [{"ticker": "APH", "between": "2026-08-28..2026-09-04"}]
    }), encoding="utf-8", newline="\n")
    rep = run(p, monkeypatch, {"APH": [("2026-09-03", "2.0:1.0")]})
    assert rep.counts["WARN"] == 0


def test_an_unparseable_acknowledgement_file_fails_loudly(tmp_path,
                                                          monkeypatch):
    p = panel(tmp_path, {"2026-08-28": {"APH": 200.0},
                         "2026-09-04": {"APH": 105.0}})
    (p / "macro").mkdir(parents=True, exist_ok=True)
    (p / "macro" / "known_corporate_actions.json").write_text(
        "{ not json", encoding="utf-8", newline="\n")
    rep = run(p, monkeypatch, {})
    assert rep.counts["FAIL"] == 1


def test_the_committed_acknowledgement_file_parses_and_covers_both():
    """The live file: if it stops matching, the warnings come back."""
    doc = json.loads((ROOT / "macro" / "known_corporate_actions.json")
                     .read_text(encoding="utf-8"))
    got = {(a["ticker"], a["between"]) for a in doc["actions"]}
    assert ("APH", "2026-08-28..2026-09-04") in got
    assert ("MNST", "2026-08-07..2026-08-14") in got
    for a in doc["actions"]:
        assert a["in_focus_110"] is False, (
            a["ticker"] + " is in the analysis set, so this is not just a "
            "market_state problem -- sector scores read it")
        assert a.get("resolution")


# -- panel coverage ----------------------------------------------------------

def test_scans_the_daily_panel_too(tmp_path, monkeypatch):
    panel(tmp_path, {"2026-09-03": {"AAA": 200.0},
                     "2026-09-04": {"AAA": 100.0}}, subdir="daily")
    rep = run(tmp_path, monkeypatch, {"AAA": [("2026-09-04", "2.0:1.0")]})
    assert "daily panel" in rep.render()


def test_no_panel_is_a_skip(tmp_path, monkeypatch):
    rep = run(tmp_path, monkeypatch, {})
    assert rep.counts["SKIP"] == 1


def test_corrections_supersede_originals(tmp_path, monkeypatch):
    p = panel(tmp_path, {"2026-08-28": {"APH": 200.0},
                         "2026-09-04": {"APH": 105.0}})
    corrected = json.loads((p / "data" / "weekly" / "2026-09-04.json")
                           .read_text(encoding="utf-8"))
    corrected["series"]["APH"]["close"] = 199.0      # restated, no longer a step
    corrected["corrects"] = "2026-09-04.json"
    corrected["reason"] = "provider restated"
    (p / "data" / "weekly" / "2026-09-04.corrected.json").write_text(
        json.dumps(corrected), encoding="utf-8", newline="\n")
    rep = run(p, monkeypatch, {"APH": [("2026-09-03", "2.0:1.0")]})
    assert rep.counts["WARN"] == 0
