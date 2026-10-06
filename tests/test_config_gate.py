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
from scan_pipeline import snapshot  # noqa: E402
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
    # The gate also asks snapshot which names the weekly writer fetches, and
    # snapshot bound the real feed when it was imported. Unless a test says
    # otherwise (WRITER), the writer fetches exactly the stubbed feed.
    writer = sorted(attrs.get("WRITER", stub.PRICE_FEED_UNIVERSE))
    monkeypatch.setattr(snapshot, "equity_universe", lambda: list(writer))
    # And the gate keeps its own copy of that set for the weekly job's check
    # dir (tc.EQUITY_UNIVERSE), which it holds to the writer's. Unless a test
    # says otherwise (GATE_LIST), the copy is in step.
    monkeypatch.setattr(tc, "EQUITY_UNIVERSE",
                        tuple(attrs.get("GATE_LIST", writer)))
    return stub


# -- the constants themselves ------------------------------------------------

def test_focus_set_is_eleven_sectors_of_ten_but_real_estate():
    """Real Estate holds nine since AVB left the owner's list (2026-09-21)."""
    assert len(t.SECTOR_FOCUS_110) == 11
    for sector, names in t.SECTOR_FOCUS_110.items():
        want = 9 if sector == "Real Estate" else 10
        assert len(names) == want, sector + " has " + str(len(names))
    assert "AVB" not in t.FOCUS_TICKERS


def test_focus_tickers_is_exactly_focus_size_unique_names():
    assert t.FOCUS_SIZE == 109
    assert len(t.FOCUS_TICKERS) == t.FOCUS_SIZE
    assert len(set(t.FOCUS_TICKERS)) == t.FOCUS_SIZE


def test_price_feed_is_the_union_of_its_three_parts():
    """Engine set, backfill and the Council watchlist (2026-09-21). The
    feed-only slot that carried AVB for the old 110 is gone with it."""
    assert set(t.PRICE_FEED_UNIVERSE) == (set(t.STOCK_UNIVERSE)
                                          | set(t.BACKFILL_44_TICKERS)
                                          | set(t.COUNCIL_WATCHLIST))
    assert not hasattr(t, "FEED_ONLY_TICKERS")
    assert t.PRICE_FEED_UNIVERSE == sorted(set(t.PRICE_FEED_UNIVERSE))


def test_the_weekly_writer_fetches_the_whole_feed():
    """The feed constant and the set the weekly writer fetches, held together.

    snapshot.equity_universe() spelled the union out for itself until
    2026-10-06, and missed the Council watchlist when it joined the feed on
    2026-09-21: BTC and GLD were in PRICE_FEED_UNIVERSE and the daily files,
    and in no weekly file -- not in `series`, not in `missing`.
    """
    writer = set(snapshot.equity_universe())
    assert set(t.PRICE_FEED_UNIVERSE) <= writer
    assert {"BTC", "GLD"} <= writer
    # The feed, the sixteen index and sector ETFs, and nothing else.
    etfs = set(snapshot.INDEX_TICKERS) | set(snapshot.SECTOR_TICKERS)
    assert len(etfs) == 16
    assert writer == set(t.PRICE_FEED_UNIVERSE) | etfs
    assert snapshot.equity_universe() == sorted(writer)


def test_the_weekly_writer_reads_the_feed_constant_not_a_copy(monkeypatch):
    """A second spelling of the union is what drifted. A name that joins the
    feed has to reach the writer without anyone editing snapshot.py."""
    monkeypatch.setattr(snapshot, "PRICE_FEED_UNIVERSE",
                        list(t.PRICE_FEED_UNIVERSE) + ["JOINED_LATER"])
    assert "JOINED_LATER" in snapshot.equity_universe()


