#!/usr/bin/env python3
"""Pass 19 -- Cecil's value trap.

ALL or HIG sat in five of the six official books from 08-17 to 09-21 while
they fell, and on 09-28 the Council's trigger check blocked all three of his
names on lines that had already fired. This pass asks whether a rule inside
his engine would do that job better. It captures his scored table each week
as Pass 12 does (the engine's legs, point-in-time P/E) and re-ranks it
offline; each rule removes names, and the next-ranked name that passes takes
the slot:

  as is                       Pass 12's as-is five
  own 50-day gate             skip a name whose last close is under its 50-day average
  sector 50-day gate          skip a name whose sector's SPDR ETF closed under its 50-day average
  one per sector              at most one name per GICS sector
  own gate + one per sector   both

Diagnostics: the trap (his names under a line against the rest of his five,
next week and over four), stacking (two or more names in one sector), and
block or replace for the three-chair book. The clean list decides; the 111
and the 277 are reported. Registered in lab/README.md before any run
(be5e232).

    python lab/pass19_cecil_trap.py
    python lab/pass19_cecil_trap.py smoke
"""
from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass7_combos as p7  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass10_sectors as p10  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402
import pass12_cecil_legs as p12  # noqa: E402
import pass13_hold_manage as p13  # noqa: E402
import pass15_exits as p15  # noqa: E402

BASE = "as is"
OWN = "own 50-day gate"
SECTOR = "sector 50-day gate"
ONE = "one per sector"
BOTH = "own gate + one per sector"
VARIANTS = (BASE, OWN, SECTOR, ONE, BOTH)
AS_IS3, BLOCK, REPLACE = "three chairs, as is", "three chairs, block", "three chairs, replace"
THREE = (AS_IS3, BLOCK, REPLACE)
MA_DAYS = 50
CLIP4 = 0.40                    # four-week returns, clipped at twice the weekly width
ETF = {"Information Technology": "XLK", "Communication Services": "XLC", "Consumer Discretionary": "XLY",
       "Consumer Staples": "XLP", "Health Care": "XLV", "Financials": "XLF", "Industrials": "XLI",
       "Energy": "XLE", "Materials": "XLB", "Utilities": "XLU", "Real Estate": "XLRE"}
ETFS = sorted(set(ETF.values()))
SPELLING = {"Technology": "Information Technology", "Healthcare": "Health Care"}   # CSV and bucket -> GICS
THE_277 = "the 277"


def sectors_for(names):
    """GICS from the S&P table, else the Council CSV, else the engine's bucket."""
    from scan_pipeline.config.tickers import COUNCIL_SECTORS
    from scan_pipeline.utils import data_utils
    sp = p9.sp500()
    out = {}
    for t in names:
        s = sp.get(t) or COUNCIL_SECTORS.get(t) or data_utils.SECTOR_MAP.get(t) or "?"
        out[t] = SPELLING.get(s, s)
    return out


def under(series, W, days=MA_DAYS):
    """The last close before Monday W is under the average of the last `days`
    closes; None when there are fewer closes than that."""
    if series is None:
        return None
    closes = [r["close"] for r in series.before(W, 2 * days + 10)]
    if len(closes) < days:
        return None
    return closes[-1] < statistics.fmean(closes[-days:])


def order_of(table, tset):
    """Pass 12's "as is" ranking, in full: score, the cheaper multiple, the week's return, the ticker."""
    rows = [s for s in table if s["ticker"] in tset]
    rows.sort(key=lambda s: s["ticker"])
    rows.sort(key=lambda s: (s["value_score"] + s["quality_score"] + s["safety_score"],
                             -(s["pe"] if s["pe"] is not None else 999.0), s["weekly_return"]), reverse=True)
    return [s["ticker"] for s in rows]


def pick(order, skip=lambda t: False, sectors=None, k=p7.TOP):
    out, used = [], set()
    for t in order:
        if skip(t) or (sectors is not None and sectors.get(t, "?") in used):
            continue
        out.append(t)
        if sectors is not None:
            used.add(sectors.get(t, "?"))
        if len(out) == k:
            break
    return out


