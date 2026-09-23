#!/usr/bin/env python3
"""Pass 16 -- exits built on each stock's own levels.

The owner's refinements of Pass 15 (2026-09-23), registered before Pass 15's
output was read: a daily MACD exit; profit targets at each stock's own
resistance levels; a stop under a clear support level, scaled to the stock
when none is in range; the 9.3/18.6/27.9% ladder; and the owner's plan that
combines them with a breakeven stop and a volatility trail after the first
third, the MACD exit and the earnings exit. Pass 15's setup throughout (a
quarter per pick, sold money parked in SPY, resting-order fills on daily
bars, 0.05% a side, random picks under the same rule, Newey-West t with 12
lags, the median week must agree); Pass 15's rules are rerun beside the new
ones and must reproduce its numbers.

Levels, point in time, as the owner's screen finds its ceilings: a swing
high (low) is a close that is the highest (lowest) of the 21 closes centred
on it, usable only once the 10 closes after it exist.
  resistance  swing highs of the last two years 4% to 50% above the entry,
              levels within 3% merged, the nearest three; targets 1% under
  support     the nearest swing low of the last year 2% to 15% below the
              entry; the stop 1% under it, else 2 weekly SDs

    python lab/pass16_exits.py
    python lab/pass16_exits.py smoke
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
import daily_screen as ds  # noqa: E402
import engine_lab as lab  # noqa: E402
import pass4_marky as p4  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402
import pass14_screen_marky as p14  # noqa: E402
import pass15_exits as p15  # noqa: E402

LEVEL_W = 10
RES_LOOKBACK, SUP_LOOKBACK = 504, 250
RES_MIN, RES_MAX, RES_MERGE, RES_N = 0.04, 0.50, 0.03, 3
SUP_MIN, SUP_MAX = 0.02, 0.15
BUFFER = 0.01
FALLBACK_SD = 2.0
LADDER_TIGHT = ((0.093, 1 / 3), (0.186, 1 / 3), (0.279, 1 / 3))
PLAN = {"support_stop": True, "resistance_ladder": True, "lock": 0.0, "trail_after_first": 2.0,
        "macd_exit": True, "earnings": True}
NEW = {
    "MACD exit": {"macd_exit": True},
    "support stop": {"support_stop": True},
    "resistance ladder": {"resistance_ladder": True},
    "ladder 9.3/18.6/27.9": {"ladder": LADDER_TIGHT},
    "the owner's plan": PLAN,
    "the owner's plan, no MACD": {k: v for k, v in PLAN.items() if k != "macd_exit"},
    "the owner's plan, generic ladder": dict({k: v for k, v in PLAN.items() if k != "resistance_ladder"}, ladder=p15.LADDER),
}
REFERENCE = {k: p15.RULES[k] for k in ("plain", "stop -8%", "ladder", "trailing 10%", "earnings exit", "the owner's set")}
RULES = dict(REFERENCE, **NEW)
BASE = "plain"
BOOKS = p15.BOOKS
DECIDES = p15.DECIDES


# ---- a ticker's levels ----------------------------------------------------------------
class Ticker:
    """One name's daily bars with its swing points and daily MACD histogram, computed once."""

    def __init__(self, rows):
        self.rows = rows
        self.dates = [r[0] for r in rows]
        c = [r[4] for r in rows]
        self.closes = c
        w = LEVEL_W
        self.highs, self.lows = [], []
        for i in range(w, len(c) - w):
            seg = c[i - w:i + w + 1]
            if c[i] == max(seg):
                self.highs.append(i)
            if c[i] == min(seg):
                self.lows.append(i)
        m = [a - b for a, b in zip(ds.ema(c, 12), ds.ema(c, 26))]
        self.hist = [a - b for a, b in zip(m, ds.ema(m, 9))]

    def levels(self, i0, entry):
        """(resistance levels ascending, support or None) known at the open of session i0."""
        cut = i0 - 1 - LEVEL_W                   # a swing point needs its 10 later closes, all before the entry
        highs = sorted(self.closes[i] for i in self.highs
                       if i0 - RES_LOOKBACK <= i <= cut and entry * (1 + RES_MIN) <= self.closes[i] <= entry * (1 + RES_MAX))
        res = []
        for v in highs:
            if not res or v > res[-1] * (1 + RES_MERGE):
                res.append(v)
        lows = [self.closes[i] for i in self.lows
                if i0 - SUP_LOOKBACK <= i <= cut and entry * (1 - SUP_MAX) <= self.closes[i] <= entry * (1 - SUP_MIN)]
        return res[:RES_N], (max(lows) if lows else None)