def test_universe_json_does_not_follow_the_feed(tmp_path):
    """build_universe() keeps its own, narrower set on purpose. universe.json
    mirrors wiki/universe.md, which lists stocks: the engines' set and the 44
    fed beside it, and not the sixteen ETFs or the watchlist's BTC and GLD.
    "One function for the feed" is a rule for the two price writers."""
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    doc = snapshot.build_universe(str(wiki), str(tmp_path / "universe.json"),
                                  enrich=False)
    names = {e["t"] for e in doc["tickers"]}
    assert names == set(t.STOCK_UNIVERSE) | set(t.BACKFILL_44_TICKERS)
    assert not names & {"BTC", "GLD", "SPY", "XLK"}


def test_council_watchlist_is_the_owners_111():
    """Council v2's universe: the owner's list, which is the focus set's 109
    stocks plus two macro ETFs. Stocks keep their heatmap/wiki sector."""
    assert len(t.COUNCIL_WATCHLIST) == 111
    focus = {x: s for s, xs in t.SECTOR_FOCUS_110.items() for x in xs}
    etfs = {x for x, s in t.COUNCIL_SECTORS.items() if s == "Macro Assets"}
    assert etfs == {"BTC", "GLD"}
    stocks = set(t.COUNCIL_WATCHLIST) - etfs
    assert stocks == set(focus)
    assert all(t.COUNCIL_SECTORS[x] == focus[x] for x in stocks)
    assert set(t.COUNCIL_WATCHLIST) <= set(t.PRICE_FEED_UNIVERSE)


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
    """A repo tree with just the files check_config reads: CLAUDE.md and the
    weekly panel. `weekly_doc` is one week; `weekly_docs` maps file names to
    documents, for a panel of several."""

    def __init__(self, tmp_path, claude_text, weekly_doc=None,
                 weekly_docs=None):
        self.root = tmp_path
        (tmp_path / "CLAUDE.md").write_text(claude_text, encoding="utf-8",
                                            newline="\n")
        docs = dict(weekly_docs or {})
        if weekly_doc is not None:
            docs["2026-09-11.json"] = weekly_doc
        if docs:
            d = tmp_path / "data" / "weekly"
            d.mkdir(parents=True)
            for name, doc in docs.items():
                (d / name).write_text(
                    json.dumps(doc), encoding="utf-8", newline="\n")


def week(names, missing=()):
    """A weekly file holding a bar for each name and a reason for each of
    `missing`."""
    return {"series": {n: {"close": 1.0, "volume": 1} for n in names},
            "missing": [{"ticker": n, "reason": "no bar for the week"}
                        for n in missing]}


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
    """A name absent with a declared reason, as AVB was after its merger, is
    not a failure."""
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


@pytest.mark.parametrize("said", [{}, {"reason": ""}, {"reason": None},
                                  {"reason": "None"}], ids=repr)
def test_gate_does_not_take_a_name_typed_into_missing_for_a_reason(
        tmp_path, monkeypatch, said):
    """The cheapest way past "no bar and no `missing` entry": the name in
    the list with nothing beside it. An entry that gives no reason accounts
    for no name (truth_check._accounts), here as under --feed."""
    focus = {"S%d" % i: ["T%d_%d" % (i, j) for j in range(10)]
             for i in range(11)}
    names = [x for xs in focus.values() for x in xs]
    fake = FakeRepo(tmp_path, "none",
                    weekly_doc={"series": {n: {"close": 1.0, "volume": 1}
                                           for n in names[:-1]},
                                "missing": [dict(said, ticker=names[-1])]})
    stub_tickers(monkeypatch, STOCK_UNIVERSE=names,
                 PRICE_FEED_UNIVERSE=sorted(names),
                 SECTOR_FOCUS_110=focus, FOCUS_TICKERS=sorted(names))
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] >= 1
    assert "no bar and no" in rep.render() and names[-1] in rep.render()


# -- the weekly writer and the whole feed ------------------------------------
#
# BTC and GLD joined PRICE_FEED_UNIVERSE on 2026-09-21. For two weekly builds
# the writer went on fetching its own, older spelling of the feed, and the
# gate above, which asked the newest file for the focus names only, passed
# both files. Each test below is one half of that.

