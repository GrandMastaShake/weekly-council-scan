#!/usr/bin/env python3
"""Pass 14 -- the weekly screen as Marky's chair, and his universe.

The owner's daily screen (screen/daily_screen.py: a rising 120-day channel,
a pullback into its lower half, the MACD histogram crossing up or turning,
and "clean air" above) is Marky's job done daily on small and mid caps. Two
questions. Run weekly on Friday's close, is it a better Marky than the
channel five (Pass 5)? And should Marky have a bigger universe than the 111?

Three universes, each scored against its own random books:
  the 111                   its 109 stocks; no cap or liquidity rule
  the S&P 500 as of 2024-09 463 names, the clean list
  the screen's list         lab/universe_smid_2026-09-23.csv: today's listing
                            at $300M to $10B and $3 or more, rate-sensitive
                            names out as the screen drops them, and the
                            screen's $5M-a-day rule applied point in time
                            from the trailing 20 sessions. Names are on it
                            because they are that size today (survivorship,
                            stated); within-universe comparisons only.

Books each week, from the screen's own analyze() and tier() on the raw
daily closes up to the Friday before (the closes it reads live):
  Screen A       Tier A names, up to five, in the screen's order (least
                 overhead first, nearest exit first)
  Screen A+B     up to five across Tier A then B, same order
  Screen C       the almost-there names, up to five
  Marky channel  Pass 5's channel five on the same universe (the baseline)

Scoring as in Passes 9-13: clipped edge over random books of the same size
from the week's tradeable names (earnings blackout) in the same universe.
Plus the screen's own trade, on adjusted closes: entry at Monday's open,
exit at the first close below the name's 40-day low as of the signal, else
week 8's Friday close; against random names from the same pool traded the
same way with their own 40-day lows; the edge per trade and per week held
(costs cancel against a random book traded the same way). The t for the
trade uses every eighth pick week so the trades do not overlap.

Registered in lab/README.md before any run.

    python lab/pass14_screen_marky.py
    python lab/pass14_screen_marky.py smoke
"""
from __future__ import annotations

import bisect
import csv
import json
import random
import statistics
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB.parent / "screen"))
import daily_screen as ds  # noqa: E402
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass7_combos as p7  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass10_sectors as p10  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402

SMID_CSV = LAB / "universe_smid_2026-09-23.csv"
SMID = "the screen's list"
BOOKS = ("Screen A", "Screen A+B", "Screen C", "Marky channel")
LIQ_DAYS = 20
SWING_WEEKS = 8
DRAWS = 200


def smid_list():
    with open(SMID_CSV, encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))]
    return sorted(r["ticker"] for r in rows
                  if "RATE-SENSITIVE" not in ds.flags({"sector": r["sector"], "industry": r["industry"]}))


def signals(names, raw, W, tset, liquidity):
    """The screen's rows for the week: tier, overhead, exit distance, the 40-day low."""
    rows = []
    for t in names:
        if t not in tset or t not in raw:
            continue
        bars = raw[t].before(W, 800)
        c = [b["close"] for b in bars][-504:]
        if len(c) < 260:
            continue
        if liquidity and statistics.fmean(b["close"] * b["volume"] for b in bars[-LIQ_DAYS:]) < ds.DOLLAR_VOL_MIN:
            continue
        try:
            a = ds.analyze(c)
        except Exception:
            continue
        tr = ds.tier(a)
        if tr:
            rows.append({"tier": tr, "ticker": t, "overhead": a["over"], "exit_dist": (a["lo40"] / a["px"] - 1) * 100})
    rows.sort(key=lambda r: (r["tier"], r["overhead"], -r["exit_dist"]))
    return rows


def lo40_adj(s, W):
    c = [b["close"] for b in s.before(W, 90)]
    return min(c[-41:-1]) if len(c) >= 41 else None


