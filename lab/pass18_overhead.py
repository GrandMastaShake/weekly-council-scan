#!/usr/bin/env python3
"""Pass 18 -- how much to sell at each level: overhead supply.

The owner's question after Passes 15 and 16: the exit rules won more often
without making more; does the overhead at a level say how much to sell
there? Supply at a level, point in time: of the shares traded in the two
years before the entry at closes 4% to 50% above the entry (the overhead
zone), the share traded within +/-3% of the level (each day to its nearest
level). Levels, fills and setup are Pass 16's: a quarter per pick, sold
money waiting in SPY, the nearest three swing highs as levels, targets 1%
under them.

  Part A  every first touch of a level during the quarter: the return from
          the fill to the quarter's end minus SPY's, against the level's
          supply share; OLS slope with errors clustered by pick week, on
          random picks from each week's pool (the members' picks beside)
  Part B  supply-weighted ladder  sell each level's supply share there
          supply-shaped thirds    Pass 16's total (a third per level found),
                                  split across the levels by supply
          against the plain quarter and Pass 16's resistance ladder

Registered in lab/README.md before any run.

    python lab/pass18_overhead.py
    python lab/pass18_overhead.py smoke
"""
from __future__ import annotations

import bisect
import json
import random
import statistics
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB.parent / "screen"))
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402
import pass14_screen_marky as p14  # noqa: E402
import pass15_exits as p15  # noqa: E402
import pass16_exits as p16  # noqa: E402

BAND = 0.03
RULES = ("plain", "resistance ladder", "supply-weighted ladder", "supply-shaped thirds")
BASE = "plain"
BOOKS = p15.BOOKS
DECIDES = {p11.CLEAN: ("Ophelia", "Cecil", "Marky", "Union"), p14.SMID: ("Screen A+B",)}


def volumes(df):
    """{ticker: {date: shares traded}} from the cached adjusted frame."""
    dates = [x.strftime("%Y-%m-%d") for x in df.index]
    out = {}
    for t in set(df.columns.get_level_values(1)):
        v = df["Volume"][t].values
        out[t] = {d: float(x) for d, x in zip(dates, v) if x == x}
    return out


def supply(pos, vol):
    """(supply share per level, overhead-zone volume, share of past closes above the entry)."""
    rows, i0 = pos.rows, pos.i0
    entry = rows[i0][1]
    lo, hi = entry * (1 + p16.RES_MIN), entry * (1 + p16.RES_MAX)
    levels = pos.res
    at = [0.0] * len(levels)
    total, above, n = 0.0, 0, 0
    for d in range(max(0, i0 - p16.RES_LOOKBACK), i0):
        date, c = rows[d][0], rows[d][4]
        n += 1
        above += c > entry
        if lo <= c <= hi:
            v = vol.get(date, 0.0)
            total += v
            if levels:
                j = min(range(len(levels)), key=lambda k: abs(c - levels[k]))
                if abs(c - levels[j]) <= BAND * levels[j]:
                    at[j] += v
    return [a / total if total > 0 else 0.0 for a in at], total, (above / n if n else 0.0)


def rules_for(pos, shares):
    entry = pos.rows[pos.i0][1]
    tgt = [L * (1 - p16.BUFFER) / entry - 1 for L in pos.res]
    n = len(tgt)
    tot = sum(shares)
    shaped = [n / 3 * s / tot for s in shares] if tot > 0 else [1 / 3] * n
    return {"plain": p16.RULES["plain"], "resistance ladder": p16.RULES["resistance ladder"],
            "supply-weighted ladder": {"ladder": tuple(zip(tgt, shares))},
            "supply-shaped thirds": {"ladder": tuple(zip(tgt, shaped))}}


def touches(pos, spy, shares, over):
    rows, i0, iend = pos.rows, pos.i0, pos.iend
    out = []
    for k, L in enumerate(pos.res):
        tp = L * (1 - p16.BUFFER)
        for d in range(i0, iend + 1):
            date, o, h, lo, c = rows[d]
            if d > i0 and o >= tp:
                fill, at = o, "open"
            elif h >= tp:
                fill, at = tp, "close"
            else:
                continue
            s_in = spy.get((date, at))
            if s_in:
                out.append({"level": k + 1, "supply": shares[k], "overhead_days": over, "days_in": d - i0,
                            "excess": (rows[iend][4] / fill - 1.0) - (pos.spy_end / s_in - 1.0)})
            break
    return out


