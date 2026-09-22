#!/usr/bin/env python3
"""Pass 9 -- the universe: the 111, the feed, and the S&P 500.

Does the team have enough to choose from? The mechanical team (the Ophelia
and Cecil engines from a baseline replay, Marky's channel five) is replayed on
the 96 history weeks and the nine Council weeks over four universes:

  the 277      the frozen engine list Passes 1-8 used (reference)
  the 111      the owner's Council list, its 109 stocks (the engines do not
               score BTC or GLD)
  the feed     the 318 stocks in the price feed: the 274 the engines scan live
               plus the 44 focus names they never see
  the S&P 500  today's 503 constituents (lab/universe_sp500_2026-09-22.csv,
               from Wikipedia, fetched 2026-09-22 06:48 ET). Survivorship
               bias: names are in it because they rose into it, so its
               absolute returns flatter; within-universe comparisons only.

Books per universe: each chair's five, and three chairs (a third each), scored
Monday open to Friday close against random books of the same weights from the
week's tradeable names in the SAME universe (production's earnings blackout),
clipped +/-20% primary, raw beside. Per universe and week, also the
equal-weighted tradeable universe against SPY (the base rate; hindsight-laden
on the curated lists) and the cross-sectional SD of clipped returns
(dispersion, the room a screen has to work in).

Sectors for Ophelia's rotation: the engines' SECTOR_MAP first; a name it
lacks takes the Council CSV's or the S&P table's GICS sector folded onto the
engines' eight buckets (proposal A of 2026-09-21), in the lab only.

Registered in lab/README.md before any number was computed.

    python lab/pass9_universe.py           # the pass
    python lab/pass9_universe.py smoke     # three weeks, the 111 only, to a scratch file
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass7_combos as p7  # noqa: E402

SP500_CSV = lab.LAB / "universe_sp500_2026-09-22.csv"
CHAIRS = ("Ophelia", "Cecil", "Marky")
BOOKS = ("Ophelia", "Cecil", "Marky", "Three chairs")
REFERENCE = "the 111"
WIDER = ("the feed", "the S&P 500")
FOLD = {  # GICS (Council CSV, S&P table) -> the engines' eight buckets
    "Communication Services": "Technology", "Information Technology": "Technology", "Technology": "Technology",
    "Consumer Discretionary": "Consumer", "Consumer Staples": "Consumer",
    "Materials": "Energy", "Energy": "Energy", "Financials": "Financials",
    "Health Care": "Healthcare", "Healthcare": "Healthcare", "Industrials": "Industrials",
    "Real Estate": "Real Estate", "Utilities": "Utilities", "Macro Assets": "Macro Assets",
}


def sp500():
    with open(SP500_CSV, encoding="ascii") as fh:
        rows = [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))]
    return {r["ticker"]: r["gics_sector"] for r in rows}


def universes():
    from scan_pipeline.config.tickers import BACKFILL_44_TICKERS, COUNCIL_SECTORS, COUNCIL_WATCHLIST, STOCK_UNIVERSE
    from scan_pipeline.utils import data_utils
    sp = sp500()
    for t, s in list(COUNCIL_SECTORS.items()) + list(sp.items()):
        data_utils.SECTOR_MAP.setdefault(t, FOLD[s])        # the lab's fold; production is untouched
    return {
        "the 277": lab.frozen_universe(),
        REFERENCE: [t for t in COUNCIL_WATCHLIST if t not in ("BTC", "GLD")],
        "the feed": sorted(set(STOCK_UNIVERSE) | set(BACKFILL_44_TICKERS)),
        "the S&P 500": sorted(sp),
    }


def _last_friday():
    today = date.today()
    return (today - timedelta(days=(today.weekday() - 4) % 7 or 7)).strftime("%Y-%m-%d")


def week_books(names, raw, adj, cal, W, proposals):
    """One week on one universe: the tradeable pool, the chairs' fives, the
    books, the base rate and the dispersion."""
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    from scan_pipeline.utils.data_utils import EARNINGS_BLACKOUT_TRADING_DAYS
    short = {t: _aggregate_weekly(raw[t].before(W, lab.LOOKBACK_DAYS)) for t in names if t in raw}
    eligible = [t for t in names if len(short.get(t, [])) >= lab.MIN_WEEKS]
    F = _aggregate_weekly(raw["SPY"].before(W, lab.LOOKBACK_DAYS))[-1].date
    tradeable = []
    for t in eligible:
        nxt = lab._next_report(cal.get(t), F)
        etd = _business_days_between(F, nxt) if nxt else None
        if etd is None or not 0 <= etd <= EARNINGS_BLACKOUT_TRADING_DAYS:
            tradeable.append(t)
    tset = set(tradeable)
    fives = {"Ophelia": [t for t in proposals["Ophelia"] if t in tset][:p7.TOP],
             "Cecil": [t for t in proposals["Cecil"] if t in tset][:p7.TOP],
             "Marky": p7.channel_ranking(raw, eligible, W, tset)[:p7.TOP]}
    books = {c: p7.equal(fives[c]) for c in CHAIRS}
    books["Three chairs"] = p7.slices([fives[c] for c in CHAIRS])
    rets = {t: adj[t].week_return(W) for t in tradeable if t in adj}
    rets = {t: r for t, r in rets.items() if r is not None}
    clipped = [p7._clip(r) for r in rets.values()]
    return books, tradeable, {"tradeable": len(tradeable), "ew_raw": statistics.fmean(rets.values()),
                              "ew_clipped": statistics.fmean(clipped), "dispersion": statistics.pstdev(clipped)}


def replay(uname, names, weeks, start, cal, raw, adj, tag):
    rows = lab.run(verbose=False, knobs=lab.VARIANTS3["base"], weeks=weeks, start=start, earnings=cal, names=names)
    proposals = {r["monday"]: r["proposals"] for r in rows}
    out = []
    for label, W, _ in weeks:
        books, tradeable, base = week_books(names, raw, adj, cal, W, proposals[W])
        spy = adj["SPY"].week_return(W) or 0.0
        out.append({"week": label, "spy": spy, "base": dict(base, vs_spy_raw=base["ew_raw"] - spy,
                                                              vs_spy_clipped=base["ew_clipped"] - p7._clip(spy)),
                    "books": p7.score_week(books, adj, W, tradeable, f"p9-{uname}-{tag}")})
    return out


def summarize(rows):
    s = {}
    for n in BOOKS:
        rs = [r["books"][n] for r in rows if n in r["books"]]
        if not rs:
            continue
        half = len(rs) // 2
        e = [x["clipped"]["edge"] for x in rs]
        ret = [x["raw"]["ret"] for x in rs]
        s[n] = {"weeks": len(rs), "edge": statistics.fmean(e), "t": lab._tstat(e),
                "ahead": sum(1 for x in e if x > 0),
                "halves": [statistics.fmean(e[:half]), statistics.fmean(e[half:])] if half else None,
                "raw_edge": statistics.fmean(x["raw"]["edge"] for x in rs),
                "mean_ret": statistics.fmean(ret), "sd": statistics.pstdev(ret), "max_dd": lab._curve(ret)[1]}
    b = [r["base"] for r in rows]
    s["base"] = {"tradeable": statistics.fmean(x["tradeable"] for x in b),
                 "vs_spy_raw": statistics.fmean(x["vs_spy_raw"] for x in b),
                 "vs_spy_raw_t": lab._tstat([x["vs_spy_raw"] for x in b]),
                 "vs_spy_clipped": statistics.fmean(x["vs_spy_clipped"] for x in b),
                 "vs_spy_clipped_t": lab._tstat([x["vs_spy_clipped"] for x in b]),
                 "dispersion": statistics.fmean(x["dispersion"] for x in b)}
    return s


def paired(rows_a, rows_b, book):
    """book's clipped edge on universe a minus on universe b, by week."""
    by = {r["week"]: r["books"][book]["clipped"]["edge"] for r in rows_b if book in r["books"]}
    diff = [r["books"][book]["clipped"]["edge"] - by[r["week"]] for r in rows_a if book in r["books"] and r["week"] in by]
    if not diff:
        return None
    half = len(diff) // 2
    return {"mean": statistics.fmean(diff), "t": lab._tstat(diff),
            "halves": [statistics.fmean(diff[:half]), statistics.fmean(diff[half:])] if half else None,
            "weeks_better": sum(1 for x in diff if x > 0), "weeks": len(diff)}


