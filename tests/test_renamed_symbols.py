"""One company, one symbol a week.

The provider serves a renamed company's whole history under the symbol it
trades by now, and of the retired symbol it keeps at most the last session.
On 2026-10-06 each was found to make `--merge` write what it must not, with
exit 0 and every gate passing:

  * named for the weeks that hold EQR, VMRK came back with EQR's own bars,
    and the merge added them a second time;
  * `--only EQR --merge` over 2026-08-21 filed EQR's close of Monday
    2026-08-17 under the Friday, beside VMRK's own bar.

A bar added to a week is never taken out. What stands in the way now, and is
held here:

  * a rename on record (RENAMED, scan_pipeline/config/tickers.py): the old
    symbol is never merged, and the new one is not added to any week up to
    the old one's last bar. Read off every week on file, so the whole run
    is refused before it downloads;
  * a rename nobody recorded: the writer refuses on the bars themselves, the
    same volume under one other key in three weeks or more;
  * truth_check --feed fails a week that holds both symbols however it came
    to, warns when they interleave, and no longer asks a week, the newest
    one included, for a symbol whose company it holds.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date

import pytest

from conftest import SCRIPTS, weekly_doc

import audit_series  # noqa: E402  (conftest stubs the provider)
import backfill_weekly as bf  # noqa: E402
import truth_check as tc  # noqa: E402
from scan_pipeline.config import tickers  # noqa: E402

ETFS = list(tc.INDEX_AND_SECTOR_ETFS)
STOCKS = ["AAPL", "JNJ", "XOM"]

# EQR's last three weeks, the two between in which the company traded as
# VMRK and the panel held neither symbol, and VMRK's first two. Before them
# all, a week that holds neither: 2024-08-09.json in the real panel.
FIRST = "2026-07-24"
EQR_WEEKS = ["2026-07-31", "2026-08-07", "2026-08-14"]
GAP_WEEKS = ["2026-08-21", "2026-08-28"]
VMRK_WEEKS = ["2026-09-04", "2026-09-11"]
ALL_WEEKS = [FIRST] + EQR_WEEKS + GAP_WEEKS + VMRK_WEEKS


def day(iso):
    return date.fromisoformat(iso)


def week(as_of, extra=(), missing=(), prints=()):
    """One week. `prints` are names given a close on no volume."""
    doc = weekly_doc(as_of, ETFS + STOCKS + list(extra))
    for name in prints:
        doc["series"][name] = {"close": 65.9, "volume": 0}
    doc["missing"] = [{"ticker": t, "reason": "no bar dated " + as_of}
                      for t in missing]
    return doc


def renamed_panel(**overrides):
    files = {FIRST + ".json": week(FIRST, missing=["EQR"])}
    files.update({d + ".json": week(d, extra=["EQR"]) for d in EQR_WEEKS})
    files.update({d + ".json": week(d, missing=["EQR"]) for d in GAP_WEEKS})
    files.update({d + ".json": week(d, extra=["VMRK"]) for d in VMRK_WEEKS})
    files.update(overrides)
    return files


def correction_of(doc, name):
    out = json.loads(json.dumps(doc))
    out["corrects"] = name
    out["reason"] = "a test"
    return out


def snapshot_of(weekly):
    return {p.name: p.read_bytes() for p in sorted(weekly.glob("*.json"))}


def run_main(monkeypatch, tmp_path, *args) -> int:
    monkeypatch.setattr(sys, "argv", ["backfill_weekly.py", "--out",
                                      str(tmp_path / "data"), *args])
    return bf.main()


def provider(monkeypatch, bars):
    """Stand in for the download: {ticker: {iso day: (close, volume)}}."""
    def download(names, first, last):
        out = {}
        for t in names:
            days = sorted(bars.get(t, {}))
            out[t] = ([day(d) for d in days],
                      [bars[t][d][0] for d in days],
                      [bars[t][d][1] for d in days])
        return out
    monkeypatch.setattr(bf, "download_equity_history", download)


def no_provider(monkeypatch):
    def download(*args, **kwargs):
        raise AssertionError("refused on the files, so nothing is downloaded")
    monkeypatch.setattr(bf, "download_equity_history", download)


# -- the map --------------------------------------------------------------------

def test_the_gate_the_audit_and_the_writer_read_one_map():
    """truth_check stays stdlib-only and runs where there is no
    scan_pipeline/, so it repeats the map. The audit and the writer read
    the config's."""
    assert tc.RENAMED_SYMBOLS == tickers.RENAMED
    assert audit_series.SUCCESSORS is tickers.RENAMED
    assert bf.feed_tickers is tickers


def test_the_renames_of_the_2026_09_21_review_are_on_record():
    """Held as four entries, not as the whole map: the next rename adds one,
    and the test above is what makes it add it in both places."""
    for old, new in {"BK": "BNY", "MMC": "MRSH", "PEAK": "DOC",
                     "EQR": "VMRK"}.items():
        assert tickers.RENAMED[old] == new
    assert "AVB" not in tickers.RENAMED, (
        "absorbed, not renamed: no symbol serves its history")


def test_an_old_symbol_is_not_in_the_feed():
    """A symbol in the feed is fetched every Saturday. A retired one comes
    back empty, or with a print under a dead symbol."""
    assert not set(tickers.RENAMED) & set(tickers.PRICE_FEED_UNIVERSE)


def test_a_rename_reads_both_ways_and_along_a_chain(monkeypatch):
    assert tickers.earlier_symbols("VMRK") == ["EQR"]
    assert tickers.later_symbols("EQR") == ["VMRK"]
    assert tickers.earlier_symbols("EQR") == []
    assert tickers.later_symbols("VMRK") == []
    assert tickers.earlier_symbols("AAPL") == tickers.later_symbols("AAPL") == []

    monkeypatch.setattr(tickers, "RENAMED", {"A": "B", "B": "C"})
    assert tickers.earlier_symbols("C") == ["B", "A"]
    assert tickers.later_symbols("A") == ["B", "C"]
    assert audit_series.successor("A") == "C", (
        "the audit asks the symbol that carries the history today, not the "
        "retired one in the middle")
    assert audit_series.successor("C") == "C"

    monkeypatch.setattr(tickers, "RENAMED", {"A": "B", "B": "A"})
    assert tickers.later_symbols("A") == ["B"], "a loop ends"
    assert tickers.earlier_symbols("A") == ["B"]


def test_a_merger_is_not_a_rename():
    """Two old symbols for one new are two companies that became one. The
    gate groups whatever a map names, so with AVB -> VMRK beside EQR -> VMRK
    every week that holds AVB and EQR would read as one company twice.
    tickers.py refuses such a map where it is defined."""
    assert len(set(tickers.RENAMED.values())) == len(tickers.RENAMED)
    groups = tc._companies({"AVB": "VMRK", "EQR": "VMRK"})
    assert groups["AVB"] == {"AVB", "EQR", "VMRK"}


