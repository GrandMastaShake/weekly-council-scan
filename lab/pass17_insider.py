#!/usr/bin/env python3
"""Pass 17 -- a fourth chair: the Insider.

Open-market purchases by officers and directors (SEC Form 4, frozen in
lab/insider_purchases_2024q3_2026q2.csv by fetch_insiders.py), counted from
their filing date. Two books a week, up to five names from the week's
tradeable names:
  Insider clusters  2+ distinct directors or officers bought in the 30 days
                    before the Monday; most buyers first, then the largest total
  Insider buys      $100,000 or more bought in total in those 30 days; largest first
Scored as every member (weekly clipped edge over random books of the same size
from the same universe's tradeable names), on the S&P 500 as of 2024-09 and
the screen's small/mid list (decide) and the 111 (reported), 96 history
weeks; held 4 and 13 weeks beside (Pass 13's method). Its independence from
Ophelia, Cecil (with a P/E) and Marky, scored in the same run on the clean
list, and four chairs (a quarter each, the Insider's buys the fourth) against
three (a third each). Registered in lab/README.md before any run.

    python lab/pass17_insider.py
    python lab/pass17_insider.py smoke
"""
from __future__ import annotations

import bisect
import csv
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB.parent / "screen"))
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass7_combos as p7  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402
import pass13_hold_manage as p13  # noqa: E402
import pass14_screen_marky as p14  # noqa: E402
import pass15_exits as p15  # noqa: E402

PURCHASES_CSV = LAB / "insider_purchases_2024q3_2026q2.csv"
WINDOW_DAYS = 30
BUY_MIN = 100_000.0
INSIDER = ("Insider clusters", "Insider buys")
MEMBERS = ("Ophelia", "Cecil", "Marky")
CHAIRS = ("Three chairs", "Four chairs")
HORIZONS = (4, 13)
DRAWS = 200
DECIDES = (p11.CLEAN, p14.SMID)


def purchases():
    """{ticker: (sorted filing dates, [(owners, value)])}."""
    with open(PURCHASES_CSV, encoding="ascii") as fh:
        rows = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    by = defaultdict(list)
    for r in rows:
        by[r["ticker"]].append((r["filing_date"], frozenset(r["owners"].split(";")), float(r["value"])))
    out = {}
    for t, xs in by.items():
        xs.sort(key=lambda x: x[0])
        out[t] = ([x[0] for x in xs], [(x[1], x[2]) for x in xs])
    return out


def insider_books(buys, tradeable, W):
    lo = lab._plus(W, -WINDOW_DAYS)
    stats = {}
    for t in tradeable:
        rec = buys.get(t)
        if not rec:
            continue
        dates, items = rec
        i, j = bisect.bisect_left(dates, lo), bisect.bisect_left(dates, W)     # filed in [W-30, W)
        if i >= j:
            continue
        owners, value = set(), 0.0
        for own, v in items[i:j]:
            owners |= own
            value += v
        stats[t] = (len(owners), value)
    clusters = sorted((t for t, (n, _) in stats.items() if n >= 2), key=lambda t: (-stats[t][0], -stats[t][1], t))
    big = sorted((t for t, (_, v) in stats.items() if v >= BUY_MIN), key=lambda t: (-stats[t][1], t))
    books = {"Insider clusters": clusters[:p7.TOP], "Insider buys": big[:p7.TOP]}
    return books, {"with_purchases": len(stats), "clusters": len(clusters), "buys": len(big)}


def held(uname, W, names, pool, adj, k, tag):
    """(book mean, pool mean) of clipped k-week holds, per week of holding; None if the data ends first."""
    clip = 0.20 * k
    rets = {t: p13.hold_return(adj[t], W, k) for t in set(pool) | set(names) if t in adj}
    rets = {t: max(-clip, min(clip, r)) for t, r in rets.items() if r is not None}
    have = [t for t in names if t in rets]
    pl = [t for t in pool if t in rets]
    if not have or len(pl) < 20:
        return None
    rng = random.Random(f"{lab.SEED}-{W}-p17hold-{uname}-{tag}-{k}")
    draws = [statistics.fmean(rets[t] for t in rng.sample(pl, len(have))) for _ in range(DRAWS)]
    return (statistics.fmean(rets[t] for t in have) - statistics.fmean(draws)) / k