def verdicts(summaries, pairs):
    v = {"beats_random": {}, "wider_feeds_the_team": {}}
    for u, s in summaries.items():
        for n in BOOKS:
            x = s.get(n)
            if x and x["halves"]:
                v["beats_random"][f"{n} on {u}"] = bool(x["t"] >= 2 and x["edge"] > 0 and all(h > 0 for h in x["halves"]))
    for u in WIDER:
        p = pairs.get(u, {}).get("Three chairs")
        v["wider_feeds_the_team"][u] = bool(p and p["t"] >= 2 and p["mean"] > 0 and all(h > 0 for h in p["halves"]))
    v["the_111_is_enough"] = not any(v["wider_feeds_the_team"].values())
    return v


def show(title, summaries, pairs):
    print(f"\n  {title}")
    print(f"  {'universe':<13}{'book':<14}{'edge/wk':>9}{'t':>7}{'ahead':>8}{'raw edge':>10}{'ret/wk':>8}{'weekly SD':>11}{'max DD':>8}   vs the 111")
    for u, s in summaries.items():
        for n in BOOKS:
            x = s.get(n)
            if not x:
                continue
            p = pairs.get(u, {}).get(n)
            tail = f"   {p['mean']*100:+.2f}%/wk (t {p['t']:+.2f}, {p['weeks_better']}/{p['weeks']})" if p else ""
            print(f"  {u:<13}{n:<14}{x['edge']*100:+8.2f}%{x['t']:+7.2f}{x['ahead']:>5}/{x['weeks']:<3}{x['raw_edge']*100:+9.2f}%"
                  f"{x['mean_ret']*100:+7.2f}%{x['sd']*100:10.2f}%{x['max_dd']*100:+7.1f}%{tail}")
    print(f"\n  {'universe':<13}{'names/wk':>9}{'EW vs SPY raw':>15}{'t':>7}{'clipped':>9}{'t':>7}{'dispersion':>12}")
    for u, s in summaries.items():
        b = s["base"]
        print(f"  {u:<13}{b['tradeable']:>9.0f}{b['vs_spy_raw']*100:+14.2f}%{b['vs_spy_raw_t']:+7.2f}"
              f"{b['vs_spy_clipped']*100:+8.2f}%{b['vs_spy_clipped_t']:+7.2f}{b['dispersion']*100:11.2f}%")