def test_the_gate_groups_the_symbols_of_one_company():
    groups = tc._companies({"A": "B", "B": "C", "X": "Y"})
    assert groups["A"] == groups["B"] == groups["C"] == {"A", "B", "C"}
    assert groups["X"] == groups["Y"] == {"X", "Y"}
    assert "AAPL" not in groups


def test_a_print_is_not_a_bar():
    """A close on volume 0 or none: AVB's two under a dead symbol. The
    writer and the gate read it the same way."""
    series = {"A": {"close": 1.0, "volume": 5}, "B": {"close": 1.0, "volume": 0},
              "C": {"close": 1.0, "volume": None}, "D": "junk"}
    assert tc._traded(series) == {"A"}
    assert [bf.real_bar(series[k]) for k in "ABCD"] == [True, False, False,
                                                        False]


# -- the writer, a rename on record ---------------------------------------------

@pytest.mark.parametrize("dry", [[], ["--dry-run"]], ids=["run", "dry-run"])
def test_the_new_symbol_is_refused_up_to_the_old_ones_last_week(
        monkeypatch, capsys, tmp_path, panel, dry):
    """The run that doubled EQR on a copy of the panel. The dry run, which
    is the workflow's default, answered "could be added" for those weeks
    and "dry-run OK"."""
    weekly = panel(renamed_panel())
    before = snapshot_of(weekly)
    no_provider(monkeypatch)

    code = run_main(monkeypatch, tmp_path, "--only", "VMRK", "--merge",
                    "--start", FIRST, "--end", VMRK_WEEKS[-1], *dry)

    assert code == 2
    assert snapshot_of(weekly) == before
    out = capsys.readouterr().out
    assert ("REFUSED, nothing downloaded and nothing written: this run "
            "would put one company in the panel under two symbols") in out
    assert "VMRK is EQR renamed. EQR has bars through 2026-08-14" in out
    assert "4 of the week(s) named, 2026-07-24..2026-08-14" in out
    assert "(--start 2026-08-21)" in out
    assert "dry-run OK" not in out
    # The plan no longer counts them as something a fetch could add: of the
    # eight weeks, two hold VMRK, four are refused, two are free.
    assert "could be added, if the provider has a bar: 2 pair(s)" in out


def test_a_week_that_holds_neither_symbol_is_refused_with_the_rest(
        monkeypatch, capsys, tmp_path, panel):
    """2024-08-09.json. The week holds no EQR bar to double, and a VMRK bar
    there would stand before all of EQR's weeks."""
    weekly = panel(renamed_panel())
    before = snapshot_of(weekly)
    no_provider(monkeypatch)

    code = run_main(monkeypatch, tmp_path, "--only", "VMRK", "--merge",
                    "--start", FIRST, "--end", FIRST)

    assert code == 2
    assert snapshot_of(weekly) == before
    out = capsys.readouterr().out
    assert "1 of the week(s) named, 2026-07-24." in out
    assert "in one that holds neither it would stand before EQR's weeks" in out


@pytest.mark.parametrize("dry", [[], ["--dry-run"]], ids=["run", "dry-run"])
def test_a_retired_symbol_is_never_merged(
        monkeypatch, capsys, tmp_path, panel, dry):
    """`--only EQR --merge` over 2026-08-21, as rehearsed: the provider's
    one EQR bar is Monday's, slice_week filed it under the Friday beside
    VMRK's own bar, the week's `missing` entry for EQR was struck, and two
    later weeks were given a new one."""
    weekly = panel(renamed_panel())
    before = snapshot_of(weekly)
    no_provider(monkeypatch)

    code = run_main(monkeypatch, tmp_path, "--only", "EQR", "--merge",
                    "--start", GAP_WEEKS[0], "--end", VMRK_WEEKS[-1], *dry)

    assert code == 2
    assert snapshot_of(weekly) == before
    out = capsys.readouterr().out
    assert ("EQR was renamed VMRK and is not merged into any week: 4 "
            "week(s) named, 2026-08-21..2026-09-11.") in out
    assert "dry-run OK" not in out


def test_a_retired_symbol_is_refused_where_the_new_one_has_no_bar_yet(
        monkeypatch, capsys, tmp_path, panel):
    """The weeks between a rename and the day the panel takes the new
    symbol. A rule that kept the old symbol only out of the new one's weeks
    let EQR's Monday bar into 2026-08-21 while VMRK began on 2026-09-25,
    and VMRK was then refused that week for good."""
    weekly = panel(renamed_panel())
    before = snapshot_of(weekly)
    no_provider(monkeypatch)

    code = run_main(monkeypatch, tmp_path, "--only", "EQR", "--merge",
                    "--start", GAP_WEEKS[0], "--end", GAP_WEEKS[0])

    assert code == 2
    assert snapshot_of(weekly) == before
    assert "EQR was renamed VMRK and is not merged into any week" in (
        capsys.readouterr().out)


def test_both_symbols_named_in_one_run_are_refused(
        monkeypatch, capsys, tmp_path, panel):
    """`--only EQR,VMRK` over the weeks between: neither is in them yet, and
    one call would have put Monday's EQR beside Friday's VMRK."""
    weekly = panel(renamed_panel())
    before = snapshot_of(weekly)
    no_provider(monkeypatch)

    code = run_main(monkeypatch, tmp_path, "--only", "EQR,VMRK", "--merge",
                    "--start", GAP_WEEKS[0], "--end", GAP_WEEKS[1])

    assert code == 2
    assert snapshot_of(weekly) == before, "VMRK is not merged either"
    assert "EQR was renamed VMRK and is not merged" in capsys.readouterr().out


def test_the_new_symbol_goes_into_the_weeks_after_the_old_ones_last(
        monkeypatch, capsys, tmp_path, panel):
    """The merge of 2026-10-06 itself: VMRK into the weeks it traded in,
    where the panel held no bar for the company. EQR's `missing` entries in
    those weeks are what a fetch saw, and stay."""
    weekly = panel(renamed_panel())
    provider(monkeypatch, {"VMRK": {GAP_WEEKS[0]: (66.0, 7_163_100),
                                    GAP_WEEKS[1]: (64.8, 4_749_500)}})

    code = run_main(monkeypatch, tmp_path, "--only", "VMRK", "--merge",
                    "--start", GAP_WEEKS[0], "--end", GAP_WEEKS[1])

    assert code == 0
    out = capsys.readouterr().out
    assert "REFUSED" not in out
    for name, bar in ((GAP_WEEKS[0], {"close": 66.0, "volume": 7_163_100}),
                      (GAP_WEEKS[1], {"close": 64.8, "volume": 4_749_500})):
        doc = json.loads((weekly / (name + ".json")).read_text("utf-8"))
        assert doc["series"]["VMRK"] == bar
        assert "EQR" not in doc["series"]
        assert [m["ticker"] for m in doc["missing"]] == ["EQR"]