def test_gate_fails_a_weekly_writer_narrower_than_the_feed(tmp_path,
                                                           monkeypatch):
    """The drift itself: the constant gains two names and the set the writer
    fetches does not."""
    fake = FakeRepo(tmp_path, "none")
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA", "BTC", "GLD"],
                 WRITER=["AAA", "SPY"])
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 1, rep.render()
    assert "equity_universe() leaves out ['BTC', 'GLD']" in rep.render()
    assert rep.counts["OK"] == 0


def test_gate_passes_a_weekly_writer_wider_than_the_feed(tmp_path,
                                                         monkeypatch):
    """The writer adds the index and sector ETFs. Wider is the design."""
    fake = FakeRepo(tmp_path, "none")
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA"],
                 WRITER=["AAA", "SPY", "XLK"])
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 0, rep.render()
    assert rep.counts["OK"] == 1


def test_gate_fails_a_list_of_its_own_that_lacks_a_name_the_writer_fetches(
        tmp_path, monkeypatch):
    """The gate carries the writer's names for the weekly job's check dir,
    where there is no scan_pipeline/ to ask (tests/test_feed_names.py). A
    name that joined the feed and not that list is one the job is never
    asked for: the same drift as BTC and GLD, one file further on."""
    fake = FakeRepo(tmp_path, "none")
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA", "BTC"],
                 WRITER=["AAA", "BTC", "SPY"], GATE_LIST=["AAA", "SPY"])
    rep = run_gate(fake.root)
    msgs = rep.render()
    assert rep.counts["FAIL"] == 1, msgs
    assert "EQUITY_UNIVERSE in scripts/truth_check.py is not" in msgs
    assert "it lacks ['BTC']" in msgs
    assert "still lists" not in msgs
    assert rep.counts["OK"] == 0


def test_gate_fails_a_list_of_its_own_that_kept_a_name_the_feed_dropped(
        tmp_path, monkeypatch):
    """The other direction. The job would be told a week is short of a name
    nobody fetches any more, and could not push a week that is whole."""
    fake = FakeRepo(tmp_path, "none")
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA"],
                 WRITER=["AAA", "SPY"], GATE_LIST=["AAA", "EA", "HES", "SPY"])
    rep = run_gate(fake.root)
    msgs = rep.render()
    assert rep.counts["FAIL"] == 1, msgs
    assert "it still lists ['EA', 'HES']" in msgs
    assert "it lacks" not in msgs


def test_gate_says_both_when_its_list_is_off_in_both_directions(
        tmp_path, monkeypatch):
    fake = FakeRepo(tmp_path, "none")
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA", "BTC"],
                 WRITER=["AAA", "BTC"], GATE_LIST=["AAA", "EA"])
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 1, rep.render()
    assert "it lacks ['BTC'] and it still lists ['EA']" in rep.render()


def test_gate_does_not_judge_its_list_when_the_writer_cannot_be_asked(
        tmp_path, monkeypatch):
    """No writer, no comparison: that failure has its own line, and a second
    one saying every name is surplus would be noise about the same thing."""
    fake = FakeRepo(tmp_path, "none")
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA"],
                 GATE_LIST=["AAA", "EA"])

    def broken():
        raise RuntimeError("no universe today")
    monkeypatch.setattr(snapshot, "equity_universe", broken)
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 1, rep.render()
    assert "cannot ask scan_pipeline.snapshot" in rep.render()
    assert "EQUITY_UNIVERSE" not in rep.render()


def test_gate_fails_when_the_writer_cannot_be_asked(tmp_path, monkeypatch):
    """No answer is not a pass, and the newest week is still held to the
    feed."""
    fake = FakeRepo(tmp_path, "none", weekly_doc=week(["AAA"]))
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA", "BTC"])

    def broken():
        raise RuntimeError("no universe today")
    monkeypatch.setattr(snapshot, "equity_universe", broken)
    rep = run_gate(fake.root)
    msgs = rep.render()
    assert rep.counts["FAIL"] == 2, msgs
    assert "cannot ask scan_pipeline.snapshot" in msgs
    assert "no universe today" in msgs
    assert "has no bar and no `missing` entry for ['BTC']" in msgs
    assert rep.counts["OK"] == 0


