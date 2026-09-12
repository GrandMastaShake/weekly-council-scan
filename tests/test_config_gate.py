"""The config-drift gate.

This exists because its absence cost two weeks. `009f7f6` added
SECTOR_FOCUS_110 and FOCUS_TICKERS; `7cf7025` deleted them and their asserts;
CLAUDE.md kept documenting both and nothing failed. The tests below pin the
constants AND prove the gate actually fires -- a gate that cannot fail is
decoration.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import truth_check as tc  # noqa: E402
import scan_pipeline.config as tickers_pkg  # noqa: E402
from scan_pipeline.config import tickers as t  # noqa: E402


def stub_tickers(monkeypatch, **attrs):
    """Swap the tickers module check_config imports.

    `from scan_pipeline.config import tickers` resolves through the PACKAGE
    ATTRIBUTE before sys.modules, so patching sys.modules alone silently
    leaves the real module in place -- which is how the first draft of these
    tests "passed" against live data.
    """
    stub = type(sys)("tickers_stub")
    stub.STOCK_UNIVERSE = attrs.get("STOCK_UNIVERSE", ["AAA"])
    stub.BACKFILL_44_TICKERS = attrs.get("BACKFILL_44_TICKERS", [])
    stub.PRICE_FEED_UNIVERSE = attrs.get("PRICE_FEED_UNIVERSE", ["AAA"])
    for k in ("SECTOR_FOCUS_110", "FOCUS_TICKERS"):
        if k in attrs:
            setattr(stub, k, attrs[k])
    monkeypatch.setitem(sys.modules, "scan_pipeline.config.tickers", stub)
    monkeypatch.setattr(tickers_pkg, "tickers", stub)
    return stub


# -- the constants themselves ------------------------------------------------

def test_focus_set_is_eleven_sectors_of_ten():
    assert len(t.SECTOR_FOCUS_110) == 11
    for sector, names in t.SECTOR_FOCUS_110.items():
        assert len(names) == 10, sector + " has " + str(len(names))


def test_focus_tickers_is_exactly_110_unique_names():
    assert len(t.FOCUS_TICKERS) == 110
    assert len(set(t.FOCUS_TICKERS)) == 110


def test_price_feed_is_the_union_of_engine_set_and_backfill():
    assert set(t.PRICE_FEED_UNIVERSE) == (set(t.STOCK_UNIVERSE)
                                          | set(t.BACKFILL_44_TICKERS))
    assert t.PRICE_FEED_UNIVERSE == sorted(set(t.PRICE_FEED_UNIVERSE))


def test_focus_is_bound_against_the_feed_not_the_engine_set():
    """The assert that was wrong before, and took the whole block down.

    STOCK_UNIVERSE is the ENGINE set and does not contain the backfilled
    names, so bounding the focus set against it cannot hold.
    """
    assert set(t.FOCUS_TICKERS) <= set(t.PRICE_FEED_UNIVERSE)
    assert not set(t.FOCUS_TICKERS) <= set(t.STOCK_UNIVERSE), (
        "if this ever passes, the engine set has widened and the comment "
        "explaining why the bound is PRICE_FEED_UNIVERSE needs revisiting")


def test_feed_is_never_narrower_than_the_analysis_set():
    assert len(t.PRICE_FEED_UNIVERSE) > len(t.FOCUS_TICKERS)


# -- the gate fires ----------------------------------------------------------

class FakeRepo:
    """A repo tree with just the two files check_config reads."""

    def __init__(self, tmp_path, claude_text, weekly_doc=None):
        self.root = tmp_path
        (tmp_path / "CLAUDE.md").write_text(claude_text, encoding="utf-8",
                                            newline="\n")
        if weekly_doc is not None:
            d = tmp_path / "data" / "weekly"
            d.mkdir(parents=True)
            (d / "2026-09-11.json").write_text(
                json.dumps(weekly_doc), encoding="utf-8", newline="\n")


def run_gate(repo_root):
    rep = tc.Report()
    tc.check_config(Path(repo_root), rep)
    return rep


def test_gate_passes_on_the_real_repo():
    rep = run_gate(ROOT)
    assert rep.counts["FAIL"] == 0, rep.render()


def test_gate_fails_when_docs_name_a_symbol_the_code_lacks(tmp_path,
                                                           monkeypatch):
    """The 7cf7025 regression, reproduced."""
    fake = FakeRepo(tmp_path, "We use `SECTOR_FOCUS_110` and `FOCUS_TICKERS`.")
    stub_tickers(monkeypatch)
    rep = run_gate(fake.root)
    msgs = rep.render()
    assert rep.counts["FAIL"] == 2
    assert "SECTOR_FOCUS_110" in msgs and "FOCUS_TICKERS" in msgs
    assert "docs and the code disagree" in msgs


def test_gate_does_not_emit_ok_alongside_failures(tmp_path, monkeypatch):
    fake = FakeRepo(tmp_path, "We use `SECTOR_FOCUS_110`.")
    stub_tickers(monkeypatch)
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] >= 1
    assert rep.counts["OK"] == 0, "an OK next to a FAIL reads as a pass"


def test_gate_fails_a_focus_name_outside_the_feed(tmp_path, monkeypatch):
    fake = FakeRepo(tmp_path, "no symbols documented here")
    focus = {"S%d" % i: ["T%d_%d" % (i, j) for j in range(10)]
             for i in range(11)}
    stub_tickers(monkeypatch, SECTOR_FOCUS_110=focus,
                 FOCUS_TICKERS=sorted(x for xs in focus.values() for x in xs))
    rep = run_gate(fake.root)
    assert "outside the price feed" in rep.render()


def test_gate_fails_a_focus_name_absent_from_the_panel_without_a_reason(
        tmp_path, monkeypatch):
    """A silently absent ticker is the ambiguity the feed contract removes."""
    focus = {"S%d" % i: ["T%d_%d" % (i, j) for j in range(10)]
             for i in range(11)}
    names = [x for xs in focus.values() for x in xs]
    fake = FakeRepo(tmp_path, "none",
                    weekly_doc={"series": {n: {"close": 1.0, "volume": 1}
                                           for n in names[:-1]},
                                "missing": []})
    stub_tickers(monkeypatch, STOCK_UNIVERSE=names,
                 PRICE_FEED_UNIVERSE=sorted(names),
                 SECTOR_FOCUS_110=focus, FOCUS_TICKERS=sorted(names))
    rep = run_gate(fake.root)
    assert "no bar and no" in rep.render()


def test_gate_accepts_a_panel_absence_that_declares_a_reason(tmp_path,
                                                             monkeypatch):
    """AVB is legitimately absent every week and says so. Not a failure."""
    focus = {"S%d" % i: ["T%d_%d" % (i, j) for j in range(10)]
             for i in range(11)}
    names = [x for xs in focus.values() for x in xs]
    fake = FakeRepo(tmp_path, "none",
                    weekly_doc={"series": {n: {"close": 1.0, "volume": 1}
                                           for n in names[:-1]},
                                "missing": [{"ticker": names[-1],
                                             "reason": "no bar for the week"}]})
    stub_tickers(monkeypatch, STOCK_UNIVERSE=names,
                 PRICE_FEED_UNIVERSE=sorted(names),
                 SECTOR_FOCUS_110=focus, FOCUS_TICKERS=sorted(names))
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 0, rep.render()