def test_a_print_under_the_old_symbol_does_not_keep_the_new_one_out(
        monkeypatch, tmp_path, panel):
    """AVB's two prints are the pattern: a feed that still asks for a dead
    symbol can be handed a close on no volume in the weeks after the rename.
    That is not the old symbol's last bar, and those are the new one's
    weeks."""
    files = renamed_panel()
    for d in GAP_WEEKS:
        files[d + ".json"] = week(d, prints=["EQR"])
    weekly = panel(files)
    assert bf.symbol_spans(str(weekly), {"EQR"})["EQR"] == (
        day(EQR_WEEKS[0]), day(EQR_WEEKS[-1]))
    provider(monkeypatch, {"VMRK": {GAP_WEEKS[0]: (66.0, 7_163_100),
                                    GAP_WEEKS[1]: (64.8, 4_749_500)}})

    code = run_main(monkeypatch, tmp_path, "--only", "VMRK", "--merge",
                    "--start", GAP_WEEKS[0], "--end", GAP_WEEKS[1])

    assert code == 0
    for d in GAP_WEEKS:
        doc = json.loads((weekly / (d + ".json")).read_text("utf-8"))
        assert doc["series"]["VMRK"]["volume"] > 0
        assert doc["series"]["EQR"] == {"close": 65.9, "volume": 0}


def test_a_new_symbol_whose_old_one_the_panel_never_held_goes_everywhere(
        monkeypatch, tmp_path, panel):
    """BNY, MRSH and DOC. BK is in `missing` in every week and in `series`
    in none, so there is no bar to double and nothing to stand before."""
    weekly = panel({d + ".json": week(d, missing=["BK"]) for d in ALL_WEEKS})
    provider(monkeypatch, {"BNY": {d: (150.0 + i, 3_000_000 + i)
                                   for i, d in enumerate(ALL_WEEKS)}})

    code = run_main(monkeypatch, tmp_path, "--only", "BNY", "--merge",
                    "--start", ALL_WEEKS[0], "--end", ALL_WEEKS[-1])

    assert code == 0
    for d in ALL_WEEKS:
        doc = json.loads((weekly / (d + ".json")).read_text("utf-8"))
        assert "BNY" in doc["series"]
        assert [m["ticker"] for m in doc["missing"]] == ["BK"]


def test_the_old_symbol_of_a_name_the_panel_holds_throughout_is_refused(
        monkeypatch, capsys, tmp_path, panel):
    weekly = panel({d + ".json": week(d, extra=["BNY"], missing=["BK"])
                    for d in ALL_WEEKS})
    before = snapshot_of(weekly)
    no_provider(monkeypatch)

    code = run_main(monkeypatch, tmp_path, "--only", "BK", "--merge",
                    "--start", ALL_WEEKS[0], "--end", ALL_WEEKS[-1])

    assert code == 2
    assert snapshot_of(weekly) == before
    assert ("BK was renamed BNY and is not merged into any week: 8 week(s) "
            "named, 2026-07-24..2026-09-11.") in capsys.readouterr().out


def test_one_refused_name_stops_the_whole_run(
        monkeypatch, capsys, tmp_path, panel):
    """The command of the rehearsal named four tickers and one range. The
    three it could have merged are for a command that names only them:
    `--start` and `--end` are the only way to keep a name out of a week."""
    weekly = panel(renamed_panel())
    before = snapshot_of(weekly)
    no_provider(monkeypatch)

    code = run_main(monkeypatch, tmp_path, "--only", "PLTR,VMRK", "--merge",
                    "--start", EQR_WEEKS[0], "--end", EQR_WEEKS[-1])

    assert code == 2
    assert snapshot_of(weekly) == before, "PLTR is not merged either"
    assert "REFUSED, nothing downloaded and nothing written" in (
        capsys.readouterr().out)


@pytest.mark.parametrize("name, weeks", [("VMRK", VMRK_WEEKS),
                                         ("EQR", EQR_WEEKS)])
def test_a_bar_the_week_holds_is_left_alone_not_refused(
        monkeypatch, capsys, tmp_path, panel, name, weeks):
    """Either symbol over the weeks that already hold it is the run with
    nothing to add, as for any other name. The refusal is for a bar that
    would be added."""
    weekly = panel(renamed_panel())
    before = snapshot_of(weekly)
    no_provider(monkeypatch)

    code = run_main(monkeypatch, tmp_path, "--only", name, "--merge",
                    "--start", weeks[0], "--end", weeks[-1])

    assert code == 2
    assert snapshot_of(weekly) == before
    out = capsys.readouterr().out
    assert "NOTHING TO MERGE" in out
    assert "REFUSED" not in out


def test_the_spans_are_read_off_the_whole_panel_not_the_range(
        tmp_path, panel):
    """Whether VMRK may go into a week depends on EQR's weeks after it,
    which a run for that one week does not name."""
    weekly = panel(renamed_panel())
    spans = bf.symbol_spans(str(weekly), {"EQR", "VMRK", "BK"})
    assert spans == {"EQR": (day(EQR_WEEKS[0]), day(EQR_WEEKS[-1])),
                     "VMRK": (day(VMRK_WEEKS[0]), day(VMRK_WEEKS[-1]))}

    refused = bf.renamed_refusals(str(weekly), [day(FIRST)], ["VMRK"], {})
    assert refused == [("VMRK", "EQR", "earlier", day(EQR_WEEKS[-1]),
                        [day(FIRST)])]
    assert bf.renamed_refusals(str(weekly), [day(GAP_WEEKS[0])], ["VMRK"],
                               {}) == []
    assert bf.renamed_refusals(str(weekly), [day(GAP_WEEKS[0])], ["EQR"],
                               {}) == [("EQR", "VMRK", "retired", None,
                                        [day(GAP_WEEKS[0])])]
    assert bf.renamed_refusals(str(weekly), [day(FIRST)], ["AAPL"], {}) == []
    assert bf.renamed_refusals(str(weekly), [], ["VMRK"], {}) == []


def test_a_week_that_holds_the_name_is_not_among_the_refused(tmp_path, panel):
    """A panel that already holds VMRK in one of EQR's weeks, by some other
    hand. The bar is there and is left alone like any other; the gate is
    what speaks of it. The run is refused for the weeks it would add to."""
    weekly = panel(renamed_panel())
    on_file = [day(d) for d in [FIRST] + EQR_WEEKS]
    held = {"VMRK": [day(EQR_WEEKS[1])], "EQR": [day(d) for d in EQR_WEEKS]}

    assert bf.renamed_refusals(str(weekly), on_file, ["VMRK"], held) == [
        ("VMRK", "EQR", "earlier", day(EQR_WEEKS[-1]),
         [day(FIRST), day(EQR_WEEKS[0]), day(EQR_WEEKS[2])])]
    assert bf.renamed_refusals(str(weekly), on_file, ["EQR"], held) == [
        ("EQR", "VMRK", "retired", None, [day(FIRST)])]