def week_rows(uname, names, weeks, start, cal, raw, adj, sectors, tag):
    cap = {}
    runs = lab.run(verbose=False, knobs=dict(lab.VARIANTS3["base"], pe_builder=p11.pe_builder), capture=cap,
                   weeks=weeks, start=start, earnings=cal, names=names)
    out = []
    for r, (label, W, _) in zip(runs, weeks):
        table = cap[W]["cecil"]
        books9, tradeable, _ = p9.week_books(names, raw, adj, cal, W, r["proposals"])
        tset = set(tradeable)
        order = order_of(table, tset)
        assert order[:p7.TOP] == p12.rerank(table, {}, W, tset, 1.0, 1.0, 0.0), f"{uname} {label}: not Pass 12's as is"

        memo = {}

        def own(t):
            if t not in memo:
                memo[t] = under(raw.get(t), W) is True
            return memo[t]

        etf_under = {e: under(raw.get(e), W) is True for e in ETFS}

        def sec(t):
            e = ETF.get(sectors.get(t, "?"))
            return bool(e and etf_under[e])

        fives = {BASE: pick(order), OWN: pick(order, own), SECTOR: pick(order, sec),
                 ONE: pick(order, sectors=sectors), BOTH: pick(order, own, sectors)}
        C = fives[BASE]
        O = [t for t, _ in books9["Ophelia"]]
        M = [t for t, _ in books9["Marky"]]
        books = {n: p7.equal(f) for n, f in fives.items()}
        books[AS_IS3] = p7.slices([O, C, M])
        books[BLOCK] = p7.slices([O, [t for t in C if not sec(t)], M])
        books[REPLACE] = p7.slices([O, fives[SECTOR], M])

        one, four = {}, {}
        for t in tradeable:
            if t not in adj:
                continue
            x = adj[t].week_return(W)
            if x is not None:
                one[t] = p7._clip(x)
            x = p13.hold_return(adj[t], W, 4)
            if x is not None:
                four[t] = max(-CLIP4, min(CLIP4, x))
        base1 = statistics.fmean(one.values()) if one else None
        base4 = statistics.fmean(four.values()) if four else None
        trap = [{"ticker": t, "sector": sectors.get(t, "?"), "own": own(t), "sector_line": sec(t),
                 "x1": one[t] - base1 if t in one else None,
                 "x4": four[t] - base4 if t in four else None} for t in C]
        out.append({"week": label, "spy": adj["SPY"].week_return(W) or 0.0, "five": C, "fives": fives,
                    "ophelia": O, "marky": M, "trap": trap,
                    "stacked": max(collections.Counter(sectors.get(t, "?") for t in C).values(), default=0) >= 2,
                    "etfs_under": sorted(e for e, u in etf_under.items() if u),
                    "books": p7.score_week(books, adj, W, tradeable, f"p19-{uname}-{tag}")})
    return out


def trap_summary(rows):
    names = [x for r in rows for x in r["trap"]]
    out = {"name_weeks": len(names),
           "stacked_weeks": statistics.fmean(1.0 if r["stacked"] else 0.0 for r in rows) if rows else None}
    for flag in ("own", "sector_line"):
        f = {"share_under": statistics.fmean(1.0 if x[flag] else 0.0 for x in names) if names else None}
        for h in ("x1", "x4"):
            diffs, u_all, a_all = [], [], []
            for r in rows:
                u = [x[h] for x in r["trap"] if x[flag] and x[h] is not None]
                a = [x[h] for x in r["trap"] if not x[flag] and x[h] is not None]
                u_all += u
                a_all += a
                if u and a:
                    diffs.append(statistics.fmean(u) - statistics.fmean(a))
            f[h] = {"under": statistics.fmean(u_all) if u_all else None, "above": statistics.fmean(a_all) if a_all else None,
                    "n_under": len(u_all), "n_above": len(a_all), "diff": statistics.fmean(diffs) if diffs else None,
                    "t": (lab._tstat(diffs) if h == "x1" else p15.nw_t(diffs, 3)), "weeks": len(diffs)}
        out[flag] = f
    return out