def run_universe(uname, names, weeks, buys):
    end = lab._plus(lab.council_weeks(p9._last_friday())[-1][1], 5)
    tickers = sorted(set(names)) + lab.EXTRA
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, p4.HIST_START)).items()}
    cal = lab.earnings_calendar(names)
    members = p15.books_for(uname)
    rows = []
    for i, (label, W, _) in enumerate(weeks):
        pool = p15.pool_for(uname, names, raw, cal, W)
        if len(pool) < 20:
            continue
        ins, cover = insider_books(buys, pool, W)
        tset = set(pool)
        mem = {m: [t for t in members.get(label, {}).get(m, []) if t in tset] for m in MEMBERS}
        weights = {b: p7.equal(v) for b, v in ins.items()}
        weights.update({m: p7.equal(v) for m, v in mem.items() if v})
        if all(mem[m] for m in MEMBERS):
            weights["Three chairs"] = p7.slices([mem[m] for m in MEMBERS])
            weights["Four chairs"] = p7.slices([mem[m] for m in MEMBERS] + [ins["Insider buys"]])
        row = {"week": label, "i": i, "cover": cover, "fives": dict(ins, **mem),
               "books": p7.score_week(weights, adj, W, pool, f"p17-{uname}"), "held": {}}
        for b in INSIDER:
            for k in HORIZONS:
                row["held"][f"{b} {k}"] = held(uname, W, ins[b], pool, adj, k, b) if ins[b] else None
        rows.append(row)
    return rows


def summarize(rows, min_weeks=10):
    s = {}
    for b in INSIDER + MEMBERS + CHAIRS:
        rs = [r for r in rows if b in r["books"]]
        if len(rs) < min_weeks:
            continue
        e = [r["books"][b]["clipped"]["edge"] for r in rs]
        ret = [r["books"][b]["raw"]["ret"] for r in rs]
        half = len(e) // 2
        s[b] = {"weeks": len(rs), "edge": statistics.fmean(e), "t": lab._tstat(e), "ahead": sum(1 for x in e if x > 0),
                "halves": [statistics.fmean(e[:half]), statistics.fmean(e[half:])],
                "raw_edge": statistics.fmean(r["books"][b]["raw"]["edge"] for r in rs),
                "sd": statistics.pstdev(ret), "max_dd": lab._curve(ret)[1],
                "names": statistics.fmean(len(r["fives"].get(b, [])) for r in rs) if b not in CHAIRS else None}
        if b in INSIDER:
            s[b]["held"] = {}
            for k in HORIZONS:
                xs = [(r["i"], r["held"][f"{b} {k}"]) for r in rows if r["held"].get(f"{b} {k}") is not None]
                ind = [x for i, x in xs if i % k == 0]
                s[b]["held"][k] = {"weeks": len(xs), "edge": statistics.fmean(x for _, x in xs) if xs else None,
                                   "t": lab._tstat(ind) if len(ind) > 2 else None, "independent": len(ind)}
    s["coverage"] = {k: statistics.fmean(r["cover"][k] for r in rows) for k in ("with_purchases", "clusters", "buys")}
    s["coverage"]["weeks_with_clusters"] = sum(1 for r in rows if r["fives"]["Insider clusters"])
    s["coverage"]["weeks_with_buys"] = sum(1 for r in rows if r["fives"]["Insider buys"])
    s["coverage"]["weeks"] = len(rows)
    return s


def independence(rows):
    out = {}
    for b in INSIDER:
        for m in MEMBERS:
            both = [r for r in rows if b in r["books"] and m in r["books"]]
            if len(both) < 10:
                continue
            x = [r["books"][b]["clipped"]["edge"] for r in both]
            y = [r["books"][m]["clipped"]["edge"] for r in both]
            shared = [len(set(r["fives"][b]) & set(r["fives"][m])) for r in both]
            out[f"{b} x {m}"] = {"weeks": len(both), "corr": statistics.correlation(x, y),
                                 "shared_per_week": statistics.fmean(shared)}
    return out