def test_a_chain_is_refused_along_its_length(monkeypatch, tmp_path, panel):
    """A became B became C. C stays out of every week up to the last bar of
    either, and neither A nor B is merged."""
    monkeypatch.setattr(tickers, "RENAMED", {"AAA": "BBB", "BBB": "CCC"})
    w = ALL_WEEKS
    files = {w[0] + ".json": week(w[0], extra=["AAA"]),
             w[1] + ".json": week(w[1], extra=["AAA"]),
             w[2] + ".json": week(w[2], extra=["BBB"]),
             w[3] + ".json": week(w[3]),
             w[4] + ".json": week(w[4], extra=["CCC"])}
    weekly = panel(files)
    on_file = [day(d) for d in w[:5]]

    assert bf.renamed_refusals(str(weekly), on_file, ["CCC"], {}) == [
        ("CCC", "BBB", "earlier", day(w[2]), on_file[:3]),
        ("CCC", "AAA", "earlier", day(w[1]), on_file[:2])]
    assert bf.renamed_refusals(str(weekly), on_file, ["BBB"], {}) == [
        ("BBB", "CCC", "retired", None, on_file)]
    assert bf.renamed_refusals(str(weekly), on_file, ["AAA"], {}) == [
        ("AAA", "BBB", "retired", None, on_file)]
    assert bf.other_symbol_held("CCC", {"AAA": {"close": 1.0, "volume": 9}}
                                ) == "AAA"


def test_a_correction_is_not_read_for_the_spans(tmp_path, panel):
    """A correction is rebuilt from its base, and the base is what a merge
    writes into."""
    files = renamed_panel()
    files[GAP_WEEKS[0] + ".corrected.json"] = correction_of(
        week(GAP_WEEKS[0], extra=["EQR"]), GAP_WEEKS[0] + ".json")
    weekly = panel(files)
    assert bf.symbol_spans(str(weekly), {"EQR"})["EQR"][1] == day(
        EQR_WEEKS[-1])


def test_a_week_that_cannot_be_read_stops_a_run_that_depends_on_it(
        monkeypatch, capsys, tmp_path, panel):
    """The bound is read off every week on file. One that is not its week,
    outside the range the run names, could hide the old symbol's last bar."""
    weekly = panel(renamed_panel())
    (weekly / (EQR_WEEKS[1] + ".json")).write_text(
        json.dumps(week(EQR_WEEKS[0], extra=["EQR"])), encoding="utf-8")
    no_provider(monkeypatch)

    with pytest.raises(SystemExit) as stopped:
        run_main(monkeypatch, tmp_path, "--only", "VMRK", "--merge",
                 "--start", GAP_WEEKS[0], "--end", GAP_WEEKS[1])

    said = str(stopped.value)
    assert "2026-08-07.json has as_of '2026-07-31'" in said
    assert "what a merge may add is read off every week on file" in said
    assert "Nothing was written" in said


def test_something_that_is_not_a_weekly_file_is_stepped_over(tmp_path, panel):
    weekly = panel(renamed_panel())
    (weekly / "2026-09-18.json").mkdir()
    (weekly / "notes.json").write_text("{}", encoding="utf-8")
    (weekly / "README.md").write_text("x", encoding="utf-8")
    assert [f.isoformat() for f, _ in bf.panel_weeks(str(weekly))] == ALL_WEEKS


# -- the writer, when it is called for one week ---------------------------------

def test_a_week_is_never_given_the_company_twice(tmp_path, panel):
    """merge_into_existing, for a caller that does not come through main().
    The week has the company, so the other symbol is neither added nor
    listed in `missing`."""
    weekly = panel(renamed_panel())
    path = weekly / (EQR_WEEKS[-1] + ".json")
    committed = path.read_bytes()
    friday = day(EQR_WEEKS[-1])

    rec = bf.merge_into_existing(
        friday, ["VMRK"], {"VMRK": ([friday], [65.19], [7_322_800])},
        str(path))

    assert rec["renamed"] == [("VMRK", "EQR")]
    assert rec["added"] == [] and rec["changed"] is False
    assert path.read_bytes() == committed


@pytest.mark.parametrize("extra", [["VMRK"], []],
                         ids=["beside-the-new-one", "before-it-is-there"])
def test_a_retired_symbols_last_bar_is_not_filed_under_a_friday(
        tmp_path, panel, extra):
    """EQR's last session was Monday 2026-08-17. Whether or not the week
    holds VMRK yet, that bar is not the Friday's."""
    files = renamed_panel()
    files["2026-08-21.json"] = week("2026-08-21", extra=extra,
                                    missing=["EQR"])
    weekly = panel(files)
    path = weekly / "2026-08-21.json"
    committed = path.read_bytes()

    rec = bf.merge_into_existing(
        day("2026-08-21"), ["EQR"],
        {"EQR": ([day("2026-08-17")], [63.66], [7_449_691])}, str(path))

    assert rec["renamed"] == [("EQR", "VMRK")]
    assert rec["added"] == [] and rec["absent"] == []
    assert path.read_bytes() == committed, (
        "no bar, and the `missing` entry a fetch wrote is still there")


def test_a_run_that_reached_a_week_it_should_not_exits_2(
        monkeypatch, capsys, tmp_path, panel):
    """main() refuses before it reaches a week. If that ever fails to, the
    week still does not take the bar, and the run does not read as done."""
    weekly = panel(renamed_panel())
    before = snapshot_of(weekly)
    monkeypatch.setattr(bf, "renamed_refusals", lambda *args: [])
    provider(monkeypatch, {"VMRK": {EQR_WEEKS[-1]: (65.19, 5_000_100)}})

    code = run_main(monkeypatch, tmp_path, "--only", "VMRK", "--merge",
                    "--start", EQR_WEEKS[-1], "--end", EQR_WEEKS[-1])

    assert code == 2
    assert snapshot_of(weekly) == before
    assert ("2026-08-14: VMRK not added, it is one company with EQR "
            "(RENAMED)") in capsys.readouterr().out


# -- the writer, a rename nobody recorded ----------------------------------------

VOLUMES = [1_442_800, 1_099_300, 2_136_000, 7_322_800]
OLD_WEEKS = ["2026-07-24", "2026-07-31", "2026-08-07", "2026-08-14"]


def unrecorded_panel(volumes=VOLUMES, extra=()):
    """OLDCO in four weeks, each with its own volume, as a real name has.
    `extra` names are given OLDCO's bar as well: weeks doubled before."""
    files = {}
    for i, (d, volume) in enumerate(zip(OLD_WEEKS, volumes)):
        doc = week(d, extra=["OLDCO"])
        doc["series"]["OLDCO"] = {"close": 65.0, "volume": volume}
        for name, held_in in extra:
            if i in held_in:
                doc["series"][name] = {"close": 64.2, "volume": volume}
        files[d + ".json"] = doc
    return files