def same_returns(rows, a, b):
    """The check beside the registered measure: each book's edge subtracts its
    own random draws (the lab seeds them by book name), so two identical books
    differ by baseline noise. Their clipped returns share one pool and differ
    only where the books do."""
    d = [r["books"][a]["clipped"]["ret"] - r["books"][b]["clipped"]["ret"] for r in rows]
    half = len(d) // 2
    return {"ret_mean": statistics.fmean(d), "ret_t": lab._tstat(d),
            "ret_halves": [statistics.fmean(d[:half]), statistics.fmean(d[half:])] if half else None}


def pairs_for(rows):
    pairs = {n: p10.paired(rows, rows, n, BASE) for n in VARIANTS[1:]}
    for n in pairs:
        pairs[n]["same_five"] = statistics.fmean(1.0 if set(r["fives"][n]) == set(r["fives"][BASE]) else 0.0
                                                 for r in rows)
        pairs[n].update(same_returns(rows, n, BASE))
    for a, b in ((BLOCK, AS_IS3), (REPLACE, AS_IS3), (REPLACE, BLOCK)):
        p = p10.paired(rows, rows, a, b)
        p["same_five"] = statistics.fmean(1.0 if r["books"][a]["book"] == r["books"][b]["book"] else 0.0
                                          for r in rows)
        p.update(same_returns(rows, a, b))
        pairs[f"{a} vs {b.split(', ')[1]}"] = p
    return pairs


def passes(p):
    return bool(p and p["t"] >= 2 and p["mean"] > 0 and p["halves"] and all(h > 0 for h in p["halves"]))


def _pct(x, width=7):
    return f"{'--':>{width}}" if x is None else f"{x * 100:+{width}.2f}"


def show(title, s, pairs, trap):
    print(f"\n  {title}")
    print(f"  {'book':<28}{'edge/wk':>9}{'t':>7}{'ahead':>8}{'ret/wk':>8}{'weekly SD':>11}{'max DD':>8}   paired")
    for n in VARIANTS + THREE:
        x = s[n]
        key = n if n in pairs else {BLOCK: f"{BLOCK} vs as is", REPLACE: f"{REPLACE} vs block"}.get(n)
        p = pairs.get(key) if key else None
        tail = ""
        if p:
            vs = "as is" if n in VARIANTS else key.split(" vs ")[1]
            tail = (f"   {p['mean']*100:+.2f}%/wk vs {vs} (t {p['t']:+.2f}, {p['weeks_better']}/{p['weeks']};"
                    f" same {p['same_five']:.0%}; returns {p['ret_mean']*100:+.2f}, t {p['ret_t']:+.2f})")
        print(f"  {n:<28}{x['edge']*100:+8.2f}%{x['t']:+7.2f}{x['ahead']:>5}/{x['weeks']:<3}{x['mean_ret']*100:+7.2f}%"
              f"{x['sd']*100:10.2f}%{x['max_dd']*100:+7.1f}%{tail}")
    print(f"  stacked (2+ names in a sector): {trap['stacked_weeks']:.0%} of weeks; name-weeks: {trap['name_weeks']}")
    for flag, label in (("own", "own line"), ("sector_line", "sector line")):
        f = trap[flag]
        print(f"  under the {label}: {f['share_under']:.0%} of his names.  excess vs the pool, under / above:")
        for h, hl in (("x1", "next week"), ("x4", "four weeks")):
            g = f[h]
            t = "--" if g["t"] is None else f"{g['t']:+.2f}"
            print(f"      {hl:<11}{_pct(g['under'])}% (n {g['n_under']}) / {_pct(g['above'])}% (n {g['n_above']})"
                  f"   paired by week {_pct(g['diff'])}% (t {t}, {g['weeks']} weeks)")


