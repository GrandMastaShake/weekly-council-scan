#!/usr/bin/env python3
"""Pass 23 -- the drift chair on the Council's clock (registered in lab/README.md, 0400fdb).

Each Monday W the chair takes names whose earnings reaction day fell in the look-back window (A: the previous Mon-Fri week; B: the
previous 15 sessions) and that are tradeable that Monday, ranks them by the table's surprise percent and buys the top five at W's
open. Scored hold 1 (W open to Friday close) and hold 4 (to the Friday of W+3) against random picks from the whole tradeable pool and
from the candidate set; and as a fourth chair against Pass 19's three chairs.

    python lab/pass23_drift_chair.py
    python lab/pass23_drift_chair.py smoke
"""
from __future__ import annotations

import bisect
import json
import random
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
import pass13_hold_manage as p13  # noqa: E402
import pass15_exits as p15  # noqa: E402
import pass19_cecil_trap as p19  # noqa: E402
import pass20_regimes as p20  # noqa: E402
import pass21_beat_fall as p21  # noqa: E402

VARIANTS = {"A last week": (7, 3, 15), "B three weeks": (21, 1, 30)}     # calendar days back (start, end), minimum tradeable candidates
FIXED = False        # "fixed" mode (the 2026-10-12 audit): the blackout looks strictly after the previous Friday, the draws run over sorted lists, B is the previous 15 sessions
TOP = 5
DRAWS = 200
CLIP4 = 0.40
NW_LAGS = 4


def candidates(events, W, variant, dates=None):
    lo, hi, _ = VARIANTS[variant]
    a, b = lab._plus(W, -lo), lab._plus(W, -hi)
    if FIXED and variant.startswith("B") and dates is not None:       # the previous 15 sessions, not three calendar weeks
        i = bisect.bisect_left(dates, W)
        a, b = dates[max(0, i - 15)], dates[i - 1]
    return [e for e in events if a <= e["react"] <= b]


def pool_fixed(names, raw, cal, W):
    """p10.pool with the first report required to fall strictly after the previous Friday (a Friday reporter is not reporting in the coming week)."""
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    from scan_pipeline.utils.data_utils import EARNINGS_BLACKOUT_TRADING_DAYS
    short = {t: _aggregate_weekly(raw[t].before(W, lab.LOOKBACK_DAYS)) for t in names if t in raw}
    eligible = [t for t in names if len(short.get(t, [])) >= lab.MIN_WEEKS]
    F = _aggregate_weekly(raw["SPY"].before(W, lab.LOOKBACK_DAYS))[-1].date
    out = []
    for t in eligible:
        nxt = lab._next_report(cal.get(t), lab._plus(F, 1))
        etd = _business_days_between(F, nxt) if nxt else None
        if etd is None or not 0 <= etd <= EARNINGS_BLACKOUT_TRADING_DAYS:
            out.append(t)
    return out


def edge_vs(rng, picks_ret, pool_rets):
    """Mean return of the picks minus the mean of DRAWS random equal-size draws from pool_rets (a dict ticker -> return)."""
    names = list(pool_rets)
    k = len(picks_ret)
    if len(names) < k:
        return None
    draws = [statistics.fmean(pool_rets[t] for t in rng.sample(names, k)) for _ in range(DRAWS)]
    return statistics.fmean(picks_ret) - statistics.fmean(draws)


def summarize(vals):
    if len(vals) < 8:
        return {"weeks": len(vals), "testable": False}
    half = len(vals) // 2
    t = p15.nw_t(vals, NW_LAGS)
    h = [statistics.fmean(vals[:half]), statistics.fmean(vals[half:])]
    med = statistics.median(vals)
    return {"weeks": len(vals), "testable": True, "mean": statistics.fmean(vals), "t": t, "halves": h, "median": med,
            "has_edge": bool(t >= 2 and all(x > 0 for x in h) and med > 0)}