def paired(rows, a, b):
    rs = [r for r in rows if a in r["books"] and b in r["books"]]
    if len(rs) < 10:
        return None
    diff = [r["books"][a]["clipped"]["edge"] - r["books"][b]["clipped"]["edge"] for r in rs]
    half = len(diff) // 2
    return {"weeks": len(diff), "mean": statistics.fmean(diff), "t": lab._tstat(diff),
            "halves": [statistics.fmean(diff[:half]), statistics.fmean(diff[half:])],
            "weeks_better": sum(1 for x in diff if x > 0)}


def show(title, s, ind, team, decides):
    c = s["coverage"]
    print(f"\n  {title}{' (decides)' if decides else ''}")
    print(f"    coverage: {c['with_purchases']:.1f} tradeable names with purchases a week; clusters {c['clusters']:.1f} "
          f"(in {c['weeks_with_clusters']}/{c['weeks']} weeks); buys >= $100k {c['buys']:.1f} (in {c['weeks_with_buys']}/{c['weeks']} weeks)")
    print(f"    {'book':<18}{'edge/wk':>9}{'t':>7}{'ahead':>8}{'names':>7}{'halves':>15}{'raw':>8}{'SD':>7}{'max DD':>8}   held 4 / 13 wks (per wk, t)")
    for b, x in s.items():
        if b == "coverage":
            continue
        names = f"{x['names']:7.1f}" if x["names"] is not None else "       "
        tail = ""
        if "held" in x:
            tail = "   " + " / ".join(f"{h['edge']*100:+.2f}% (t {h['t']:+.2f})" if h["edge"] is not None and h["t"] is not None else "--"
                                     for h in x["held"].values())
        print(f"    {b:<18}{x['edge']*100:+8.2f}%{x['t']:+7.2f}{x['ahead']:>5}/{x['weeks']:<3}{names}"
              f"{x['halves'][0]*100:+7.2f}/{x['halves'][1]*100:+.2f}{x['raw_edge']*100:+7.2f}%{x['sd']*100:6.2f}%{x['max_dd']*100:+7.1f}%{tail}")
    for k, v in ind.items():
        print(f"    {k:<30} edge corr {v['corr']:+.2f}, names shared {v['shared_per_week']:.2f} a week ({v['weeks']} weeks)")
    if team:
        print(f"    four chairs minus three: {team['mean']*100:+.2f}%/wk (t {team['t']:+.2f}, {team['weeks_better']}/{team['weeks']}, "
              f"halves {team['halves'][0]*100:+.2f}/{team['halves'][1]*100:+.2f})")


def main(smoke=False):
    buys = purchases()
    U = p9.universes()
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    universes = {p11.CLEAN: p9.sp500_asof(), p14.SMID: p14.smid_list(), p9.REFERENCE: U[p9.REFERENCE]}
    if smoke:
        universes, hweeks = {p9.REFERENCE: U[p9.REFERENCE]}, hweeks[:6]
    result = {"window_days": WINDOW_DAYS, "buy_min": BUY_MIN, "horizons": HORIZONS, "universes": {}}
    for uname, names in universes.items():
        print(f"  {uname}: {len(names)} names", flush=True)
        rows = run_universe(uname, names, hweeks, buys)
        s = summarize(rows, min_weeks=3 if smoke else 10)
        ind = independence(rows)
        team = paired(rows, "Four chairs", "Three chairs")
        show(f"{uname}: {len(rows)} weeks", s, ind, team, uname in DECIDES)
        result["universes"][uname] = {"summary": s, "independence": ind, "four_minus_three": team, "weeks": rows}
    v = {}
    for uname in DECIDES:
        s = result["universes"].get(uname, {}).get("summary", {})
        for b in INSIDER:
            x = s.get(b)
            v[f"{b} beats random on {uname}"] = bool(x and x["t"] >= 2 and x["edge"] > 0 and all(h > 0 for h in x["halves"]))
    team = result["universes"].get(p11.CLEAN, {}).get("four_minus_three")
    v["a fourth chair adds to the team"] = bool(team and team["t"] >= 2 and team["mean"] > 0 and all(h > 0 for h in team["halves"]))
    result["verdicts"] = v
    print("\n  registered verdicts: " + "; ".join(f"{k}: {'YES' if ok else 'no'}" for k, ok in v.items()))
    out = lab.CACHE / "pass17.smoke.json" if smoke else lab.RESULTS / "pass17_insider.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