def same_bars(volumes, name="NEWCO"):
    """A name as the provider serves it: OLDCO's sessions, a close adjusted
    to a later date, and the volumes given."""
    return {name: {d: (64.2, volume)
                   for d, volume in zip(OLD_WEEKS, volumes)
                   if volume != "no bar"}}


def test_an_unrecorded_rename_is_refused_on_its_volumes(
        monkeypatch, capsys, tmp_path, panel):
    """No map names the pair. The bars do: a close is adjusted to its fetch
    date, a volume is not, and two companies do not trade the same number
    of shares week after week."""
    weekly = panel(unrecorded_panel())
    before = snapshot_of(weekly)
    provider(monkeypatch, same_bars(VOLUMES))

    code = run_main(monkeypatch, tmp_path, "--only", "NEWCO", "--merge",
                    "--start", OLD_WEEKS[0], "--end", OLD_WEEKS[-1])

    assert code == 2
    assert snapshot_of(weekly) == before, "refused before the first write"
    out = capsys.readouterr().out
    assert ("REFUSED, nothing written: the bars this run would add are "
            "already in the panel under another symbol") in out
    assert ("NEWCO has the same non-zero volume as OLDCO in 4 week(s) this "
            "run would add, 2026-07-24..2026-08-14.") in out
    assert "record it in RENAMED" in out and "RENAMED_SYMBOLS" in out
    assert "merged +" not in out


def test_three_weeks_are_the_threshold(monkeypatch, tmp_path, panel):
    assert bf.SAME_BARS_WEEKS == 3
    weekly = panel(unrecorded_panel())
    before = snapshot_of(weekly)
    provider(monkeypatch, same_bars(VOLUMES[:3] + [9_999_900]))

    code = run_main(monkeypatch, tmp_path, "--only", "NEWCO", "--merge",
                    "--start", OLD_WEEKS[0], "--end", OLD_WEEKS[-1])

    assert code == 2
    assert snapshot_of(weekly) == before


def test_two_weeks_of_one_volume_are_a_coincidence(
        monkeypatch, capsys, tmp_path, panel):
    """On the panel of 2026-10-06, 59 pairs of different tickers share a
    volume in a week, each in one week only. Two is still short of the
    threshold, and a name that is not refused is merged."""
    weekly = panel(unrecorded_panel())
    provider(monkeypatch, same_bars(VOLUMES[:2] + [5_000_100, 6_000_200]))

    code = run_main(monkeypatch, tmp_path, "--only", "NEWCO", "--merge",
                    "--start", OLD_WEEKS[0], "--end", OLD_WEEKS[-1])

    assert code == 0
    assert "REFUSED" not in capsys.readouterr().out
    for d in OLD_WEEKS:
        doc = json.loads((weekly / (d + ".json")).read_text("utf-8"))
        assert {"OLDCO", "NEWCO"} <= set(doc["series"])


def test_the_count_is_one_other_keys_not_the_names(
        monkeypatch, capsys, tmp_path, panel):
    """A name that meets three different tickers once each has met three
    coincidences. On the real panel CI does so in four weeks and ELV in
    three, and counted by name both would be refused."""
    files = {}
    others = ["AAPL", "JNJ", "XOM", "AAPL"]
    for d, other, volume in zip(OLD_WEEKS, others, VOLUMES):
        doc = week(d)
        for i, name in enumerate(STOCKS):
            doc["series"][name] = {"close": 100.0, "volume": 900_000 + i}
        doc["series"][other] = {"close": 100.0, "volume": volume}
        files[d + ".json"] = doc
    panel(files)
    provider(monkeypatch, same_bars(VOLUMES))

    code = run_main(monkeypatch, tmp_path, "--only", "NEWCO", "--merge",
                    "--start", OLD_WEEKS[0], "--end", OLD_WEEKS[-1])

    assert code == 0, "AAPL twice, JNJ once, XOM once: no pair reaches three"
    assert "REFUSED" not in capsys.readouterr().out


def test_weeks_the_pair_already_shares_are_counted(
        monkeypatch, capsys, tmp_path, panel):
    """A doubling brought in two weeks at a time. The first two runs are
    under the threshold; the third finds two weeks of the pair on file,
    outside the week it names, and one more would make three."""
    weekly = panel(unrecorded_panel(extra=[("NEWCO", (0, 1))]))
    before = snapshot_of(weekly)
    provider(monkeypatch, same_bars(VOLUMES))

    code = run_main(monkeypatch, tmp_path, "--only", "NEWCO", "--merge",
                    "--start", OLD_WEEKS[2], "--end", OLD_WEEKS[2])

    assert code == 2
    assert snapshot_of(weekly) == before
    assert ("NEWCO has the same non-zero volume as OLDCO in 1 week(s) this "
            "run would add, 2026-08-07, and in 2 the panel already holds, "
            "2026-07-24..2026-07-31.") in capsys.readouterr().out


def test_two_names_of_one_run_are_held_against_each_other(
        monkeypatch, capsys, tmp_path, panel):
    """Neither is in the panel, so neither can be compared with it. They are
    each other's bars all the same."""
    weekly = panel({d + ".json": week(d) for d in OLD_WEEKS})
    before = snapshot_of(weekly)
    bars = same_bars(VOLUMES, name="NEWCO")
    bars.update(same_bars(VOLUMES, name="ALIAS"))
    provider(monkeypatch, bars)

    code = run_main(monkeypatch, tmp_path, "--only", "NEWCO,ALIAS", "--merge",
                    "--start", OLD_WEEKS[0], "--end", OLD_WEEKS[-1])

    assert code == 2
    assert snapshot_of(weekly) == before
    assert ("ALIAS has the same non-zero volume as NEWCO in 4 week(s) this "
            "run would add") in capsys.readouterr().out


def test_no_volume_proves_nothing(monkeypatch, capsys, tmp_path, panel):
    """A bar with volume 0 or none has no witness. AVB's two prints under a
    dead symbol are such bars, and so is an index's. Three weeks of 0 are
    past the threshold and still say nothing."""
    weekly = panel(unrecorded_panel(volumes=[0, 0, 0, None]))
    provider(monkeypatch, same_bars([0, 0, 0, None]))

    code = run_main(monkeypatch, tmp_path, "--only", "NEWCO", "--merge",
                    "--start", OLD_WEEKS[0], "--end", OLD_WEEKS[-1])

    assert code == 0
    assert "REFUSED" not in capsys.readouterr().out
    assert bf.same_bars_refusals(
        str(weekly), [day(d) for d in OLD_WEEKS], ["NEWCO"], {}) == []