class Pos:
    __slots__ = ("rows", "i0", "iend", "spy_end", "reports", "wsd", "res", "sup", "hist")


def position(t, W, tickers, spy, cal):
    tk = tickers.get(t)
    if not tk:
        return None
    base = p15.position(t, W, {t: tk.rows}, spy, cal)
    if not base:
        return None
    p = Pos()
    p.rows, p.i0, p.iend, p.spy_end, p.reports, p.wsd = base
    p.res, p.sup = tk.levels(p.i0, p.rows[p.i0][1])
    p.hist = tk.hist
    return p


# ---- one position under a rule (a superset of Pass 15's simulate) ----------------------
def simulate(rule, pos, spy):
    rows, i0, iend = pos.rows, pos.i0, pos.iend
    entry = rows[i0][1]
    rem, value, held = 1.0, 0.0, 0.0
    why = {}
    stop = entry * (1 + rule["stop"]) if rule.get("stop") is not None else None
    if rule.get("vol_stop"):
        stop = entry * (1 - rule["vol_stop"] * pos.wsd) if pos.wsd else None
    if rule.get("support_stop"):
        stop = (pos.sup * (1 - BUFFER) if pos.sup else
                entry * (1 - FALLBACK_SD * pos.wsd) if pos.wsd else None)
    if rule.get("resistance_ladder"):
        targets = [v * (1 - BUFFER) for v in pos.res]
        fracs = [1 / 3] * len(targets)
    else:
        targets = [entry * (1 + p) for p, _ in rule.get("ladder", ())]
        fracs = [f for _, f in rule.get("ladder", ())]
    k, lock_next, pending, hi = 0, False, None, None
    closes = []
    band, n = rule.get("stagnation") or (None, None)
    trail, taf, macd = rule.get("trail"), rule.get("trail_after_first"), rule.get("macd_exit")
    report = None
    if rule.get("earnings") and pos.reports:
        j = bisect.bisect_right(pos.reports, rows[i0][0])
        report = pos.reports[j] if j < len(pos.reports) else None

    def sell(frac, px, d, at, reason):
        nonlocal rem, value, held
        frac = min(frac, rem)
        if frac <= 1e-12:
            return
        s_in = spy.get((rows[d][0], at))
        value += frac * px / entry * (1 - p15.SIDE) * (pos.spy_end / s_in if s_in else 1.0)
        held += frac * (d - i0 + (1 if at == "close" else 0))
        rem -= frac
        why[reason] = why.get(reason, 0.0) + frac

    for d in range(i0, iend + 1):
        date, o, h, lo, c = rows[d]
        if d > i0:
            if pending:
                sell(rem, o, d, "open", pending)
                break
            if stop is not None and o <= stop:
                sell(rem, o, d, "open", "stop")
                break
            while k < len(targets) and o >= targets[k]:
                sell(fracs[k], o, d, "open", f"target {k + 1}")
                k += 1
                lock_next = True
            if rem <= 1e-12:
                break
        if stop is not None and lo <= stop:
            sell(rem, stop, d, "close", "stop")
            break
        while k < len(targets) and h >= targets[k]:
            sell(fracs[k], targets[k], d, "close", f"target {k + 1}")
            k += 1
            lock_next = True
        if rem <= 1e-12:
            break
        if d == iend:
            sell(rem, c, d, "close", "horizon")
            break
        if report and rows[d + 1][0] >= report:
            sell(rem, c, d, "close", "earnings")
            break
        hi = c if hi is None else max(hi, c)
        if trail and c < (1 - trail) * hi:
            pending = "trailing"
        if taf and k >= 1 and pos.wsd and c < hi * (1 - taf * pos.wsd):
            pending = "trailing"
        if macd and pos.hist[d - 1] > 0 >= pos.hist[d]:
            pending = "MACD"
        closes.append(c)
        if band and len(closes) > n:
            w = closes[-(n + 1):]
            if max(w) <= w[0] * (1 + band) and min(w) >= w[0] * (1 - band):
                pending = "stagnation"
        if lock_next and rule.get("lock") is not None:
            stop = max(stop or 0.0, entry * (1 + rule["lock"]))
        lock_next = False
    return value * (1 - p15.SIDE) - 1.0, held / 5.0, why


