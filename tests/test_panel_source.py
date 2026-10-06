"""The engines' panel reader, and a week that has two files.

`panel_source.load_price_cache` listed `data/weekly/*.json`. A corrected week
is two of those, `<date>.json` and `<date>.corrected.json`, both carrying the
same `as_of`, so the week was read twice. Every name got a second row for it
whose open was its own close: a 0.0 week-over-week return that never
happened. With the reader on, the committed panel (2026-08-21 and 2026-08-28
are corrected) gave, measured 2026-10-06:

  * twelve rows a name that covered ten weeks. The two flat rows alone
    lowered the 12-week standard deviation Marky scores on for 307 of the
    314 names scanned, by 8% at the median;
  * on the Monday after a corrected Friday, the flat row as the latest row
    of every name. Ophelia's sector base, the row before the latest, was
    then the latest week and not the one before it, and every four-row
    window (her volatility and momentum, Marky's momentum) held three weeks;
  * AVB's 2026-08-21 close of 65.9005 on volume 0, the bar the correction
    exists to drop, read from the base all the same.

The reader is opt-in (COUNCIL_SCAN_SOURCE=panel) and was off, so no book was
built on any of it. DATA_FEED.md sec.1: "Readers prefer the correction; the
original stays."

No network. The panels are built here, apart from two tests at the end that
ask the committed one: for one fixed window ending 2026-09-11, and for the
corrected weeks, whichever they are.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pytest

from conftest import ROOT, weekly_doc

from scan_pipeline import panel_source, snapshot
from scan_pipeline.utils.data_utils import (
    compute_4_week_return, compute_std_dev, get_price_history)

WEEKS = ["2026-07-31", "2026-08-07", "2026-08-14",
         "2026-08-21", "2026-08-28", "2026-09-04"]
# Real names, because universe() keeps only what the config can book. No two
# consecutive closes are equal: a flat week here is the reader's doing.
CLOSES = {"NVDA": [100.0, 104.0, 96.0, 108.0, 112.0, 120.0],
          "PLTR": [50.0, 52.0, 51.0, 49.0, 53.0, 55.0]}
CORRECTED = "2026-08-21"            # WEEKS[3]


def bar(close, volume=1_000_000):
    return {"close": close, "volume": volume}


# A name that trades, prints a close behind volume 0, and trades again. The
# first two bars are AVB's own; in the panel it never did trade again.
AVB = {"2026-08-14": {"AVB": bar(184.06)},
       "2026-08-21": {"AVB": bar(65.9005, volume=0)},
       "2026-08-28": {"AVB": bar(185.0)}}


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    """The reader caches by (directory, as_of, weeks), not by what is on disk."""
    monkeypatch.setattr(panel_source, "_CACHE", {})


def correction(base, drop=(), restate=None):
    """A full copy of `base`, as a correction is (DATA_FEED.md sec.1)."""
    doc = json.loads(json.dumps(base))
    for ticker in drop:
        doc["series"].pop(ticker)
        doc["missing"].append({"ticker": ticker, "reason": "dropped"})
    for ticker, close in (restate or {}).items():
        doc["series"][ticker]["close"] = close
    doc["corrects"] = base["as_of"] + ".json"
    doc["reason"] = "test"
    return doc


def files(corrections=None, weeks=WEEKS, extra=None):
    """{file name: doc} for `weeks`. `corrections` maps a date to the keyword
    arguments of correction(); `extra` maps a date to {ticker: bar} added to
    its base file."""
    out = {}
    for as_of in weeks:
        base = weekly_doc(as_of, [])
        base["series"] = {t: bar(series[WEEKS.index(as_of)])
                          for t, series in CLOSES.items()}
        base["series"].update((extra or {}).get(as_of, {}))
        out[as_of + ".json"] = base
        if corrections and as_of in corrections:
            out[as_of + ".corrected.json"] = correction(
                base, **corrections[as_of])
    return out


def rows(history):
    return [(h.date, h.open, h.close) for h in history]


def expected(ticker, first=1, closes=None):
    """Each week from WEEKS[first] on, once, opened at the week before's
    close."""
    series = closes or CLOSES[ticker]
    return [(WEEKS[i], series[i - 1], series[i])
            for i in range(first, len(WEEKS))]


# -- a week is read once -----------------------------------------------------

def test_a_week_with_a_correction_appears_once(panel):
    d = panel(files(corrections={CORRECTED: {}, "2026-08-28": {}}))
    cache = panel_source.load_price_cache(directory=str(d))
    for ticker, series in CLOSES.items():
        assert rows(cache[ticker]) == expected(ticker), ticker
        # what compute_std_dev is handed: the second row was a 0.0
        returns = [h.return_ for h in cache[ticker]]
        want = [(b - a) / a for a, b in zip(series, series[1:])]
        assert returns == pytest.approx(want), ticker
        assert compute_std_dev(returns) == pytest.approx(compute_std_dev(want))


def test_a_panel_with_no_correction_reads_as_it_always_did(panel):
    d = panel(files())
    cache = panel_source.load_price_cache(directory=str(d))
    assert {t: rows(h) for t, h in cache.items()} == {
        t: expected(t) for t in CLOSES}


# -- the correction is the week ----------------------------------------------

@pytest.mark.parametrize("restated", [101.0, 131.0],
                         ids=["below-the-base", "above-the-base"])
def test_the_corrections_close_wins(panel, restated):
    """Both rows used to be kept and sorted by close, so which of the two the
    next week opened at depended on which way the restatement went."""
    d = panel(files(corrections={CORRECTED: {"restate": {"NVDA": restated}}}))
    nvda = panel_source.load_price_cache(directory=str(d))["NVDA"]
    closes = list(CLOSES["NVDA"])
    base = closes[3]
    closes[3] = restated
    assert rows(nvda) == expected("NVDA", closes=closes)
    assert base not in [p for h in nvda for p in (h.open, h.close)]


def test_the_first_week_on_file_can_be_the_corrected_one(panel):
    """It has no row of its own, having no week before it. What it gives is
    the close the second week opens at."""
    d = panel(files(corrections={WEEKS[0]: {"restate": {"NVDA": 90.0}}}))
    nvda = panel_source.load_price_cache(directory=str(d))["NVDA"]
    closes = [90.0] + CLOSES["NVDA"][1:]
    assert rows(nvda) == expected("NVDA", closes=closes)


def test_a_bar_the_correction_drops_is_not_read(panel):
    """AVB on 2026-08-21: a close behind volume 0, which the base keeps."""
    d = panel(files(corrections={CORRECTED: {"drop": ["AVB"]}}, extra=AVB))
    cache = panel_source.load_price_cache(directory=str(d))
    avb = cache.get("AVB", [])
    assert CORRECTED not in [h.date for h in avb]
    assert 65.9005 not in [p for h in avb for p in (h.open, h.close)]
    # dropping one name leaves the others in the week as they were
    assert rows(cache["NVDA"]) == expected("NVDA")
    # Nothing here says what AVB's next row is. It opens at the close of two
    # weeks before, and whether a row may span a gap is not decided
    # (load_price_cache's docstring).


def test_as_of_on_the_corrected_week_itself_reads_the_correction(panel):
    """The cut-off compared file names, and "2026-08-21.corrected" sorts
    after "2026-08-21": asked for that very week, the reader took the base."""
    d = panel(files(corrections={CORRECTED: {"restate": {"NVDA": 101.0},
                                             "drop": ["AVB"]}}, extra=AVB))
    cache = panel_source.load_price_cache(as_of=CORRECTED, directory=str(d))
    assert rows(cache["NVDA"])[-1] == (CORRECTED, 96.0, 101.0)
    assert CORRECTED not in [h.date for h in cache.get("AVB", [])]


# -- what the engines ask for ------------------------------------------------

def test_the_monday_after_a_corrected_friday_the_engines_get_whole_weeks(
        panel):
    """The flat row was the latest row of every name. Ophelia's sector base
    is the row before the latest, of two: that became the latest week itself,
    a week ahead of the one she means. And each four-row window, her
    volatility and momentum and Marky's momentum, held three weeks."""
    friday, monday = "2026-08-28", "2026-08-31"
    d = panel(files(corrections={friday: {}}))
    cache = panel_source.load_price_cache(as_of=monday, directory=str(d))
    for ticker, series in CLOSES.items():
        two = get_price_history(ticker, monday, 2, cache)
        assert rows(two) == [(WEEKS[3], series[2], series[3]),
                             (friday, series[3], series[4])], ticker
        four = get_price_history(ticker, monday, 4, cache)
        assert [h.date for h in four] == WEEKS[1:5], ticker
        assert compute_4_week_return(four) == pytest.approx(
            (series[4] - series[1]) / series[1])