def main(smoke=False):
    U = universes()
    if smoke:
        U = {REFERENCE: U[REFERENCE]}
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cweeks = lab.council_weeks(_last_friday())
    if smoke:
        hweeks, cweeks = hweeks[:3], cweeks[:1]
    cal = lab.earnings_calendar(sorted({t for names in U.values() for t in names}))
    end = lab._plus(cweeks[-1][1], 5)
    hist, cw = {}, {}
    for uname, names in U.items():
        # A finished universe is checkpointed in the gitignored cache, so a run
        # cut short (the pass takes the better part of an hour) resumes there.
        ck = lab.CACHE / f"pass9_{uname.replace(' ', '_').replace('&', 'and')}{'_smoke' if smoke else ''}.json"
        if ck.exists():
            doc = json.loads(ck.read_text(encoding="ascii"))
            hist[uname], cw[uname] = doc["hist"], doc["council"]
            print(f"  {uname}: from checkpoint {ck.name}")
            continue
        tickers = sorted(set(names)) + lab.EXTRA
        raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
        adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, p4.HIST_START)).items()}
        print(f"  {uname}: {len(names)} names, {len([t for t in names if t in raw])} with prices", flush=True)
        hist[uname] = replay(uname, names, hweeks, lab.HISTORY_DATA_START, cal, raw, adj, "hist")
        cw[uname] = replay(uname, names, cweeks, lab.DATA_START, cal, raw, adj, "council")
        lab.CACHE.mkdir(parents=True, exist_ok=True)
        with open(ck, "w", encoding="ascii", newline="\n") as fh:
            json.dump({"hist": hist[uname], "council": cw[uname]}, fh, default=float)
    hs = {u: summarize(rows) for u, rows in hist.items()}
    hp = {u: {n: paired(hist[u], hist[REFERENCE], n) for n in BOOKS} for u in hist if u != REFERENCE}
    show(f"History, {len(hweeks)} weeks", hs, hp)
    cs = {u: summarize(rows) for u, rows in cw.items()}
    cp = {u: {n: paired(cw[u], cw[REFERENCE], n) for n in BOOKS} for u in cw if u != REFERENCE}
    show(f"Council weeks, {len(cweeks)} (seen weeks: reported, decide nothing)", cs, cp)
    v = verdicts(hs, hp)
    hits = [k for k, ok in v["beats_random"].items() if ok]
    print(f"\n  registered verdicts (history): beats random: {', '.join(hits) if hits else 'none'}; "
          f"wider feeds the team: {', '.join(u for u, ok in v['wider_feeds_the_team'].items() if ok) or 'none'}; "
          f"the 111 is enough: {'yes' if v['the_111_is_enough'] else 'NO'}")
    out = lab.RESULTS / ("pass9_universe.smoke.json" if smoke else "pass9_universe.json")
    if smoke:
        out = Path(__file__).resolve().parent / "cache" / out.name     # gitignored scratch
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump({"universes": {u: len(n) for u, n in U.items()}, "sp500_source": SP500_CSV.name,
                   "history": {"summary": hs, "paired_vs_111": hp, "weeks": hist},
                   "council": {"summary": cs, "paired_vs_111": cp, "weeks": cw}, "verdicts": v},
                  fh, indent=1, default=float)
        fh.write("\n")