def swing(s, W, lo40):
    """(return, sessions held, exited) for one name: Monday's open to the first
    close below lo40, else the Friday close of week 8."""
    lo = bisect.bisect_left(s.dates, W)
    hi = bisect.bisect_right(s.dates, lab._plus(W, 7 * (SWING_WEEKS - 1) + 4))
    if lo >= hi:
        return None
    entry = s.rows[lo]["open"]
    for i in range(lo, hi):
        if s.rows[i]["close"] < lo40:
            return s.rows[i]["close"] / entry - 1.0, i - lo + 1, True
    return s.rows[hi - 1]["close"] / entry - 1.0, hi - lo, False


def replay(uname, names, weeks, cal, raw, adj, liquidity, tag):
    out = []
    for i, (label, W, _) in enumerate(weeks):
        tradeable = p10.pool(names, raw, cal, W)
        tset = set(tradeable)
        rows = signals(names, raw, W, tset, liquidity)
        pool = [t for t in tradeable if t in raw and len(raw[t].before(W, 800)) >= 260] if not liquidity else \
               [t for t in tradeable if t in raw and len(raw[t].before(W, 800)) >= 260
                and statistics.fmean(b["close"] * b["volume"] for b in raw[t].before(W, 800)[-LIQ_DAYS:]) >= ds.DOLLAR_VOL_MIN]
        if len(pool) < 20:
            continue
        eligible = [t for t in names if t in raw]
        books = {"Screen A": [r["ticker"] for r in rows if r["tier"] == "A"][:p7.TOP],
                 "Screen A+B": [r["ticker"] for r in rows if r["tier"] in "AB"][:p7.TOP],
                 "Screen C": [r["ticker"] for r in rows if r["tier"] == "C"][:p7.TOP],
                 "Marky channel": [t for t in p7.channel_ranking(raw, eligible, W, set(pool))][:p7.TOP]}
        week = {"week": label, "i": i, "spy": adj["SPY"].week_return(W) or 0.0, "signals": len(rows),
                "tiers": {t: sum(1 for r in rows if r["tier"] == t) for t in "ABC"}, "pool": len(pool),
                "fives": books,
                "books": p7.score_week({b: p7.equal(v) for b, v in books.items()}, adj, W, pool, f"p14-{uname}-{tag}")}
        # the screen's own trade, every name in the pool once, then books and random draws
        trades = {}
        for t in pool:
            if t in adj:
                lo = lo40_adj(adj[t], W)
                res = swing(adj[t], W, lo) if lo else None
                if res:
                    trades[t] = res
        tpool = sorted(trades)
        week["swing"] = {}
        for b, names_b in books.items():
            picks = [t for t in names_b if t in trades]
            if not picks or len(tpool) < 20:
                continue
            rng = random.Random(f"{lab.SEED}-{W}-p14swing-{uname}-{tag}-{b}")
            draws = [rng.sample(tpool, len(picks)) for _ in range(DRAWS)]
            r_book = statistics.fmean(trades[t][0] for t in picks)
            held = statistics.fmean(trades[t][1] for t in picks) / 5.0
            r_rand = statistics.fmean(statistics.fmean(trades[t][0] for t in d) for d in draws)
            held_rand = statistics.fmean(statistics.fmean(trades[t][1] for t in d) for d in draws) / 5.0
            week["swing"][b] = {"ret": r_book, "weeks_held": held, "exited": statistics.fmean(1.0 if trades[t][2] else 0.0 for t in picks),
                                "random_ret": r_rand, "random_weeks_held": held_rand,
                                "edge": r_book - r_rand, "edge_per_week": (r_book - r_rand) / max(held, 0.2)}
        out.append(week)
    return out