def test_gate_fails_a_feed_name_the_newest_week_does_not_account_for(
        tmp_path, monkeypatch):
    """BTC and GLD as they stood: in the feed, outside the focus set, and in
    neither `series` nor `missing` of the newest weekly file."""
    focus = {"S%d" % i: ["T%d_%d" % (i, j) for j in range(10)]
             for i in range(11)}
    names = [x for xs in focus.values() for x in xs]
    fake = FakeRepo(tmp_path, "none", weekly_doc=week(names))
    stub_tickers(monkeypatch, STOCK_UNIVERSE=names,
                 PRICE_FEED_UNIVERSE=sorted(names + ["BTC", "GLD"]),
                 SECTOR_FOCUS_110=focus, FOCUS_TICKERS=sorted(names))
    rep = run_gate(fake.root)
    msgs = rep.render()
    assert rep.counts["FAIL"] == 1, msgs
    assert ("2026-09-11.json has no bar and no `missing` entry for "
            "['BTC', 'GLD']") in msgs
    assert "--merge" in msgs, "the message has to say how a name joins a week"
    assert rep.counts["OK"] == 0


def test_gate_accepts_a_feed_name_the_newest_week_lists_as_missing(
        tmp_path, monkeypatch):
    """A bar or a reason. SPCX before it listed is the standing case."""
    fake = FakeRepo(tmp_path, "none",
                    weekly_doc=week(["AAA", "BTC"], missing=["GLD"]))
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA", "BTC", "GLD"])
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 0, rep.render()


def test_gate_holds_the_newest_week_to_the_etfs_the_writer_adds(tmp_path,
                                                                monkeypatch):
    """The sixteen index and sector ETFs are in no ticker list: the writer
    adds them. A newest week without one is the same silent absence, and
    2024-08-09.json was written without all sixteen."""
    fake = FakeRepo(tmp_path, "none", weekly_doc=week(["AAA", "SPY"]))
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA"],
                 WRITER=["AAA", "SPY", "XLK"])
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 1, rep.render()
    assert "has no bar and no `missing` entry for ['XLK']" in rep.render()


def test_gate_reads_the_newest_week_and_no_other(tmp_path, monkeypatch):
    """A name missing from an older week is a name that joined later: VMRK
    has bars from 2026-08-21 and none before. The newest week is the one the
    writer has just produced, and the one this holds."""
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA", "JOINED"])

    older_lacks = tmp_path / "older_lacks"
    older_lacks.mkdir()
    fake = FakeRepo(older_lacks, "none", weekly_docs={
        "2026-09-04.json": week(["AAA"]),
        "2026-09-11.json": week(["AAA", "JOINED"])})
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 0, rep.render()

    newest_lacks = tmp_path / "newest_lacks"
    newest_lacks.mkdir()
    fake = FakeRepo(newest_lacks, "none", weekly_docs={
        "2026-09-04.json": week(["AAA", "JOINED"]),
        "2026-09-11.json": week(["AAA"])})
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 1, rep.render()
    assert ("2026-09-11.json has no bar and no `missing` entry for "
            "['JOINED']") in rep.render()


def test_gate_reads_the_base_file_of_a_corrected_newest_week(tmp_path,
                                                             monkeypatch):
    """The question is what the writer was asked to fetch, and a correction
    is a copy made afterwards. A name only the correction holds was never
    fetched for the week; a stale correction is another test's business
    (tests/test_instrument_sessions.py)."""
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA", "BTC"])
    fake = FakeRepo(tmp_path, "none", weekly_docs={
        "2026-09-11.json": week(["AAA"]),
        "2026-09-11.corrected.json": week(["AAA", "BTC"])})
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 1, rep.render()
    assert "2026-09-11.json has no bar" in rep.render()


