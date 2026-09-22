#!/usr/bin/env python3
"""Pass 10 -- Ophelia's map: whose sectors?

The owner asked whether Ophelia should treat semiconductors as a sector of
their own, and whether the standard sectors are the problem ("would be
interesting if we made our own"). Her rotation is the part of her that
showed up in Pass 9b: a 40-point anchor for the top sector by prior-week
average return, 20 for the second, a flow term, and up to 30 points of
regime credit for offensive or defensive sectors. So the map it reads is a
fair question. Five maps, the engine Ophelia's five each week, scored like
Pass 9 (clipped edge over random books from the same universe's tradeable
names), on the S&P 500 as it stood on 2024-09-09 (463 names, the clean list)
with the 111's 109 stocks beside it:

  engine 8         the eight engine buckets (Pass 9b's map)          baseline
  engine 8+Semis   the eight, with the GICS sub-industries "Semiconductors"
                   and "Semiconductor Materials & Equipment" as a ninth
                   bucket, offensive
  GICS 11          the index's eleven GICS sectors; a sector is offensive or
                   defensive by the engine bucket it folds onto
  GICS 11+Semis    GICS 11 with the semiconductor sub-industries as a
                   twelfth sector, offensive
  our own 11       point-in-time: each week, the names with at least 40 of
                   the trailing 52 weekly close-to-close returns, average-
                   linkage clustering on 1 - correlation, cut into eleven
                   clusters; a cluster is offensive or defensive by the
                   majority engine bucket of its members; names with too
                   little history sit in "Other"

The 111 has no sub-industry column: its semiconductor names are NVDA, AMD
and TSM (a three-name sector; reported, decides nothing), and its GICS
sectors come from the Council CSV. The regime credit's lists are module
constants of the engine since 2026-09-22 (a behavior-preserving change), so
every map keeps the credit. Registered in lab/README.md before any run.

    python lab/pass10_sectors.py
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass7_combos as p7  # noqa: E402
import pass9_universe as p9  # noqa: E402

FULL_CSV = lab.LAB / "universe_sp500_full_2026-09-22.csv"
SEMI_SUBS = {"Semiconductors", "Semiconductor Materials & Equipment"}
SEMIS_111 = {"NVDA", "AMD", "TSM"}
SCHEMES = ("engine 8", "engine 8+Semis", "GICS 11", "GICS 11+Semis", "our own 11")
BASE = "engine 8"
K = 11
MIN_HISTORY, WINDOW = 40, 52
OFFENSIVE, DEFENSIVE = ["Technology", "Consumer", "Industrials"], ["Utilities", "Healthcare"]


class WeekMap:
    """SECTOR_MAP stand-in whose lookups follow the week the lab is replaying."""
    def __init__(self, by_week):
        self.by_week = by_week

    def get(self, t, default=None):
        return self.by_week.get(lab._TAP["week"], {}).get(t, default)


class WeekSet:
    """A regime list whose membership follows the week (the clusters' offensive set)."""
    def __init__(self, by_week):
        self.by_week = by_week

    def __contains__(self, label):
        return label in self.by_week.get(lab._TAP["week"], set())


def sp500_full():
    with open(FULL_CSV, encoding="ascii") as fh:
        return {r["ticker"]: r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}


def bucket(t):
    """The engine bucket a name folds onto, whatever the map in force."""
    from scan_pipeline.config.tickers import COUNCIL_SECTORS
    from scan_pipeline.utils.data_utils import GICS_FOLD, SECTOR_MAP
    if t in SECTOR_MAP:
        return SECTOR_MAP[t]
    return GICS_FOLD.get(COUNCIL_SECTORS.get(t) or "", "Unknown")


def static_maps(uname, names, sp):
    """{scheme: (ticker -> label, offensive labels, defensive labels)} for the four fixed maps."""
    from scan_pipeline.config.tickers import COUNCIL_SECTORS
    from scan_pipeline.utils.data_utils import GICS_FOLD
    base = {t: bucket(t) for t in names}
    semis = ({t for t in names if t in sp and sp[t]["gics_sub_industry"] in SEMI_SUBS}
             if uname != p9.REFERENCE else {t for t in names if t in SEMIS_111})
    gics = {t: (sp[t]["gics_sector"] if uname != p9.REFERENCE else COUNCIL_SECTORS[t]) for t in names}
    fold = dict(GICS_FOLD, **{"Information Technology": "Technology", "Health Care": "Healthcare"})
    g_off = sorted({g for g in gics.values() if fold.get(g) in OFFENSIVE})
    g_def = sorted({g for g in gics.values() if fold.get(g) in DEFENSIVE})
    return {
        "engine 8": (base, OFFENSIVE, DEFENSIVE),
        "engine 8+Semis": ({t: ("Semiconductors" if t in semis else b) for t, b in base.items()},
                           OFFENSIVE + ["Semiconductors"], DEFENSIVE),
        "GICS 11": (gics, g_off, g_def),
        "GICS 11+Semis": ({t: ("Semiconductors" if t in semis else g) for t, g in gics.items()},
                          g_off + ["Semiconductors"], g_def),
    }, len(semis)


def cluster_maps(names, adj, weeks):
    """Per week: {ticker: 'C1'..'C11' or 'Other'}, and the offensive/defensive cluster sets."""
    import numpy as np
    from scipy.cluster.hierarchy import fcluster, linkage
    from scan_pipeline.fetch_market_data import _aggregate_weekly
    maps, off, dfn = {}, {}, {}
    for _, W, _ in weeks:
        spy_dates = [h.date for h in _aggregate_weekly(adj["SPY"].before(W, 400))][-(WINDOW + 1):]
        idx = {d: i for i, d in enumerate(spy_dates)}
        rows, kept = [], []
        for t in names:
            if t not in adj:
                continue
            wk = _aggregate_weekly(adj[t].before(W, 400))
            closes = {h.date: h.close for h in wk if h.date in idx}
            series = np.full(len(spy_dates), np.nan)
            prev = None
            for d in spy_dates:
                c = closes.get(d)
                if c and prev:
                    series[idx[d]] = c / prev - 1.0
                prev = c if c else prev
            series = series[1:]
            if np.isfinite(series).sum() >= MIN_HISTORY:
                s = np.where(np.isfinite(series), series, 0.0)
                sd = s.std()
                rows.append((s - s.mean()) / sd if sd > 0 else s)
                kept.append(t)
        labels = {t: "Other" for t in names}
        if len(kept) > K:
            Z = linkage(np.array(rows), method="average", metric="correlation")
            for t, c in zip(kept, fcluster(Z, K, criterion="maxclust")):
                labels[t] = f"C{int(c)}"
        maps[W] = labels
        members = {}
        for t, c in labels.items():
            members.setdefault(c, []).append(bucket(t))
        majority = {c: Counter(bs).most_common(1)[0][0] for c, bs in members.items() if c != "Other"}
        off[W] = {c for c, b in majority.items() if b in OFFENSIVE}
        dfn[W] = {c for c, b in majority.items() if b in DEFENSIVE}
    return maps, off, dfn


def pool(names, raw, cal, W):
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
    return tradeable


def replay(uname, scheme, names, weeks, start, cal, raw, adj, sector_map, offensive, defensive, tag):
    from scan_pipeline.utils import data_utils
    original = data_utils.SECTOR_MAP
    data_utils.SECTOR_MAP = sector_map
    try:
        knobs = dict(lab.VARIANTS3["base"], **{"ophelia.OFFENSIVE_SECTORS": offensive,
                                               "ophelia.DEFENSIVE_SECTORS": defensive})
        rows = lab.run(verbose=False, knobs=knobs, weeks=weeks, start=start, earnings=cal, names=names)
    finally:
        data_utils.SECTOR_MAP = original
    out = []
    for r, (label, W, _) in zip(rows, weeks):
        tradeable = pool(names, raw, cal, W)
        tset = set(tradeable)
        five = [t for t in r["proposals"]["Ophelia"] if t in tset][:p7.TOP]
        lab._TAP["week"] = W                       # a WeekMap reads the week being scored
        out.append({"week": label, "spy": adj["SPY"].week_return(W) or 0.0,
                    "five": five, "sectors": [sector_map.get(t, "?") for t in five],
                    "books": p7.score_week({"Ophelia": p7.equal(five)}, adj, W, tradeable, f"p10-{uname}-{scheme}-{tag}")})
    return out


def summarize(rows):
    rs = [r["books"]["Ophelia"] for r in rows if "Ophelia" in r["books"]]
    e = [x["clipped"]["edge"] for x in rs]
    ret = [x["raw"]["ret"] for x in rs]
    half = len(rs) // 2
    by_half_year = {}
    for r in rows:
        if "Ophelia" in r["books"]:
            key = r["week"][:4] + ("H1" if r["week"][5:7] <= "06" else "H2")
            by_half_year.setdefault(key, []).append(r["books"]["Ophelia"]["clipped"]["edge"])
    return {"weeks": len(rs), "edge": statistics.fmean(e), "t": lab._tstat(e),
            "ahead": sum(1 for x in e if x > 0),
            "halves": [statistics.fmean(e[:half]), statistics.fmean(e[half:])] if half else None,
            "raw_edge": statistics.fmean(x["raw"]["edge"] for x in rs),
            "mean_ret": statistics.fmean(ret), "sd": statistics.pstdev(ret), "max_dd": lab._curve(ret)[1],
            "names": statistics.fmean(len(r["five"]) for r in rows),
            "by_half_year": {k: statistics.fmean(v) for k, v in sorted(by_half_year.items())}}


def paired(rows_a, rows_b):
    by = {r["week"]: r["books"]["Ophelia"]["clipped"]["edge"] for r in rows_b if "Ophelia" in r["books"]}
    diff = [r["books"]["Ophelia"]["clipped"]["edge"] - by[r["week"]] for r in rows_a
            if "Ophelia" in r["books"] and r["week"] in by]
    half = len(diff) // 2
    return {"mean": statistics.fmean(diff), "t": lab._tstat(diff),
            "halves": [statistics.fmean(diff[:half]), statistics.fmean(diff[half:])] if half else None,
            "weeks_better": sum(1 for x in diff if x > 0), "weeks": len(diff),
            "same_five": statistics.fmean(1.0 if ra["five"] == rb["five"] else 0.0
                                          for ra, rb in zip(rows_a, rows_b))}


def show(title, summaries, pairs):
    print(f"\n  {title}")
    print(f"  {'scheme':<16}{'edge/wk':>9}{'t':>7}{'ahead':>8}{'ret/wk':>8}{'weekly SD':>11}{'max DD':>8}{'names':>7}   vs engine 8")
    for scheme in SCHEMES:
        x = summaries.get(scheme)
        if not x:
            continue
        p = pairs.get(scheme)
        tail = (f"   {p['mean']*100:+.2f}%/wk (t {p['t']:+.2f}, {p['weeks_better']}/{p['weeks']}; same five {p['same_five']:.0%})"
                if p else "")
        print(f"  {scheme:<16}{x['edge']*100:+8.2f}%{x['t']:+7.2f}{x['ahead']:>5}/{x['weeks']:<3}{x['mean_ret']*100:+7.2f}%"
              f"{x['sd']*100:10.2f}%{x['max_dd']*100:+7.1f}%{x['names']:7.1f}{tail}")
    print("  by half-year, clipped edge/wk: " + " | ".join(
        f"{scheme}: " + ", ".join(f"{k} {v*100:+.2f}" for k, v in summaries[scheme]["by_half_year"].items())
        for scheme in SCHEMES if scheme in summaries))


def main(smoke=False):
    U = p9.universes()
    sp = sp500_full()
    universes = {"the S&P 500 as of 2024-09": p9.sp500_asof(), p9.REFERENCE: U[p9.REFERENCE]}
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cweeks = lab.council_weeks(p9._last_friday())
    if smoke:                                      # three weeks on the 111, to the gitignored cache
        universes, hweeks, cweeks = {p9.REFERENCE: U[p9.REFERENCE]}, hweeks[:3], cweeks[:1]
    end = lab._plus(cweeks[-1][1], 5)
    result = {"schemes": SCHEMES, "k": K, "window": WINDOW, "min_history": MIN_HISTORY, "universes": {}}
    for uname, names in universes.items():
        cal = lab.earnings_calendar(names)
        tickers = sorted(set(names)) + lab.EXTRA
        raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
        adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, p4.HIST_START)).items()}
        maps, n_semis = static_maps(uname, names, sp)
        cm, c_off, c_def = cluster_maps(names, adj, hweeks + cweeks)
        maps["our own 11"] = (WeekMap(cm), WeekSet(c_off), WeekSet(c_def))
        print(f"  {uname}: {len(names)} names, {n_semis} semiconductors", flush=True)
        hist, cw = {}, {}
        for scheme in SCHEMES:
            m, off, dfn = maps[scheme]
            hist[scheme] = replay(uname, scheme, names, hweeks, lab.HISTORY_DATA_START, cal, raw, adj, m, off, dfn, "hist")
            cw[scheme] = replay(uname, scheme, names, cweeks, lab.DATA_START, cal, raw, adj, m, off, dfn, "council")
            print(f"    {scheme}: done", flush=True)
        hs = {s: summarize(hist[s]) for s in SCHEMES}
        hp = {s: paired(hist[s], hist[BASE]) for s in SCHEMES if s != BASE}
        show(f"{uname}: history, {len(hweeks)} weeks", hs, hp)
        cs = {s: summarize(cw[s]) for s in SCHEMES}
        cp = {s: paired(cw[s], cw[BASE]) for s in SCHEMES if s != BASE}
        show(f"{uname}: Council weeks, {len(cweeks)} (seen weeks: reported, decide nothing)", cs, cp)
        sizes = Counter(len({c for c in cm[W].values()}) for _, W, _ in hweeks)
        result["universes"][uname] = {"names": len(names), "semis": n_semis, "cluster_count_weeks": dict(sizes),
                                      "history": {"summary": hs, "paired": hp, "weeks": hist},
                                      "council": {"summary": cs, "paired": cp, "weeks": cw}}
    primary = result["universes"].get("the S&P 500 as of 2024-09")
    if primary:
        prim = primary["history"]["paired"]
        v = {s: bool(p["t"] >= 2 and p["mean"] > 0 and all(h > 0 for h in p["halves"])) for s, p in prim.items()}
        result["verdicts"] = v
        print("\n  registered verdicts (history, the S&P 500 as of 2024-09): "
              + "; ".join(f"{s} {'HELPS' if ok else 'no'}" for s, ok in v.items()))
    out = lab.CACHE / "pass10_sectors.smoke.json" if smoke else lab.RESULTS / "pass10_sectors.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