def summarize(rows):
    s = {}
    for b in BOOKS:
        rs = [(r["i"], r["books"][b], r.get("swing", {}).get(b)) for r in rows if b in r["books"]]
        if not rs:
            continue
        e = [x["clipped"]["edge"] for _, x, _ in rs]
        ret = [x["raw"]["ret"] for _, x, _ in rs]
        half = len(e) // 2
        sw = [(i, w) for i, _, w in rs if w]
        ind = [w for i, w in sw if i % SWING_WEEKS == 0]
        s[b] = {"weeks": len(rs), "edge": statistics.fmean(e), "t": lab._tstat(e),
                "ahead": sum(1 for x in e if x > 0),
                "halves": [statistics.fmean(e[:half]), statistics.fmean(e[half:])] if half else None,
                "raw_edge": statistics.fmean(x["raw"]["edge"] for _, x, _ in rs),
                "mean_ret": statistics.fmean(ret), "sd": statistics.pstdev(ret), "max_dd": lab._curve(ret)[1],
                "names": statistics.fmean(len(r["fives"][b]) for r in rows if b in r["books"]),
                "swing": None}
        if sw:
            s[b]["swing"] = {"weeks": len(sw), "edge": statistics.fmean(w["edge"] for _, w in sw),
                             "edge_per_week": statistics.fmean(w["edge_per_week"] for _, w in sw),
                             "weeks_held": statistics.fmean(w["weeks_held"] for _, w in sw),
                             "exited": statistics.fmean(w["exited"] for _, w in sw),
                             "t_independent": lab._tstat([w["edge"] for w in ind]) if len(ind) > 2 else None,
                             "n_independent": len(ind)}
    s["signals_per_week"] = statistics.fmean(r["signals"] for r in rows)
    s["tiers_per_week"] = {t: statistics.fmean(r["tiers"][t] for r in rows) for t in "ABC"}
    s["pool_per_week"] = statistics.fmean(r["pool"] for r in rows)
    return s


def paired(rows_a, rows_b, a, b):
    by = {r["week"]: r["books"][b]["clipped"]["edge"] for r in rows_b if b in r["books"]}
    diff = [r["books"][a]["clipped"]["edge"] - by[r["week"]] for r in rows_a if a in r["books"] and r["week"] in by]
    if len(diff) < 3:
        return None
    half = len(diff) // 2
    same = [1.0 if set(ra["fives"][a]) == set(rb["fives"][b]) else 0.0
            for ra in rows_a for rb in rows_b if ra["week"] == rb["week"] and a in ra["books"] and b in rb["books"]]
    return {"mean": statistics.fmean(diff), "t": lab._tstat(diff), "weeks_better": sum(1 for x in diff if x > 0),
            "weeks": len(diff), "halves": [statistics.fmean(diff[:half]), statistics.fmean(diff[half:])],
            "same_five": statistics.fmean(same) if same else None}


def show(title, s, pairs):
    print(f"\n  {title}: {s['signals_per_week']:.1f} signals a week (A {s['tiers_per_week']['A']:.1f}, "
          f"B {s['tiers_per_week']['B']:.1f}, C {s['tiers_per_week']['C']:.1f}); pool {s['pool_per_week']:.0f}")
    print(f"  {'book':<14}{'edge/wk':>9}{'t':>7}{'ahead':>8}{'names':>7}{'ret/wk':>8}{'SD':>7}{'max DD':>8}   swing: edge/trade, per wk held, held, exited, t(ind)")
    for b in BOOKS:
        x = s.get(b)
        if not x:
            continue
        sw = x["swing"]
        tail = (f"   {sw['edge']*100:+.2f}%, {sw['edge_per_week']*100:+.2f}%/wk, {sw['weeks_held']:.1f} wks, "
                f"{sw['exited']:.0%}, t {sw['t_independent'] if sw['t_independent'] is None else round(sw['t_independent'], 2)} (n {sw['n_independent']})") if sw else ""
        print(f"  {b:<14}{x['edge']*100:+8.2f}%{x['t']:+7.2f}{x['ahead']:>5}/{x['weeks']:<3}{x['names']:6.1f}{x['mean_ret']*100:+7.2f}%"
              f"{x['sd']*100:6.2f}%{x['max_dd']*100:+7.1f}%{tail}")
    for k, p in pairs.items():
        if p:
            print(f"  paired {k:<34}{p['mean']*100:+.2f}%/wk (t {p['t']:+.2f}, {p['weeks_better']}/{p['weeks']}"
                  + (f"; same five {p['same_five']:.0%}" if p["same_five"] is not None else "") + ")")