def test_the_volume_rule_names_the_pair_and_its_weeks(tmp_path, panel):
    weekly = panel(unrecorded_panel())
    fridays = [day(d) for d in OLD_WEEKS]
    history = {"NEWCO": (fridays, [64.2] * 4, VOLUMES),
               "PLTR": (fridays, [50.0] * 4, [123_456] * 4)}

    assert bf.same_bars_refusals(str(weekly), fridays, ["NEWCO", "PLTR"],
                                 history) == [("NEWCO", "OLDCO", fridays, [])]
    # A name every week already holds adds nothing, whatever it shares.
    assert bf.same_bars_refusals(str(weekly), fridays, ["OLDCO"],
                                 {"OLDCO": (fridays, [65.0] * 4, VOLUMES)}
                                 ) == []


def test_the_volume_rule_reads_a_holiday_week_by_its_session(
        tmp_path, panel):
    """The Friday was a holiday and both bars are Thursday's. slice_week
    takes the last bar of the week, which is the session the file holds."""
    weekly = panel(unrecorded_panel())
    fridays = [day(d) for d in OLD_WEEKS]
    sessions = fridays[:3] + [day("2026-08-13")]
    history = {"NEWCO": (sessions, [64.2] * 4, VOLUMES)}

    assert bf.same_bars_refusals(str(weekly), fridays, ["NEWCO"], history) \
        == [("NEWCO", "OLDCO", fridays, [])]


def test_the_volume_rule_steps_over_a_friday_with_no_file(tmp_path, panel):
    weekly = panel(unrecorded_panel())
    fridays = [day(d) for d in OLD_WEEKS] + [day("2026-08-21")]
    history = {"NEWCO": (fridays, [64.2] * 5, VOLUMES + [3_000_300])}

    assert bf.same_bars_refusals(str(weekly), fridays, ["NEWCO"], history) \
        == [("NEWCO", "OLDCO", fridays[:4], [])]


def test_the_volume_rule_does_not_stop_on_a_week_outside_the_run(
        tmp_path, panel):
    """It reads the whole panel for the weeks a pair already shares. A week
    it cannot read, outside the run, has nothing to add to the count and is
    the feed gate's to report. Inside the run it stops the merge anyway."""
    weekly = panel(unrecorded_panel())
    (weekly / "2026-06-05.json").write_text("{ not json", encoding="utf-8")
    fridays = [day(d) for d in OLD_WEEKS]
    history = {"NEWCO": (fridays, [64.2] * 4, VOLUMES)}

    assert bf.same_bars_refusals(str(weekly), fridays, ["NEWCO"], history) \
        == [("NEWCO", "OLDCO", fridays, [])]
    with pytest.raises(SystemExit):
        bf.same_bars_refusals(str(weekly), fridays + [day("2026-06-05")],
                              ["NEWCO"], history)


# -- the gate ---------------------------------------------------------------------

def gate(repo):
    rep = tc.Report()
    tc.check_renamed_symbols(repo, rep)
    return rep


def absence(repo):
    rep = tc.Report()
    tc.check_silent_absence(repo, rep)
    return [line for line in rep.lines if line.startswith("WARN")]


def doubled_panel(**overrides):
    doubled = EQR_WEEKS[-1]
    files = renamed_panel(**{doubled + ".json": week(doubled,
                                                     extra=["EQR", "VMRK"])})
    files.update(overrides)
    return files


def test_an_ordinary_panel_passes_in_one_line(tmp_path, panel):
    panel(renamed_panel())
    rep = gate(tmp_path)
    assert rep.counts == {"OK": 1, "WARN": 0, "FAIL": 0, "SKIP": 0}
    assert rep.lines == [
        "OK: feed: none of 8 weekly file(s) holds a renamed company under "
        "two symbols, and none of the 4 rename(s) on record has its symbols "
        "interleaved"]


def test_a_week_that_holds_both_symbols_fails_the_feed_gate(tmp_path, panel):
    """However it came to: this is the check for a writer that is not
    scripts/backfill_weekly.py."""
    panel(doubled_panel())
    rep = gate(tmp_path)

    assert rep.counts == {"OK": 0, "WARN": 0, "FAIL": 1, "SKIP": 0}
    line = rep.lines[0]
    assert line.startswith(
        "FAIL: feed: 1 weekly file(s) hold EQR and VMRK in `series`: one "
        "company under two symbols (EQR -> VMRK). Do not delete a bar, do "
        "not edit a file and do not push one. Look at main first, file by "
        "file.")
    assert "DATA_FEED.md sec.1, \"One company, one symbol a week\"" in line
    assert line.endswith("The files, each one whose `series` has both: "
                         "2026-08-14.json.")


def test_the_message_says_what_not_to_do_before_what_to_do(tmp_path, panel):
    """It is read in order by an agent whose other instruction is that any
    FAIL is fixed before pushing, and a bar cannot be fixed out of a file.
    The file may be on main with both symbols, on main with one, or not on
    main at all, and each has its sentence. On the runner nothing is put
    back one file at a time: that copy is synced whole."""
    panel(doubled_panel())
    line = gate(tmp_path).lines[0]
    order = [line.index(part) for part in (
        "Do not delete a bar",
        "Look at main first",
        "Where main's copy holds both symbols too",
        "the owner decides",
        "Where main's copy holds one",
        "discard the uncommitted change to that file alone",
        "on the weekly job's runner, stop and report",
        "Where main has no such file",
        "stop and report, because the feed is naming both symbols")]
    assert order == sorted(order)
    for wrong in ("remove the", "delete the file", "add it to `missing`",
                  "write the week again", "put main's copy back"):
        assert wrong not in line


def test_a_correction_is_judged_under_its_own_name(tmp_path, panel):
    """Readers prefer it, and it is a full copy: a doubled base rebuilt into
    its correction is two files that hold both."""
    doubled = EQR_WEEKS[-1]
    files = doubled_panel()
    files[doubled + ".corrected.json"] = correction_of(
        files[doubled + ".json"], doubled + ".json")
    panel(files)

    rep = gate(tmp_path)
    assert rep.counts["FAIL"] == 1
    assert "2 weekly file(s) hold EQR and VMRK" in rep.lines[0]
    assert rep.lines[0].endswith(
        "2026-08-14.corrected.json, 2026-08-14.json.")


def test_one_line_a_company_however_many_weeks(tmp_path, panel):
    """On the copy of 2026-10-06 it was 105 files. The reader needs the
    first sentence once, and two companies are two lines."""
    panel({d + ".json": week(d, extra=["EQR", "VMRK", "BK", "BNY"])
           for d in ALL_WEEKS})

    rep = gate(tmp_path)

    assert rep.counts == {"OK": 0, "WARN": 0, "FAIL": 2, "SKIP": 0}
    assert rep.lines[0].startswith(
        "FAIL: feed: 8 weekly file(s) hold BK and BNY in `series`: one "
        "company under two symbols (BK -> BNY).")
    assert rep.lines[1].startswith(
        "FAIL: feed: 8 weekly file(s) hold EQR and VMRK in `series`: one "
        "company under two symbols (EQR -> VMRK).")
    assert rep.lines[1].endswith(
        "2026-07-24.json, 2026-07-31.json, 2026-08-07.json, "
        "2026-08-14.json, 2026-08-21.json, 2026-08-28.json, ... and 2 more.")


