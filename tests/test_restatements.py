"""Restated weeks of the paper portfolio (#112).

A closed week is never rewritten. portfolio/restatements/<week>.yaml carries
corrected figures beside portfolio/history/<week>.yaml and the metrics read
it in the week's place. These tests hold the committed restatements to the
weeks they restate, and the reader to its rules, on copies under tmp_path.
"""

import importlib.util
import json
import shutil

import pytest
import yaml

from conftest import ROOT

HISTORY = ROOT / "portfolio" / "history"
RESTATEMENTS = ROOT / "portfolio" / "restatements"


def _load_tracker():
    spec = importlib.util.spec_from_file_location(
        "portfolio_tracker_restatements", ROOT / "portfolio" / "tracker.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tk = _load_tracker()


def _read(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture
def book(tmp_path, monkeypatch):
    """A copy of the committed history and restatements, and nowhere else to
    write: the official book is never touched by a test."""
    history = tmp_path / "history"
    restatements = tmp_path / "restatements"
    shutil.copytree(HISTORY, history)
    shutil.copytree(RESTATEMENTS, restatements)
    monkeypatch.setattr(tk, "HISTORY_DIR", history)
    monkeypatch.setattr(tk, "RESTATEMENTS_DIR", restatements)
    monkeypatch.setattr(tk, "METRICS_PATH", tmp_path / "metrics.json")
    return history, restatements


def _restatements():
    return sorted(RESTATEMENTS.glob("*.yaml"))


def test_there_is_a_restatement_to_check():
    assert [p.name for p in _restatements()] == ["2026-09-14.yaml"]


@pytest.mark.parametrize("path", _restatements(), ids=lambda p: p.name)
def test_a_committed_restatement_fits_its_week(path):
    base = _read(HISTORY / path.name)
    restatement = _read(path)
    assert restatement["corrects"] == "portfolio/history/" + path.name
    week = tk.apply_restatement(base, restatement)
    # What was recorded is said, and it is what the history file holds.
    for field, value in restatement["recorded"].items():
        assert base[field] == value, field
    for pos in restatement["positions"]:
        held = next(p for p in base["positions"] if p["ticker"] == pos["ticker"])
        assert held["pnl_pct"] == pos["recorded_pnl_pct"], pos["ticker"]
        assert held["sponsor"] == pos["sponsor"], pos["ticker"]
    # The week's return is its positions' weighted returns, cash at zero.
    weighted = sum(p["weight"] * p["pnl_pct"] for p in week["positions"])
    assert round(weighted, 2) == week["weighted_return"]
    assert round(week["weighted_return"] - week["spy_return"], 2) \
        == pytest.approx(week["alpha"], abs=0.011)
    hits = sum(1 for p in week["positions"] if p["pnl_pct"] > 0)
    assert round(hits / len(week["positions"]), 2) == week["hit_rate"]


@pytest.mark.parametrize("path", _restatements(), ids=lambda p: p.name)
def test_a_restatement_leaves_every_sponsor_hit_count_alone(path):
    """The Council engines read history/*.yaml for each sponsor's hits and
    never this directory, so a restatement that flipped a position's sign
    would leave them counting the old result. None may."""
    base = _read(HISTORY / path.name)
    week = tk.apply_restatement(base, _read(path))
    for before, after in zip(base["positions"], week["positions"]):
        assert (before["pnl_pct"] > 0) == (after["pnl_pct"] > 0), before["ticker"]


def test_the_history_file_is_left_as_written(book):
    history, _ = book
    before = (history / "2026-09-14.yaml").read_bytes()
    tk.calculate_metrics()
    assert (history / "2026-09-14.yaml").read_bytes() == before


def test_the_metrics_read_the_restated_week(book):
    weeks = {w["week"]: w for w in tk.load_history_weeks()}
    assert weeks["2026-09-14"]["weighted_return"] == -0.31
    assert weeks["2026-09-14"]["spy_return"] == 0.6
    assert weeks["2026-09-14"]["alpha"] == -0.92
    assert "#112" in weeks["2026-09-14"]["restated"]
    assert "restated" not in weeks["2026-09-21"]


def test_the_committed_metrics_are_what_the_restated_history_gives(book):
    computed = tk.calculate_metrics()
    committed = json.loads(
        (ROOT / "portfolio" / "metrics.json").read_text(encoding="utf-8"))
    computed.pop("last_updated")
    committed.pop("last_updated")
    assert computed == committed


def test_without_restatements_the_recorded_week_comes_back(book):
    _, restatements = book
    shutil.rmtree(restatements)
    weeks = {w["week"]: w for w in tk.load_history_weeks()}
    week = weeks["2026-09-14"]
    assert (week["weighted_return"], week["spy_return"], week["alpha"]) \
        == (0.23, -0.34, 0.57)
    assert "restated" not in week


def test_a_restatement_that_names_other_positions_is_refused(book):
    _, restatements = book
    path = restatements / "2026-09-14.yaml"
    data = _read(path)
    data["positions"][0]["ticker"] = "XOM"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(tk.RestatementMismatch):
        tk.calculate_metrics()


def test_a_restatement_with_no_reason_is_refused(book):
    _, restatements = book
    path = restatements / "2026-09-14.yaml"
    data = _read(path)
    del data["reason"]
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(tk.RestatementMismatch):
        tk.calculate_metrics()


def test_a_restatement_of_a_week_with_no_history_is_refused(book):
    _, restatements = book
    data = _read(restatements / "2026-09-14.yaml")
    data["week"] = "2026-09-07"
    (restatements / "2026-09-07.yaml").write_text(
        yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(tk.RestatementMismatch):
        tk.calculate_metrics()


def test_restatements_are_ascii():
    for path in _restatements():
        path.read_bytes().decode("ascii")