def reproduces_pass12(rows, uname):
    doc = json.loads((lab.RESULTS / "pass12_cecil_legs.json").read_text(encoding="utf-8"))
    if uname not in doc["universes"]:
        return None
    old = {r["week"]: r["fives"][p12.BASE] for r in doc["universes"][uname]["history"]["weeks"]}
    hits = [r["five"] == old[r["week"]] for r in rows if r["week"] in old]
    return statistics.fmean(hits) if hits else None


def main(smoke=False):
    U = p9.universes()
    universes = {p11.CLEAN: p9.sp500_asof(), p9.REFERENCE: U[p9.REFERENCE], THE_277: U[THE_277]}
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cweeks = lab.council_weeks(p9._last_friday())
    if smoke:
        universes, hweeks, cweeks = {p9.REFERENCE: U[p9.REFERENCE]}, hweeks[:3], cweeks[:1]
    end = lab._plus(cweeks[-1][1], 5)
    result = {"registered": "be5e232", "variants": list(VARIANTS), "three_chairs": list(THREE),
              "ma_days": MA_DAYS, "clip4": CLIP4, "etf": ETF, "universes": {}}
    for uname, names in universes.items():
        cal = lab.earnings_calendar(names)
        sectors = sectors_for(names)
        tickers = sorted(set(names) | set(ETFS)) + [x for x in lab.EXTRA if x not in names]
        raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
        adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, p4.HIST_START)).items()}
        gaps = [e for e in ETFS if e not in raw]
        print(f"  Cecil on {uname}: {len(names)} names; sector ETFs missing: {gaps or 'none'}", flush=True)
        hist = week_rows(uname, names, hweeks, lab.HISTORY_DATA_START, cal, raw, adj, sectors, "hist")
        cw = week_rows(uname, names, cweeks, lab.DATA_START, cal, raw, adj, sectors, "council")
        rep = None if smoke else reproduces_pass12(hist, uname)
        out = {"reproduces_pass12_as_is": rep,
               "sectors": dict(collections.Counter(sectors.values()))}
        for section, rows, title in (("history", hist, f"Cecil on {uname}: history, {len(hweeks)} weeks"),
                                     ("council", cw, f"Cecil on {uname}: Council weeks, {len(cweeks)} (seen; decide nothing)")):
            s = {n: p10.summarize(rows, n) for n in VARIANTS + THREE}
            pairs = pairs_for(rows)
            trap = trap_summary(rows)
            show(title, s, pairs, trap)
            out[section] = {"summary": s, "paired": pairs, "trap": trap, "weeks": rows}
        print(f"\n  Council weeks on {uname}, as is -> sector gate (ETFs under the line):")
        for r in cw:
            print(f"    {r['week']}  {' '.join(r['fives'][BASE]):<28}-> {' '.join(r['fives'][SECTOR]):<28}"
                  f"own gate -> {' '.join(r['fives'][OWN]):<28}({' '.join(r['etfs_under']) or 'none'})")
        print(f"  'as is' reproduces Pass 12's as-is five: {'n/a' if rep is None else f'{rep:.0%} of weeks'}")
        result["universes"][uname] = out
    if p11.CLEAN in result["universes"]:
        pairs = result["universes"][p11.CLEAN]["history"]["paired"]
        v = {n: passes(pairs[n]) for n in VARIANTS[1:]}
        v["replace beats block"] = passes(pairs[f"{REPLACE} vs block"])
        result["verdicts"] = v
        print("\n  registered verdicts (history, the clean list): "
              + "; ".join(f"{n} {'HELPS' if ok else 'no'}" for n, ok in v.items()))
    out = lab.CACHE / "pass19.smoke.json" if smoke else lab.RESULTS / "pass19_cecil_trap.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"  wrote {out.relative_to(lab.LAB.parent)}")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