def test_gate_fails_cleanly_on_a_newest_week_it_cannot_read(tmp_path,
                                                            monkeypatch):
    """CI and the daily job run --feed --config in one call. A traceback
    here would lose every line --feed had collected about the same file."""
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA"])
    for label, body in (("not_json", "{ this is not json"),
                        ("a_list", "[1, 2, 3]")):
        root = tmp_path / label
        (root / "data" / "weekly").mkdir(parents=True)
        (root / "CLAUDE.md").write_text("none", encoding="utf-8",
                                        newline="\n")
        (root / "data" / "weekly" / "2026-09-11.json").write_text(
            body, encoding="utf-8", newline="\n")
        rep = run_gate(root)
        assert rep.counts["FAIL"] == 1, rep.render()
        assert "cannot read 2026-09-11.json" in rep.render()
        assert rep.counts["OK"] == 0


def test_gate_survives_a_malformed_missing_list(tmp_path, monkeypatch):
    """A bare string where an entry belongs is --feed's finding. It must not
    stop this check from saying what is absent."""
    doc = week(["AAA"])
    doc["missing"] = ["GLD", {"ticker": "BTC", "reason": "no bar"}]
    fake = FakeRepo(tmp_path, "none", weekly_doc=doc)
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=["AAA", "BTC", "GLD"])
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 1, rep.render()
    assert "for ['GLD']" in rep.render()


def test_gate_shortens_a_long_list_of_names(tmp_path, monkeypatch):
    """A writer that lost a whole set would print three hundred names."""
    feed = ["N%03d" % i for i in range(40)]
    fake = FakeRepo(tmp_path, "none")
    stub_tickers(monkeypatch, PRICE_FEED_UNIVERSE=feed, WRITER=feed[:10])
    rep = run_gate(fake.root)
    msgs = rep.render()
    assert rep.counts["FAIL"] == 1, msgs
    assert "'N010'" in msgs and "'N021'" in msgs
    assert "'N022'" not in msgs
    assert "and 18 more" in msgs


def test_gate_fails_when_docs_name_the_watchlist_and_the_code_lacks_it(
        tmp_path, monkeypatch):
    """CLAUDE.md describes the feed as a union of three sets since
    2026-10-06. The third is held like the other two."""
    fake = FakeRepo(tmp_path, "The feed includes `COUNCIL_WATCHLIST`.")
    stub_tickers(monkeypatch)
    rep = run_gate(fake.root)
    assert rep.counts["FAIL"] == 1, rep.render()
    assert "COUNCIL_WATCHLIST" in rep.render()


def test_every_name_the_writer_fetches_is_in_the_newest_week_on_file():
    """The real panel, stated without the gate in between: after the merge
    of 2026-10-06 the newest weekly file has a bar or a reason for all of
    the feed and all sixteen ETFs."""
    weekly = ROOT / "data" / "weekly"
    newest = sorted(f for f in weekly.glob("*.json")
                    if "corrected" not in f.name)[-1]
    doc = json.loads(newest.read_text(encoding="utf-8"))
    held = set(doc["series"]) | {m["ticker"] for m in doc["missing"]}
    assert not sorted(set(snapshot.equity_universe()) - held), newest.name
    assert {"BTC", "GLD"} <= held


def test_the_engines_panel_scan_set_leaves_out_btc_and_gld(monkeypatch):
    """Fed and stored, not scanned. Every weekly file has held BTC and GLD
    since 2026-10-06, so the opt-in panel reader loads both. Neither is in a
    list the engines book from, and an ETF has no fundamentals for Cecil to
    value; putting them in front of an engine is Council v2's decision, not
    a side effect of widening the feed."""
    from scan_pipeline import panel_source
    monkeypatch.setenv("COUNCIL_SCAN_SOURCE", "panel")
    monkeypatch.setenv("COUNCIL_PANEL_DIR", str(ROOT / "data" / "weekly"))
    monkeypatch.delenv("COUNCIL_WIKI_WILDCARDS", raising=False)
    monkeypatch.setattr(panel_source, "_CACHE", {})
    assert {"BTC", "GLD"} <= set(panel_source.load_price_cache())
    scan = set(panel_source.universe())
    assert "NVDA" in scan and "PLTR" in scan, "the panel was not read"
    assert not scan & {"BTC", "GLD"}
    assert not {"BTC", "GLD"} & set(t.scan_universe())