ASOF = lab.HISTORY_FIRST_MONDAY                       # 2024-09-09
ASOF_NAME = "the S&P 500 as of 2024-09"
SP500_ADDED_CSV = lab.LAB / "universe_sp500_added_2026-09-22.csv"


def sp500_asof():
    """Today's constituents that were already in the index when the history
    began: 'Date added' before the first history Monday (a blank date is a
    long-standing member). Removals since then are still missing, which
    flatters the base rate but not a momentum screen's edge; additions,
    which are names that rose into the index, are what this takes out."""
    with open(SP500_ADDED_CSV, encoding="ascii") as fh:
        rows = [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))]
    return sorted(r["ticker"] for r in rows if not r["date_added"] or r["date_added"] < ASOF)


def main_asof():
    """Pass 9b (registered after Pass 9's results, before this run): the S&P
    500 as it stood on 2024-09-09, scored like Pass 9's universes and paired
    against Pass 9's file for the 111 and for today's S&P 500."""
    universes()                                       # installs the sector fold
    names = sp500_asof()
    doc = json.loads((lab.RESULTS / "pass9_universe.json").read_text(encoding="utf-8"))
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cweeks = lab.council_weeks(_last_friday())
    cal = lab.earnings_calendar(names)
    end = lab._plus(cweeks[-1][1], 5)
    tickers = sorted(set(names)) + lab.EXTRA
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, p4.HIST_START)).items()}
    print(f"  {ASOF_NAME}: {len(names)} of today's {len(sp500())} names", flush=True)
    hist = replay(ASOF_NAME, names, hweeks, lab.HISTORY_DATA_START, cal, raw, adj, "hist")
    cw = replay(ASOF_NAME, names, cweeks, lab.DATA_START, cal, raw, adj, "council")
    out = {"universe": ASOF_NAME, "names": len(names), "asof": ASOF, "source": SP500_ADDED_CSV.name}
    for section, rows, title in (("history", hist, f"History, {len(hweeks)} weeks"),
                                 ("council", cw, f"Council weeks, {len(cweeks)} (seen weeks: reported, decide nothing)")):
        ref = doc[section]["weeks"]
        s = summarize(rows)
        pairs = {other: {n: paired(rows, ref[other], n) for n in BOOKS} for other in (REFERENCE, "the S&P 500")}
        show(title, {ASOF_NAME: s}, {ASOF_NAME: pairs[REFERENCE]})
        print("  against today's S&P 500 (the additions' share):")
        for n in BOOKS:
            p = pairs["the S&P 500"][n]
            print(f"    {n:<14}{p['mean']*100:+.2f}%/wk (t {p['t']:+.2f}, {p['weeks_better']}/{p['weeks']})")
        out[section] = {"summary": s, "paired": pairs, "weeks": rows}
    x = out["history"]["summary"]["Ophelia"]
    out["verdicts"] = {"Ophelia beats random on the S&P 500 as of 2024-09":
                       bool(x["t"] >= 2 and x["edge"] > 0 and all(h > 0 for h in x["halves"]))}
    print("\n  registered verdict (history): " + "; ".join(f"{k}: {'YES' if v else 'no'}" for k, v in out["verdicts"].items()))
    with open(lab.RESULTS / "pass9b_sp500_asof.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump(out, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    if sys.argv[1:] == ["asof"]:
        main_asof()
    else:
        main(smoke=sys.argv[1:] == ["smoke"])