def slope(pts):
    """OLS slope of excess on supply, standard error clustered by pick week."""
    if len(pts) < 30:
        return None
    x = [p["supply"] for p in pts]
    y = [p["excess"] for p in pts]
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx <= 0:
        return None
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    clusters = {}
    for p, a, c in zip(pts, x, y):
        clusters[p["week"]] = clusters.get(p["week"], 0.0) + (a - mx) * ((c - my) - b * (a - mx))
    se = (sum(v * v for v in clusters.values())) ** 0.5 / sxx
    terc = sorted(pts, key=lambda p: p["supply"])
    k = len(terc) // 3
    groups = {"low": terc[:k], "mid": terc[k:2 * k], "high": terc[2 * k:]}
    return {"touches": len(pts), "weeks": len(clusters), "slope": b, "t": b / se if se > 0 else 0.0,
            "no_supply_share": sum(1 for a in x if a == 0) / len(x),
            "terciles": {g: {"supply": statistics.fmean(p["supply"] for p in v),
                             "excess": statistics.fmean(p["excess"] for p in v)} for g, v in groups.items() if v}}


def run_universe(uname, names, weeks, smoke=False):
    end = lab._plus(lab.council_weeks(p9._last_friday())[-1][1], 5)
    tickers_list = sorted(set(names)) + lab.EXTRA
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers_list, False, end, p4.HIST_START)).items()}
    frame = lab.download(tickers_list, True, end, p4.HIST_START)
    bars = p15.ohlc_by_ticker(frame)
    vol = volumes(frame)
    spy = {}
    for d, o, h, lo, c in bars["SPY"]:
        spy[(d, "open")], spy[(d, "close")] = o, c
    cal = lab.earnings_calendar(names)
    books = p15.books_for(uname)
    last_fri = bars["SPY"][-1][0]
    weeks = [w for w in weeks if lab._plus(w[1], 7 * (p15.HORIZON_WEEKS - 1) + 4) <= last_fri and w[0] in books]
    if smoke:
        weeks = weeks[:6]
    tickers = {}
    cohorts, pool_touch, book_touch = [], [], []
    trades = {b: {r: [] for r in RULES} for b in BOOKS}
    pool_trades = {r: [] for r in RULES}
    for label, W, _ in weeks:
        pool = p15.pool_for(uname, names, raw, cal, W)
        rng = random.Random(f"{lab.SEED}-{W}-p15-{uname}")        # Pass 15's sample
        sample = sorted(rng.sample(pool, min(p15.POOL_SAMPLE, len(pool))))
        book_names = {t for b in books[label].values() for t in b}
        sims = {}
        for t in set(sample) | book_names:
            if t not in tickers and t in bars:
                tickers[t] = p16.Ticker(bars[t])
            pos = p16.position(t, W, tickers, spy, cal)
            if not pos:
                continue
            shares, _, over = supply(pos, vol.get(t, {}))
            sims[t] = {rule: p16.simulate(spec, pos, spy) for rule, spec in rules_for(pos, shares).items()}
            for x in touches(pos, spy, shares, over):
                x["week"] = label
                if t in sample:
                    pool_touch.append(x)
                if t in book_names:
                    book_touch.append(dict(x, ticker=t))
        in_pool = [t for t in sample if t in sims]
        if len(in_pool) < 20:
            continue
        s_rows = bars["SPY"]
        sd = [r[0] for r in s_rows]
        i0 = bisect.bisect_left(sd, W)
        iend = bisect.bisect_right(sd, lab._plus(W, 7 * (p15.HORIZON_WEEKS - 1) + 4)) - 1
        coh = {"week": label, "spy": s_rows[iend][4] / s_rows[i0][1] - 1.0, "books": {}, "pool": {}}
        for rule in RULES:
            coh["pool"][rule] = statistics.fmean(sims[t][rule][0] for t in in_pool)
            pool_trades[rule].extend(sims[t][rule] for t in in_pool)
        for b, picks in books[label].items():
            have = [t for t in picks if t in sims]
            if b not in BOOKS or not have:
                continue
            coh["books"][b] = {rule: statistics.fmean(sims[t][rule][0] for t in have) for rule in RULES}
            for rule in RULES:
                trades[b][rule].extend(sims[t][rule] for t in have)
        cohorts.append(coh)
    return cohorts, trades, pool_trades, pool_touch, book_touch