def test_a_print_beside_a_bar_is_not_the_company_twice(tmp_path, panel):
    """VMRK's bar in 2026-08-21.json stands beside AVB's print on volume 0.
    For a rename on record the same: the print is a defect of its own, and
    the week holds the company once."""
    files = renamed_panel()
    for d in GAP_WEEKS:
        files[d + ".json"] = week(d, extra=["VMRK"], prints=["EQR"])
    panel(files)
    assert gate(tmp_path).counts == {"OK": 1, "WARN": 0, "FAIL": 0, "SKIP": 0}


def test_symbols_that_interleave_are_warned_about_not_failed(tmp_path, panel):
    """A VMRK bar in the first week, before all of EQR's. No week holds
    both, so nothing is doubled and nothing can mend it: a committed file
    is not edited. Until 2026-10-06 the only word on it was the "name left
    out" warning, which answered with the merge that doubles 105 weeks."""
    panel(renamed_panel(**{FIRST + ".json": week(FIRST, extra=["VMRK"],
                                                 missing=["EQR"])}))
    rep = gate(tmp_path)

    assert rep.counts == {"OK": 0, "WARN": 1, "FAIL": 0, "SKIP": 0}
    line = rep.lines[0]
    assert line.startswith(
        "WARN: feed: VMRK has a bar in 1 week(s) not after EQR's last, "
        "2026-08-14: 2026-07-24.json. EQR was renamed VMRK")
    assert ("Do not merge VMRK into the weeks between, and do not merge EQR "
            "at all.") in line
    assert "--only" not in line, "it prints no command"


def test_a_doubled_week_is_the_failure_and_not_also_the_warning(
        tmp_path, panel):
    panel(doubled_panel())
    assert gate(tmp_path).counts == {"OK": 0, "WARN": 0, "FAIL": 1, "SKIP": 0}


def test_the_spans_behind_the_warning_are_the_bases(tmp_path, panel):
    """A correction that still carries a bar its base never had is the
    correction trap, and the feed gate's to find. It does not move a span."""
    files = renamed_panel()
    files[GAP_WEEKS[1] + ".corrected.json"] = correction_of(
        week(GAP_WEEKS[1], extra=["EQR"]), GAP_WEEKS[1] + ".json")
    files[GAP_WEEKS[0] + ".json"] = week(GAP_WEEKS[0], extra=["VMRK"],
                                         missing=["EQR"])
    panel(files)
    assert gate(tmp_path).counts == {"OK": 1, "WARN": 0, "FAIL": 0, "SKIP": 0}


def test_a_chain_interleaves_along_its_length(monkeypatch, tmp_path, panel):
    monkeypatch.setattr(tc, "RENAMED_SYMBOLS", {"AAA": "BBB", "BBB": "CCC"})
    w = ALL_WEEKS
    panel({w[0] + ".json": week(w[0], extra=["CCC"]),
           w[1] + ".json": week(w[1], extra=["AAA"]),
           w[2] + ".json": week(w[2], extra=["CCC"])})
    rep = gate(tmp_path)
    assert rep.counts == {"OK": 0, "WARN": 1, "FAIL": 0, "SKIP": 0}
    assert "CCC has a bar in 1 week(s) not after AAA's last" in rep.lines[0]


def test_an_old_symbol_in_missing_beside_the_new_ones_bar_is_no_failure(
        tmp_path, panel):
    """BK, MMC and PEAK in 111 weeks of the real panel, and EQR in five. A
    `missing` entry is a symbol that was asked for and not served."""
    panel({d + ".json": week(d, extra=["BNY", "VMRK"], missing=["BK", "EQR"])
           for d in ALL_WEEKS})
    assert gate(tmp_path).counts == {"OK": 1, "WARN": 0, "FAIL": 0, "SKIP": 0}


def test_a_file_the_feed_gate_refuses_is_left_to_it(tmp_path, panel):
    weekly = panel(renamed_panel())
    (weekly / (EQR_WEEKS[0] + ".json")).write_text("{ not json",
                                                   encoding="utf-8")
    (weekly / (EQR_WEEKS[1] + ".json")).write_text(
        json.dumps({"as_of": EQR_WEEKS[1], "series": []}), encoding="utf-8")
    rep = gate(tmp_path)
    assert rep.counts["FAIL"] == 0
    assert "none of 6 weekly file(s)" in rep.lines[0]


def test_a_tree_with_no_weekly_files_is_none_of_its_business(tmp_path):
    assert gate(tmp_path).lines == []
    (tmp_path / "data" / "weekly").mkdir(parents=True)
    assert gate(tmp_path).lines == []


def test_the_feed_gate_runs_it_and_exits_1(tmp_path, panel):
    """The backfill workflow runs --feed ahead of its commit step, and CI
    runs it on the pull request: that is where a doubled week is stopped."""
    panel(doubled_panel())
    r = subprocess.run([sys.executable, str(SCRIPTS / "truth_check.py"),
                        "--repo", str(tmp_path), "--feed",
                        "--today", "2026-09-12"],
                       capture_output=True, text=True)
    assert r.returncode == 1, r.stdout
    assert "FAIL: feed: 1 weekly file(s) hold EQR and VMRK" in r.stdout


def test_symbols_that_interleave_do_not_fail_the_feed_gate(tmp_path, panel):
    """It is a warning wherever --feed runs: CI, the daily job, the backfill
    workflow and the weekly job's gate print it and go on. The panel is the
    real one's shape with one VMRK bar put into the first week, which drew
    105 lines and as many --merge commands from the gate before."""
    files = renamed_panel(**{FIRST + ".json": week(FIRST, extra=["VMRK"],
                                                   missing=["EQR"])})
    for d in GAP_WEEKS:
        files[d + ".json"] = week(d, extra=["VMRK"], missing=["EQR"])
    panel(files)
    r = subprocess.run([sys.executable, str(SCRIPTS / "truth_check.py"),
                        "--repo", str(tmp_path), "--feed",
                        "--today", "2026-09-12"],
                       capture_output=True, text=True)
    assert "WARN: feed: VMRK has a bar in 1 week(s) not after EQR's last" \
        in r.stdout
    assert "hold EQR and VMRK" not in r.stdout
    assert "--only VMRK --merge" not in r.stdout
    assert "has neither a bar nor a `missing` entry" not in r.stdout


# -- the warning that printed the command -----------------------------------------