def main(smoke=False):
    U = p9.universes()
    universes = {p9.REFERENCE: (U[p9.REFERENCE], False), p11.CLEAN: (p9.sp500_asof(), False), SMID: (smid_list(), True)}
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    cweeks = lab.council_weeks(p9._last_friday())
    if smoke:
        universes, hweeks, cweeks = {p9.REFERENCE: universes[p9.REFERENCE]}, hweeks[:3], cweeks[:1]
    end = lab._plus(cweeks[-1][1], 5)
    result = {"universes": {}, "swing_weeks": SWING_WEEKS}
    hist_all = {}
    for uname, (names, liquidity) in universes.items():
        cal = lab.earnings_calendar(names)
        tickers = sorted(set(names)) + lab.EXTRA
        raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
        adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, p4.HIST_START)).items()}
        print(f"  {uname}: {len(names)} names, {len([t for t in names if t in raw and raw[t].rows])} with prices", flush=True)
        hist = replay(uname, names, hweeks, cal, raw, adj, liquidity, "hist")
        cw = replay(uname, names, cweeks, cal, raw, adj, liquidity, "council")
        hist_all[uname] = hist
        hs, cs = summarize(hist), summarize(cw)
        hp = {"Screen A+B vs Marky channel": paired(hist, hist, "Screen A+B", "Marky channel"),
              "Screen A vs Screen A+B": paired(hist, hist, "Screen A", "Screen A+B")}
        cp = {"Screen A+B vs Marky channel": paired(cw, cw, "Screen A+B", "Marky channel")}
        show(f"{uname}: history, {len(hist)} weeks", hs, hp)
        show(f"{uname}: Council weeks, {len(cw)} (seen; decide nothing)", cs, cp)
        result["universes"][uname] = {"names": len(names), "liquidity_rule": liquidity,
                                      "history": {"summary": hs, "paired": hp, "weeks": hist},
                                      "council": {"summary": cs, "paired": cp, "weeks": cw}}
    across = {}
    if SMID in hist_all and p9.REFERENCE in hist_all:
        for b in ("Screen A+B", "Marky channel"):
            across[b] = paired(hist_all[SMID], hist_all[p9.REFERENCE], b, b)
            if across[b]:
                print(f"  across universes, {b}: the screen's list minus the 111, {across[b]['mean']*100:+.2f}%/wk (t {across[b]['t']:+.2f})")
    result["across"] = across
    v = {}
    for uname in result["universes"]:
        p = result["universes"][uname]["history"]["paired"]["Screen A+B vs Marky channel"]
        v[f"the screen is a better Marky on {uname}"] = bool(p and p["t"] >= 2 and p["mean"] > 0 and all(h > 0 for h in p["halves"]))
    if SMID in result["universes"]:
        x = result["universes"][SMID]["history"]["summary"]["Screen A+B"]
        a = across.get("Screen A+B")
        v["the bigger universe pays for Marky's job"] = bool(x["t"] >= 2 and x["edge"] > 0 and x["halves"] and all(h > 0 for h in x["halves"])
                                                             and a and a["t"] >= 2 and a["mean"] > 0)
    result["verdicts"] = v
    print("\n  registered verdicts (history): " + "; ".join(f"{k}: {'YES' if ok else 'no'}" for k, ok in v.items()))
    out = lab.CACHE / "pass14.smoke.json" if smoke else lab.RESULTS / "pass14_screen_marky.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
