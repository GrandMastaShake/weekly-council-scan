#!/usr/bin/env python3
"""Pass 25 -- the sector anchor on 27 years of SPDR sector ETFs (registered in lab/README.md, cebc16e).

Each Monday W from 1999: the fresh signal is each sector ETF's return over the Friday-to-Friday week that closed before W, the stale
signal the week before that; the target is the ETF's Monday-open to Friday-close return minus the equal-weight mean of the sectors
that exist. Scored by the weekly rank IC across the sectors and the top-three minus bottom-three spread of the target.

    python lab/pass25_sector_history.py
    python lab/pass25_sector_history.py smoke
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass15_exits as p15  # noqa: E402
import pass20_regimes as p20  # noqa: E402
import pass24_sector_score as p24  # noqa: E402

ETFS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "XLRE", "XLC"]
START = "1998-12-01"
FIRST_MONDAY = "1999-01-04"
MIN_SECTORS = 6
NW_LAGS = 4
ERAS = {"1999-2008": (1999, 2008), "2009-2017": (2009, 2017), "2018-2026": (2018, 2026)}
WINDOWS = {"2000-2002": (2000, 2002), "2007-2009": (2007, 2009), "2020": (2020, 2020), "2022": (2022, 2022)}


def mondays(first, last):
    out, d = [], first
    while d <= last:
        out.append(d)
        d = lab._plus(d, 7)
    return out


def week_row(W, adj):
    f1, f0, f_1 = W, lab._plus(W, -7), lab._plus(W, -14)
    fresh, stale, tgt = {}, {}, {}
    for t in ETFS:
        s = adj.get(t)
        if s is None:
            continue
        a, b, c = p24.span(s, f0, f1), p24.span(s, f_1, f0), s.week_return(W)
        if a is None or b is None or c is None:
            continue
        fresh[t], stale[t], tgt[t] = a[0], b[0], c
    if len(tgt) < MIN_SECTORS:
        return None
    mean_t = statistics.fmean(tgt.values())
    names = sorted(tgt)
    excess = {t: tgt[t] - mean_t for t in names}
    out = {"n": len(names)}
    top_bottom = {}
    for sig, vals in (("fresh", fresh), ("stale", stale)):
        out[sig] = lab.spearman([vals[t] for t in names], [excess[t] for t in names])
        order = sorted(names, key=lambda t: (vals[t], t))
        top_bottom[sig] = statistics.fmean(excess[t] for t in order[-3:]) - statistics.fmean(excess[t] for t in order[:3])
        out[sig + "_spread"] = top_bottom[sig]
    return out


def stat(xs):
    if len(xs) < 3:
        return {"weeks": len(xs)}
    half = len(xs) // 2
    return {"weeks": len(xs), "mean": statistics.fmean(xs), "t": p15.nw_t(xs, NW_LAGS),
            "halves": [statistics.fmean(xs[:half]), statistics.fmean(xs[half:])]}


def main(smoke=False):
    tickers = ETFS
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, p20.END, START)).items()}
    empty = [t for t in ETFS if t not in adj or len(adj[t].dates) < 1000]
    if empty:
        raise SystemExit(f"no bars for {empty}: delete the cached download in lab/cache and rerun")
    print("  first bar per ETF: " + ", ".join(f"{t} {adj[t].dates[0]}" for t in ETFS))
    first = "2018-06-04" if smoke else FIRST_MONDAY
    rows = []
    for W in mondays(first, "2026-09-21"):
        r = week_row(W, adj)
        if r is not None:
            r["W"] = W
            rows.append(r)
    print(f"  {len(rows)} weeks from {rows[0]['W']} to {rows[-1]['W']}; sectors per week {min(r['n'] for r in rows)} to {max(r['n'] for r in rows)}")
    result = {"registered": "cebc16e", "weeks": len(rows), "first": rows[0]["W"], "last": rows[-1]["W"], "signals": {}}
    for sig in ("fresh", "stale"):
        ic = [r[sig] for r in rows]
        sp = [r[sig + "_spread"] for r in rows]
        res = {"ic": stat(ic), "spread": stat(sp), "eras": {}, "windows": {}}
        for name, (a, b) in ERAS.items():
            sel = [r[sig] for r in rows if a <= int(r["W"][:4]) <= b]
            res["eras"][name] = stat(sel) if sel else {"weeks": 0}
        for name, (a, b) in WINDOWS.items():
            sel = [r[sig] for r in rows if a <= int(r["W"][:4]) <= b]
            res["windows"][name] = stat(sel) if sel else {"weeks": 0}
        eras_pos = all(res["eras"][e].get("mean", 0) > 0 for e in ERAS if res["eras"][e]["weeks"] >= 20)
        res["holds"] = bool(res["ic"]["mean"] > 0 and res["ic"]["t"] is not None and res["ic"]["t"] >= 2 and eras_pos)
        result["signals"][sig] = res
        print(f"\n  {sig} signal: mean IC {res['ic']['mean']:+.4f} (NW t {res['ic']['t']:+.2f}) over {res['ic']['weeks']} weeks, halves "
              f"{res['ic']['halves'][0]:+.4f} / {res['ic']['halves'][1]:+.4f}; top-3 minus bottom-3 {res['spread']['mean']*100:+.3f}%/wk (t {res['spread']['t']:+.2f})")
        for name, s in res["eras"].items():
            if s["weeks"] >= 3:
                print(f"    era {name}: IC {s['mean']:+.4f} (t {s['t']:+.2f}, {s['weeks']} weeks)")
        for name, s in res["windows"].items():
            if s["weeks"] >= 3:
                print(f"    window {name}: IC {s['mean']:+.4f} (t {s['t']:+.2f}, {s['weeks']} weeks)")
        print(f"    -> holds: {'YES' if res['holds'] else 'no'}")
    result["verdicts"] = {sig: result["signals"][sig]["holds"] for sig in ("fresh", "stale")}
    path = lab.CACHE / "pass25.smoke.json" if smoke else lab.RESULTS / "pass25_sector_history.json"
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")
    print(f"\n  wrote {path}")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