def book_summary(cohorts, trades, min_weeks):
    out = {}
    for b in BOOKS:
        rows = [c for c in cohorts if b in c["books"]]
        if len(rows) < min_weeks:
            continue
        out[b] = {}
        pairs = {r: BASE for r in RULES if r != BASE}
        pairs["shaped minus thirds"] = ("supply-shaped thirds", "resistance ladder")
        pairs["weighted minus shaped"] = ("supply-weighted ladder", "supply-shaped thirds")
        for name, ref in pairs.items():
            a, z = ref if isinstance(ref, tuple) else (name, ref)
            val = [c["books"][b][a] - c["books"][b][z] for c in rows]
            rnd = [c["pool"][a] - c["pool"][z] for c in rows]
            half = len(val) // 2
            x = {"weeks": len(val), "value": statistics.fmean(val), "t": p15.nw_t(val),
                 "median": statistics.median(val), "weeks_better": sum(1 for v in val if v > 0),
                 "halves": [statistics.fmean(val[:half]), statistics.fmean(val[half:])],
                 "on_random": statistics.fmean(rnd)}
            if not isinstance(ref, tuple):
                tr = p15.trade_stats(trades[b][name])
                x["sold_at_targets"] = sum(v for k, v in tr["reasons"].items() if k.startswith("target"))
                x["win_rate"], x["sd"] = tr["win_rate"], tr["sd"]
            out[b][name] = x
    return out


def main(smoke=False):
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    universes = {p11.CLEAN: p9.sp500_asof(), p14.SMID: p14.smid_list()}
    if smoke:
        universes = {p11.CLEAN: universes[p11.CLEAN]}
    result = {"band": BAND, "rules": list(RULES), "universes": {}}
    for uname, names in universes.items():
        print(f"  {uname}: {len(names)} names", flush=True)
        cohorts, trades, pool_trades, pool_touch, book_touch = run_universe(uname, names, hweeks, smoke)
        a_pool, a_book = slope(pool_touch), slope(book_touch)
        bs = book_summary(cohorts, trades, 3 if smoke else 10)
        print(f"\n  {uname}: {len(cohorts)} pick weeks")
        for name, a in (("random picks", a_pool), ("the members' picks", a_book)):
            if a:
                terc = "; ".join(f"{g} supply {v['supply']:.0%}: {v['excess']*100:+.2f}%" for g, v in a["terciles"].items())
                print(f"    Part A, {name}: {a['touches']} touches in {a['weeks']} weeks ({a['no_supply_share']:.0%} with no supply); "
                      f"slope {a['slope']*100:+.2f} points of excess per 100% supply (clustered t {a['t']:+.2f}); {terc}")
        for b, rules in bs.items():
            tag = " (decides)" if b in DECIDES.get(uname, ()) else ""
            print(f"    {b}{tag}")
            for name, x in rules.items():
                extra = (f", sold at targets {x['sold_at_targets']:.0%}, win {x['win_rate']:.0%}"
                         if "sold_at_targets" in x else "")
                print(f"      {name:<26}{x['value']*100:+7.2f}% (t {x['t']:+.2f}, median {x['median']*100:+.2f}%, "
                      f"{x['weeks_better']}/{x['weeks']}, halves {x['halves'][0]*100:+.2f}/{x['halves'][1]*100:+.2f}; "
                      f"random {x['on_random']*100:+.2f}%{extra})")
        result["universes"][uname] = {"part_a": {"random": a_pool, "members": a_book}, "part_b": bs,
                                      "cohorts": cohorts}
    v = {}
    for uname in DECIDES:
        u = result["universes"].get(uname)
        if not u:
            continue
        a = u["part_a"]["random"]
        v[f"supply predicts a stall on {uname}"] = bool(a and a["t"] <= -2)
        for b in DECIDES[uname]:
            for name in ("supply-weighted ladder", "supply-shaped thirds", "shaped minus thirds"):
                x = u["part_b"].get(b, {}).get(name)
                v[f"{name} helps {b} on {uname}"] = bool(x and x["t"] is not None and x["t"] >= 2 and x["value"] > 0
                                                         and x["median"] > 0 and all(h > 0 for h in x["halves"]))
    result["verdicts"] = v
    hits = [k for k, ok in v.items() if ok]
    print("\n  registered verdicts: " + (", ".join(hits) if hits else "none"))
    out = lab.CACHE / "pass18.smoke.json" if smoke else lab.RESULTS / "pass18_overhead.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