def main(smoke=False):
    names = p9.sp500_asof()
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cal = lab.earnings_calendar(names)
    tickers = sorted(set(names) | set(p19.ETFS)) + [x for x in lab.EXTRA if x not in names]
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, p20.END, p4.HIST_START)).items()}
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, p20.END, p4.HIST_START)).items()}
    events = p21.build_events(names, adj, p21.fetch(sorted(set(names))))
    rows = p20.load_rows(p11.CLEAN, "hist", len(hweeks))
    if smoke:
        rows = rows[:30]
    monday = {label: W for label, W, _ in hweeks}
    out = {v: {"active": 0, "hold1_pool": [], "hold1_cand": [], "hold4_pool": [], "hold4_cand": []} for v in VARIANTS}
    team = {v: [] for v in VARIANTS}
    weekly = []
    for r in rows:
        W = monday[r["week"]]
        tradeable = set((pool_fixed if FIXED else p10.pool)(names, raw, cal, W))
        O, C, M = r["ophelia"], r["five"], r["marky"]
        books3 = p7.slices([O, C, M])
        wk = {"W": W}
        for v, (_, _, need) in VARIANTS.items():
            cand = [e for e in candidates(events, W, v, raw["SPY"].dates) if e["t"] in tradeable]
            seen, uniq = set(), []
            for e in sorted(cand, key=lambda e: (-e["surprise"], e["t"])):          # one row per ticker: its best-surprise event in the window
                if e["t"] not in seen:
                    seen.add(e["t"])
                    uniq.append(e)
            if len(uniq) < need:
                team[v].append(0.0)
                continue
            D = [e["t"] for e in uniq[:TOP]]
            cset = [e["t"] for e in uniq]
            out[v]["active"] += 1
            # hold 1: the lab's own scorer (clipped weekly returns, random picks from the whole tradeable pool)
            scored = p7.score_week({"Drift": p7.equal(D), "Four": p7.slices([O, C, M, D]), "Three": books3}, adj, W, sorted(tradeable), f"p23-{v}")
            out[v]["hold1_pool"].append(scored["Drift"]["clipped"]["edge"])
            wk1 = {t: p7._clip(adj[t].week_return(W) or 0.0) for t in cset if t in adj and adj[t].week_return(W) is not None}
            rng = random.Random(f"{lab.SEED}-p23-{v}-{W}-1")
            e1 = edge_vs(rng, [wk1[t] for t in D if t in wk1], wk1)
            if e1 is not None:
                out[v]["hold1_cand"].append(e1)
            # hold 4
            def h4(t):
                x = p13.hold_return(adj[t], W, 4) if t in adj else None
                return None if x is None else max(-CLIP4, min(CLIP4, x))
            pool4 = {t: h4(t) for t in (sorted(tradeable) if FIXED else tradeable)}
            pool4 = {t: x for t, x in pool4.items() if x is not None}
            cand4 = {t: x for t, x in ((t, h4(t)) for t in cset) if x is not None}
            picks4 = [pool4[t] for t in D if t in pool4]
            if len(picks4) == len(D) and len(pool4) >= 30:
                rng = random.Random(f"{lab.SEED}-p23-{v}-{W}-4")
                out[v]["hold4_pool"].append(edge_vs(rng, picks4, pool4) / 4.0)
                if len(cand4) >= TOP:
                    out[v]["hold4_cand"].append(edge_vs(rng, picks4, cand4) / 4.0)
            team[v].append(scored["Four"]["clipped"]["ret"] - scored["Three"]["clipped"]["ret"])
            wk[v] = D
        weekly.append(wk)
    result = {"registered": "0400fdb", "weeks": len(rows), "variants": {}}
    print(f"\n  S&P 500 as of 2024-09, {len(rows)} history weeks; the chair buys the top {TOP} by earnings surprise at Monday's open")
    print(f"  {'variant':<15}{'test':<26}{'active':>7}{'mean/wk':>9}{'t':>7}  halves            median  edge?")
    for v in VARIANTS:
        res = {"active_weeks": out[v]["active"]}
        for key, label in (("hold1_pool", "hold 1 vs the pool"), ("hold1_cand", "hold 1 vs candidates"), ("hold4_pool", "hold 4 vs the pool (/wk)"), ("hold4_cand", "hold 4 vs candidates (/wk)")):
            s = summarize(out[v][key])
            res[key] = s
            if s["testable"]:
                print(f"  {v:<15}{label:<26}{s['weeks']:>7}{s['mean']*100:>+8.3f}%{s['t']:>+7.2f}  {s['halves'][0]*100:+.3f}/{s['halves'][1]*100:+.3f}  {s['median']*100:>+7.3f}  {'YES' if s['has_edge'] else 'no'}")
            else:
                print(f"  {v:<15}{label:<26}{s['weeks']:>7}  untestable")
        d = team[v]
        half = len(d) // 2
        tt = lab._tstat(d) if len(d) > 2 else 0.0
        adds = bool(tt >= 2 and statistics.fmean(d[:half]) > 0 and statistics.fmean(d[half:]) > 0)
        res["team"] = {"weeks": len(d), "mean_diff": statistics.fmean(d), "t": tt, "halves": [statistics.fmean(d[:half]), statistics.fmean(d[half:])], "adds": adds}
        print(f"  {v:<15}{'four chairs minus three':<26}{len(d):>7}{res['team']['mean_diff']*100:>+8.3f}%{tt:>+7.2f}  {res['team']['halves'][0]*100:+.3f}/{res['team']['halves'][1]*100:+.3f}  {'':>7}  {'ADDS' if adds else 'no'}")
        result["variants"][v] = res
    result["verdicts"] = {f"{v} {k}": bool(result["variants"][v][k].get("has_edge")) for v in VARIANTS for k in ("hold1_pool", "hold4_pool")}
    result["verdicts"].update({f"{v} team": result["variants"][v]["team"]["adds"] for v in VARIANTS})
    print("\n  registered verdicts: " + "; ".join(f"{k} {'YES' if ok else 'no'}" for k, ok in result["verdicts"].items()))
    result["weekly_picks"] = weekly
    path = lab.CACHE / "pass23.smoke.json" if smoke else lab.RESULTS / ("pass23_drift_chair_fixed.json" if FIXED else "pass23_drift_chair.json")
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"  wrote {path}")


if __name__ == "__main__":
    FIXED = "fixed" in sys.argv[1:]
    main(smoke=sys.argv[1:] == ["smoke"])