def test_weeks_counts_weeks_not_files(panel):
    """Three scored weeks are three weeks, whatever was corrected in them."""
    d = panel(files(corrections={CORRECTED: {}, "2026-08-28": {}}))
    cache = panel_source.load_price_cache(weeks=3, directory=str(d))
    for ticker in CLOSES:
        assert rows(cache[ticker]) == expected(ticker, first=3), ticker


def test_min_weeks_is_counted_in_weeks(panel, monkeypatch):
    """PLTR has four weeks on file, so three returns: one short of MIN_WEEKS.
    The second row of the corrected week made it four and let the name in."""
    docs = files(weeks=WEEKS[1:], corrections={CORRECTED: {}})
    del docs[WEEKS[1] + ".json"]["series"]["PLTR"]
    monkeypatch.setenv("COUNCIL_PANEL_DIR", str(panel(docs)))
    assert panel_source.universe() == ["NVDA"]
    assert panel_source.universe(min_weeks=3) == ["NVDA", "PLTR"]
    cache = panel_source.load_price_cache()
    assert len(cache["NVDA"]) == 4 and len(cache["PLTR"]) == 3


# -- one listing, and what comes with it -------------------------------------

def test_the_reader_lists_weeks_through_the_derivers_own_function(
        panel, monkeypatch):
    """One spelling of which file answers for a week. This reader had its
    own, and that is how it came to disagree with the deriver."""
    d = panel(files(corrections={CORRECTED: {}}))
    asked = []
    real = snapshot._load_weekly_files
    monkeypatch.setattr(snapshot, "_load_weekly_files",
                        lambda directory: asked.append(directory)
                        or real(directory))
    panel_source.load_price_cache(directory=str(d))
    assert asked == [str(d)]