def test_a_week_is_not_asked_for_a_symbol_whose_company_it_holds(
        tmp_path, panel):
    """A VMRK bar in the first week, with EQR's weeks after it and VMRK's
    after those. Each of EQR's weeks was named as lacking VMRK, with the
    --merge command that doubles it: 105 of them on a copy of the real
    panel."""
    first = week(FIRST, extra=["VMRK"], missing=["EQR"])
    panel(renamed_panel(**{FIRST + ".json": first}))

    found = absence(tmp_path)

    named = sorted(line.split(" has neither")[0] for line in found)
    assert named == ["WARN: feed: %s.json" % d for d in GAP_WEEKS], (
        "the two weeks that hold neither symbol are still told so")
    assert not any(d in line for line in found for d in EQR_WEEKS)


def test_a_week_that_holds_neither_symbol_is_still_asked(tmp_path, panel):
    """The rule excuses a week that has the company, not the name."""
    files = renamed_panel()
    files[GAP_WEEKS[0] + ".json"] = week(GAP_WEEKS[0], extra=["VMRK"])
    files[GAP_WEEKS[1] + ".json"] = week(GAP_WEEKS[1])
    panel(files)

    found = absence(tmp_path)

    assert len(found) == 1
    assert "2026-08-28.json has neither a bar nor a `missing` entry for 1 " \
           "name(s): VMRK." in found[0]
    assert "--only VMRK --merge" in found[0]


def test_a_print_does_not_hold_the_week_for_the_company(tmp_path, panel):
    """EQR's weeks hold only a close on no volume. That is not the company's
    bar, and the week is asked for the symbol the bars before and after it
    carry."""
    files = renamed_panel(**{FIRST + ".json": week(FIRST, extra=["VMRK"])})
    for d in EQR_WEEKS + GAP_WEEKS:
        files[d + ".json"] = week(d, prints=["EQR"])
    panel(files)

    found = absence(tmp_path)

    assert len(found) == len(EQR_WEEKS + GAP_WEEKS)
    assert all("name(s): VMRK." in line for line in found)


def test_the_week_is_read_as_readers_see_it(tmp_path, panel):
    """A correction in place of its base, as everywhere in that check. One
    that drops the old symbol's bar leaves a week without the company."""
    first = week(FIRST, extra=["VMRK"], missing=["EQR"])
    files = renamed_panel(**{FIRST + ".json": first})
    dropped = EQR_WEEKS[1]
    files[dropped + ".corrected.json"] = correction_of(week(dropped),
                                                       dropped + ".json")
    panel(files)

    found = absence(tmp_path)

    assert any(line.startswith("WARN: feed: %s.corrected.json has neither"
                               % dropped) and "VMRK" in line
               for line in found)
    assert not any(EQR_WEEKS[0] in line or EQR_WEEKS[2] in line
                   for line in found)


def test_the_panel_as_the_merge_left_it_is_quiet(tmp_path, panel):
    """EQR through its last week, VMRK from its first, and the weeks between
    listing EQR in `missing`: nothing is asked for."""
    files = renamed_panel()
    for d in GAP_WEEKS:
        files[d + ".json"] = week(d, extra=["VMRK"], missing=["EQR"])
    panel(files)
    assert absence(tmp_path) == []
    assert gate(tmp_path).counts == {"OK": 1, "WARN": 0, "FAIL": 0, "SKIP": 0}


# -- the newest week, in the week a rename is recorded -----------------------------

def newest_week(names, missing=(), prints=()):
    doc = weekly_doc("2026-10-09", sorted(names),
                     fetched_at="2026-10-10T13:20:00Z")
    for name in prints:
        doc["series"][name] = {"close": 65.9, "volume": 0}
    doc["missing"] = [{"ticker": t, "reason": "no bar dated 2026-10-09"}
                      for t in missing]
    return doc


def feed_names(repo):
    rep = tc.Report()
    tc.check_feed_names(repo, rep)
    return rep


def test_a_week_that_holds_the_old_symbol_accounts_for_the_new_one():
    doc = newest_week(["AAPL", "EQR"])
    assert tc._unaccounted(doc, ["AAPL", "VMRK"]) == set()
    assert tc._unaccounted(newest_week(["AAPL"]), ["AAPL", "VMRK"]) == {"VMRK"}
    assert tc._unaccounted(newest_week(["AAPL"], missing=["EQR"]),
                           ["AAPL", "VMRK"]) == {"VMRK"}, (
        "the old symbol asked for and not served is not the company's bar")
    assert tc._unaccounted(newest_week(["AAPL"], prints=["EQR"]),
                           ["AAPL", "VMRK"]) == {"VMRK"}, (
        "nor is a print on no volume")
    assert tc._unaccounted(newest_week(["AAPL"]), ["AAPL", "MSFT"]) == {"MSFT"}


def test_the_week_a_rename_is_recorded_in_does_not_fail_the_gate(
        monkeypatch, capsys, tmp_path, panel):
    """The feed takes the new symbol on a weekday. The newest file was
    written the Saturday before, by a writer that was asked for the old
    one, and holds its bar. The gate's cure for a name the newest week
    lacks is a merge, and the merge is the one that is refused: the same
    bar a second time. Without the excuse --feed and --config fail until
    the next Saturday, and the daily job commits nothing meanwhile."""
    names = [n for n in tc.EQUITY_UNIVERSE if n != "VMRK"] + ["EQR"]
    weekly = panel({"2026-10-02.json": weekly_doc(
                        "2026-10-02", sorted(names),
                        fetched_at="2026-10-03T13:20:00Z"),
                    "2026-10-09.json": newest_week(names)})

    rep = feed_names(tmp_path)
    assert rep.counts == {"OK": 1, "WARN": 0, "FAIL": 0, "SKIP": 0}, rep.lines

    before = snapshot_of(weekly)
    no_provider(monkeypatch)
    code = run_main(monkeypatch, tmp_path, "--only", "VMRK", "--merge",
                    "--start", "2026-10-09", "--end", "2026-10-09")
    assert code == 2 and snapshot_of(weekly) == before
    assert "VMRK is EQR renamed. EQR has bars through 2026-10-09" in (
        capsys.readouterr().out)


def test_a_new_symbol_the_newest_week_holds_under_no_symbol_is_still_asked(
        tmp_path, panel):
    """The rename took effect before the Friday: the old symbol has no bar
    for the week and the new one was not asked for. That week does lack the
    company, the gate says so, and the merge is free to add it."""
    names = [n for n in tc.EQUITY_UNIVERSE if n != "VMRK"]
    panel({"2026-10-09.json": newest_week(names, missing=["EQR"])})

    rep = feed_names(tmp_path)

    assert rep.counts["FAIL"] == 1, rep.lines
    assert "has no bar and no `missing` entry for ['VMRK']" in rep.lines[0]