# ---- a universe ------------------------------------------------------------------------
def summarize(cohorts, trades, pool_trades, min_weeks=10):
    out = {}
    for b in BOOKS:
        rows = [c for c in cohorts if b in c["books"]]
        if len(rows) < min_weeks:
            continue
        out[b] = {}
        for rule in RULES:
            val = [c["books"][b][rule] - c["books"][b][BASE] for c in rows]
            rnd = [c["pool"][rule] - c["pool"][BASE] for c in rows]
            spy = [c["books"][b][rule] - c["spy"] for c in rows]
            edge = [c["books"][b][rule] - c["pool"][rule] for c in rows]
            half = len(val) // 2
            out[b][rule] = {"weeks": len(rows), "ret": statistics.fmean(c["books"][b][rule] for c in rows),
                            "value": statistics.fmean(val), "t": p15.nw_t(val),
                            "median": statistics.median(val), "weeks_better": sum(1 for x in val if x > 0),
                            "halves": [statistics.fmean(val[:half]), statistics.fmean(val[half:])],
                            "on_random": statistics.fmean(rnd), "on_random_t": p15.nw_t(rnd),
                            "skill": statistics.fmean(val) - statistics.fmean(rnd),
                            "vs_spy": statistics.fmean(spy), "vs_spy_t": p15.nw_t(spy),
                            "edge_vs_random": statistics.fmean(edge), "edge_t": p15.nw_t(edge),
                            "trades": p15.trade_stats(trades[b][rule]), "random_trades": p15.trade_stats(pool_trades[rule])}
    return out


def run_universe(uname, names, weeks, smoke=False):
    end = lab._plus(lab.council_weeks(p9._last_friday())[-1][1], 5)
    tickers_list = sorted(set(names)) + lab.EXTRA
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers_list, False, end, p4.HIST_START)).items()}
    bars = p15.ohlc_by_ticker(lab.download(tickers_list, True, end, p4.HIST_START))
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
    cohorts, levels = [], {"book": [], "pool": []}
    trades = {b: {r: [] for r in RULES} for b in BOOKS}
    pool_trades = {r: [] for r in RULES}
    for label, W, _ in weeks:
        pool = p15.pool_for(uname, names, raw, cal, W)
        rng = random.Random(f"{lab.SEED}-{W}-p15-{uname}")      # Pass 15's sample, so its rules reproduce
        sample = sorted(rng.sample(pool, min(p15.POOL_SAMPLE, len(pool))))
        book_names = {t for b in books[label].values() for t in b}
        sims = {}
        for t in set(sample) | book_names:
            if t not in tickers and t in bars:
                tickers[t] = Ticker(bars[t])
            pos = position(t, W, tickers, spy, cal)
            if pos:
                sims[t] = {rule: simulate(spec, pos, spy) for rule, spec in RULES.items()}
                levels["book" if t in book_names else "pool"].append((pos.sup is not None, len(pos.res)))
        s_rows = bars["SPY"]
        sd = [r[0] for r in s_rows]
        i0 = bisect.bisect_left(sd, W)
        iend = bisect.bisect_right(sd, lab._plus(W, 7 * (p15.HORIZON_WEEKS - 1) + 4)) - 1
        in_pool = [t for t in sample if t in sims]
        if len(in_pool) < 20:
            continue
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
    lv = {}
    for side, xs in levels.items():
        if xs:
            lv[side] = {"support_found": statistics.fmean(1.0 if s else 0.0 for s, _ in xs),
                        "resistance_levels": {str(n): sum(1 for _, r in xs if r == n) / len(xs) for n in range(RES_N + 1)}}
    return cohorts, summarize(cohorts, trades, pool_trades, min_weeks=3 if smoke else 10), lv