def test_a_week_that_does_not_parse_is_not_stepped_over(panel):
    """It used to be, and the weeks either side of it then read as adjacent:
    2026-08-21 opening at the close of 2026-08-07. It is damage, the deriver
    does not read around it either, and the error says where to look."""
    d = panel(files())
    (d / "2026-08-14.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(panel_source.PanelUnreadable) as caught:
        panel_source.load_price_cache(directory=str(d))
    assert str(d) in str(caught.value)
    assert "truth_check.py --repo . --feed" in str(caught.value)
    assert isinstance(caught.value.__cause__, ValueError)


@pytest.mark.parametrize("first, loaded", [
    ("", False),
    ("from scan_pipeline.config import tickers\n", False),
    ("from scan_pipeline import snapshot\n", True),
], ids=["panel_source-first", "tickers-first", "snapshot-first"])
def test_importing_the_reader_does_not_import_the_deriver(panel, first,
                                                          loaded):
    """The reader imports snapshot when it first reads, not when it is
    imported: run_scan imports panel_source every Monday, panel on or off,
    and the default path should load what it always did. A clean interpreter
    each time, because in this one snapshot is long imported, and one per
    import order, each of which must also read the panel."""
    d = panel(files(weeks=WEEKS[1:]))
    probe = (
        "import sys\n" + first +
        "from scan_pipeline import panel_source\n"
        "loaded = 'scan_pipeline.snapshot' in sys.modules\n"
        "from scan_pipeline.config import tickers\n"
        "print(loaded, ','.join(tickers.scan_universe('2026-09-07')))\n")
    env = dict(os.environ, COUNCIL_SCAN_SOURCE="panel",
               COUNCIL_PANEL_DIR=str(d), PYTHONDONTWRITEBYTECODE="1")
    env.pop("COUNCIL_WIKI_WILDCARDS", None)
    r = subprocess.run([sys.executable, "-c", probe], cwd=str(ROOT), env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == [str(loaded), "NVDA,PLTR"], r.stdout


# -- the committed panel -----------------------------------------------------

REAL = ROOT / "data" / "weekly"


def test_the_reported_reproduction_on_the_committed_panel():
    """as_of 2026-09-11, six weeks. It printed 2026-08-21 and 2026-08-28
    twice each, so six rows covered four weeks."""
    cache = panel_source.load_price_cache(as_of="2026-09-11", weeks=6,
                                          directory=str(REAL))
    nvda = cache["NVDA"]
    assert [h.date for h in nvda] == [
        "2026-08-07", "2026-08-14", "2026-08-21", "2026-08-28",
        "2026-09-04", "2026-09-11"]
    assert all(b.open == a.close for a, b in zip(nvda, nvda[1:]))
    assert all(h.open != h.close for h in nvda)
    # 2026-08-21.corrected.json exists to drop this bar
    avb = cache.get("AVB", [])
    assert "2026-08-21" not in [h.date for h in avb]
    assert 65.9005 not in [p for h in avb for p in (h.open, h.close)]


def closes_of(week):
    """{ticker: close} from the file that answers for a week, spelled here
    without the reader's help."""
    fixed = REAL / (week + ".corrected.json")
    path = fixed if fixed.is_file() else REAL / (week + ".json")
    series = json.loads(path.read_text(encoding="utf-8"))["series"]
    return {t: float(b["close"]) for t, b in series.items()
            if b.get("close") is not None}


def test_every_correction_on_file_is_the_week_the_reader_returns():
    """Whatever is corrected, now or later. A corrected week reads from the
    week before's close to the correction's, for exactly the names both
    hold, and the week after opens at the correction's close.

    The window is the week before, the week and the week after, as far as
    they exist: the first week on file has no row of its own, the newest has
    no week after, and either can be the corrected one. A name the correction
    lacks is asked nothing about the week after (see the gap, above)."""
    on_file = sorted(p.stem for p in REAL.glob("*.json")
                     if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem))
    corrected = sorted(p.name[: -len(".corrected.json")]
                       for p in REAL.glob("*.corrected.json"))
    assert corrected, "the panel has held a correction since 2026-08-26"
    for week in corrected:
        i = on_file.index(week)
        held = closes_of(week)
        before = closes_of(on_file[i - 1]) if i else {}
        after = on_file[i + 1] if i + 1 < len(on_file) else None
        cache = panel_source.load_price_cache(
            as_of=after or week, weeks=2 if after else 1, directory=str(REAL))

        own = {t: [h for h in hist if h.date == week]
               for t, hist in cache.items()}
        own = {t: hs for t, hs in own.items() if hs}
        assert sorted(own) == sorted(set(held) & set(before)), week
        for ticker, hs in own.items():
            assert [(h.open, h.close) for h in hs] == [
                (before[ticker], held[ticker])], (week, ticker)

        if after:
            opens = {t: [h.open for h in hist if h.date == after]
                     for t, hist in cache.items() if t in held}
            opens = {t: o for t, o in opens.items() if o}
            assert sorted(opens) == sorted(set(held) & set(closes_of(after)))
            assert opens == {t: [held[t]] for t in opens}, week