def reproduces_pass15(summaries):
    path = lab.RESULTS / "pass15_exits.json"
    if not path.exists():
        return None
    old = json.loads(path.read_text(encoding="utf-8"))["universes"]
    diffs = [abs(old[u]["summary"][b][r][k] - s[b][r][k])
             for u, s in summaries.items() if u in old
             for b in s if b in old[u]["summary"]
             for r in REFERENCE for k in ("value", "on_random", "vs_spy")]
    return max(diffs) < 1e-9 if diffs else None


def show(title, s, decides, lv):
    print(f"\n  {title}")
    for side, x in lv.items():
        print(f"    levels ({side} trades): support found {x['support_found']:.0%}; resistance levels 0/1/2/3: "
              + " / ".join(f"{x['resistance_levels'][str(n)]:.0%}" for n in range(RES_N + 1)))
    for b, rules in s.items():
        tag = " (decides)" if b in decides else ""
        p = rules[BASE]
        print(f"  {b}{tag}: {p['weeks']} weeks; the plain quarter {p['ret']*100:+.2f}% (vs SPY {p['vs_spy']*100:+.2f}%), "
              f"win rate {p['trades']['win_rate']:.0%}")
        print(f"    {'rule':<34}{'vs plain':>9}{'t':>7}{'median':>8}{'better':>8}{'halves':>15}{'random':>9}{'vs SPY':>9}"
              f"{'win':>6}{'avg win':>9}{'avg loss':>9}{'wks in':>7}{'stopped':>8}")
        for rule, x in rules.items():
            if rule == BASE:
                continue
            tr = x["trades"]
            mark = "  (Pass 15)" if rule in REFERENCE else ""
            print(f"    {rule:<34}{x['value']*100:+8.2f}%{x['t']:+7.2f}{x['median']*100:+7.2f}%{x['weeks_better']:>4}/{x['weeks']:<3}"
                  f"{x['halves'][0]*100:+7.2f}/{x['halves'][1]*100:+.2f}"
                  f"{x['on_random']*100:+8.2f}%{x['vs_spy']*100:+8.2f}%{tr['win_rate']:6.0%}{(tr['avg_win'] or 0)*100:+8.1f}%"
                  f"{(tr['avg_loss'] or 0)*100:+8.1f}%{tr['weeks_in']:7.1f}{tr['stopped']:8.0%}{mark}")


def main(smoke=False):
    U = p9.universes()
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    universes = {p11.CLEAN: p9.sp500_asof(), p9.REFERENCE: U[p9.REFERENCE], p14.SMID: p14.smid_list()}
    if smoke:
        universes = {p9.REFERENCE: U[p9.REFERENCE]}
    result = {"rules": RULES, "new": list(NEW), "reference": list(REFERENCE), "levels_config": {
        "w": LEVEL_W, "resistance": [RES_MIN, RES_MAX, RES_MERGE, RES_N, RES_LOOKBACK],
        "support": [SUP_MIN, SUP_MAX, SUP_LOOKBACK], "buffer": BUFFER, "fallback_sd": FALLBACK_SD}, "universes": {}}
    summaries = {}
    for uname, names in universes.items():
        print(f"  {uname}: {len(names)} names", flush=True)
        cohorts, s, lv = run_universe(uname, names, hweeks, smoke)
        show(f"{uname}: {len(cohorts)} pick weeks, each held up to a quarter", s, DECIDES.get(uname, ()), lv)
        result["universes"][uname] = {"summary": s, "levels": lv, "cohorts": cohorts}
        summaries[uname] = s
    rep = None if smoke else reproduces_pass15(summaries)
    result["reproduces_pass15"] = rep
    print(f"\n  Pass 15's rules reproduce its numbers: {rep}")
    v = {}
    for uname, books in DECIDES.items():
        s = summaries.get(uname, {})
        for b in books:
            for rule in NEW:
                x = (s.get(b) or {}).get(rule)
                if x:
                    v[f"{rule} helps {b} on {uname}"] = bool(x["t"] is not None and x["t"] >= 2 and x["value"] > 0
                                                             and x["median"] > 0 and all(h > 0 for h in x["halves"]))
    result["verdicts"] = v
    hits = [k for k, ok in v.items() if ok]
    print("  registered verdicts: " + (", ".join(hits) if hits else "none helps"))
    out = lab.CACHE / "pass16.smoke.json" if smoke else lab.RESULTS / "pass16_exits.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
