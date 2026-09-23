#!/usr/bin/env python3
"""Pass 15 -- exits: the owner's selling rules.

The owner's rules for a multi-week position (2026-09-23): take profits a
third at +10%, a third at +20% and a third at +30%; sell everything at -8%;
once the first third is sold, sell the rest if it trails back to +5%; and
sell whatever has not moved more than 5% either way in two weeks. Every
pass so far exited on a schedule (the Council sells every Friday; Passes 13
and 14 held fixed windows or stopped at a 40-day low). This asks whether
rules like these improve a position held for up to a quarter.

Setup. Each pick is bought at its week's Monday open and given one quarter
(13 weeks). A rule decides when to sell; whatever it sells goes into SPY
until the quarter ends, so a rule is judged only on whether leaving the pick
beats staying in it, with the owner's benchmark as the place the money
waits. Fills on daily bars (adjusted open, high, low, close): resting orders
-- a stop or target inside the day's range fills at its price, an open
through it fills at the open, and a stop and a target on the same day count
the stop first; signals read on closes (stagnation, trailing) sell at the
next open; a stop moved after the first third takes effect the next
session. 0.05% a side on every purchase and sale of the pick; SPY is free.

Rules, the plain quarter as the baseline:
  plain                        hold the quarter
  stop -8%                     sell everything at -8%
  ladder                       a third at +10%, +20%, +30%
  ladder + stops               the ladder; -8% before the first third, +5% after it
  stagnation                   sell when the last ten closes stayed within 5%
                               either way of the close ten sessions before
  the owner's set              ladder + stops + stagnation
  trailing 10%                 sell at the next open after a close 10% below the
                               highest close since entry (lets winners run)
  stop 2 weekly SDs            a stop scaled to the name: 2 x (60-day daily SD x sqrt 5)
  earnings exit                sell at the close before the next earnings report
  the owner's set + earnings

Books, as earlier passes recorded them: Ophelia (Pass 9 / 9b), Cecil with a
point-in-time P/E (Pass 11), Marky's channel five and the owner's screen,
Tier A then B (Pass 14), and the union of the three members, on the S&P 500
as of 2024-09 (decides for the members), the screen's own list (decides for
the screen) and the 111 (reported). Random picks from the same week's pool
under the same rule (a seeded sample of up to 300) show what a rule does to
any stock. Quarters must end by 2026-09-18, so 94 pick weeks; consecutive
quarters overlap, so t is Newey-West with 12 lags. Quarter returns are not
clipped (a rule's value lives in the tails), so one +500% name can carry a
mean; a rule helps only if the median week agrees with the mean.

Registered in lab/README.md before any run.

    python lab/pass15_exits.py
    python lab/pass15_exits.py smoke
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
import pass10_sectors as p10  # noqa: E402
import pass11_cecil_themes as p11  # noqa: E402
import pass14_screen_marky as p14  # noqa: E402

HORIZON_WEEKS = 13
SIDE = 0.0005
POOL_SAMPLE = 300
NW_LAGS = HORIZON_WEEKS - 1
LADDER = ((0.10, 1 / 3), (0.20, 1 / 3), (0.30, 1 / 3))
OWNER = {"ladder": LADDER, "stop": -0.08, "lock": 0.05, "stagnation": (0.05, 10)}
RULES = {
    "plain": {},
    "stop -8%": {"stop": -0.08},
    "ladder": {"ladder": LADDER},
    "ladder + stops": {"ladder": LADDER, "stop": -0.08, "lock": 0.05},
    "stagnation": {"stagnation": (0.05, 10)},
    "the owner's set": OWNER,
    "trailing 10%": {"trail": 0.10},
    "stop 2 weekly SDs": {"vol_stop": 2.0},
    "earnings exit": {"earnings": True},
    "the owner's set + earnings": dict(OWNER, earnings=True),
}
BASE = "plain"
BOOKS = ("Ophelia", "Cecil", "Marky", "Union", "Screen A+B")
DECIDES = {p11.CLEAN: ("Ophelia", "Cecil", "Marky", "Union"), p14.SMID: ("Screen A+B",)}


# ---- data ------------------------------------------------------------------
def ohlc_by_ticker(df):
    """{ticker: [(date, open, high, low, close)]}; engine_lab's bars keep no high or low."""
    dates = [x.strftime("%Y-%m-%d") for x in df.index]
    out = {}
    for t in sorted(set(df.columns.get_level_values(1))):
        cols = [df[f][t].values for f in ("Open", "High", "Low", "Close")]
        rows = []
        for d, o, h, lo, c in zip(dates, *cols):
            if o == o and h == h and lo == lo and c == c and o > 0 and c > 0 and lo > 0:
                o, h, lo, c = float(o), float(h), float(lo), float(c)
                rows.append((d, o, max(h, o, c), min(lo, o, c), c))    # adjusted bars can round past the open
        if rows:
            out[t] = rows
    return out


def books_for(uname):
    """{week: {book: [tickers]}} from the passes that recorded them."""
    R = lab.RESULTS
    out = {}

    def put(week, book, names):
        out.setdefault(week, {})[book] = list(dict.fromkeys(names))
    if uname == p11.CLEAN:
        for r in json.loads((R / "pass9b_sp500_asof.json").read_text(encoding="utf-8"))["history"]["weeks"]:
            put(r["week"], "Ophelia", [t for t, _ in r["books"]["Ophelia"]["book"]])
    elif uname == p9.REFERENCE:
        for r in json.loads((R / "pass9_universe.json").read_text(encoding="utf-8"))["history"]["weeks"][p9.REFERENCE]:
            put(r["week"], "Ophelia", [t for t, _ in r["books"]["Ophelia"]["book"]])
    if uname in (p11.CLEAN, p9.REFERENCE):
        for r in json.loads((R / "pass11_cecil_themes.json").read_text(encoding="utf-8"))["cecil"][uname]["history"]["weeks"]:
            put(r["week"], "Cecil", r["fives"]["Cecil, P/E"])
    for r in json.loads((R / "pass14_screen_marky.json").read_text(encoding="utf-8"))["universes"][uname]["history"]["weeks"]:
        put(r["week"], "Marky", r["fives"]["Marky channel"])
        put(r["week"], "Screen A+B", r["fives"]["Screen A+B"])
    for b in out.values():
        if all(k in b for k in ("Ophelia", "Cecil", "Marky")):
            b["Union"] = list(dict.fromkeys(b["Ophelia"] + b["Cecil"] + b["Marky"]))
    return out


def pool_for(uname, names, raw, cal, W):
    tradeable = p10.pool(names, raw, cal, W)
    if uname != p14.SMID:
        return tradeable
    out = []                                         # Pass 14's pool: two years of history, $5M a day
    for t in tradeable:
        bars = raw[t].before(W, 800) if t in raw else []
        if len(bars) >= 260 and statistics.fmean(b["close"] * b["volume"] for b in bars[-p14.LIQ_DAYS:]) >= ds.DOLLAR_VOL_MIN:
            out.append(t)
    return out


# ---- one position ----------------------------------------------------------------
def simulate(rule, rows, i0, iend, spy, spy_end, reports, wsd):
    """(return over the quarter, weeks in the stock, {exit reason: fraction sold})."""
    entry = rows[i0][1]
    rem, value, held = 1.0, 0.0, 0.0
    why = {}
    stop = entry * (1 + rule["stop"]) if rule.get("stop") is not None else None
    if rule.get("vol_stop"):
        stop = entry * (1 - rule["vol_stop"] * wsd) if wsd else None
    targets = [entry * (1 + p) for p, _ in rule.get("ladder", ())]
    fracs = [f for _, f in rule.get("ladder", ())]
    k, lock_next, pending, hi = 0, False, None, None
    closes = []
    band, n = rule.get("stagnation") or (None, None)
    trail = rule.get("trail")
    report = None
    if rule.get("earnings") and reports:
        j = bisect.bisect_right(reports, rows[i0][0])
        report = reports[j] if j < len(reports) else None

    def sell(frac, px, d, at, reason):
        nonlocal rem, value, held
        frac = min(frac, rem)
        if frac <= 1e-12:
            return
        s_in = spy.get((rows[d][0], at))
        value += frac * px / entry * (1 - SIDE) * (spy_end / s_in if s_in else 1.0)
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
        closes.append(c)
        if band and len(closes) > n:
            w = closes[-(n + 1):]
            if max(w) <= w[0] * (1 + band) and min(w) >= w[0] * (1 - band):
                pending = "stagnation"
        if lock_next and rule.get("lock") is not None:
            stop = max(stop or 0.0, entry * (1 + rule["lock"]))
        lock_next = False
    return value * (1 - SIDE) - 1.0, held / 5.0, why


def position(t, W, bars, spy, cal):
    """(rows, i0, iend, spy_end, reports, wsd) for a pick bought on W's Monday, or None."""
    rows = bars.get(t)
    if not rows:
        return None
    dates = [r[0] for r in rows]
    i0 = bisect.bisect_left(dates, W)
    fri = lab._plus(W, 7 * (HORIZON_WEEKS - 1) + 4)
    iend = bisect.bisect_right(dates, fri) - 1
    if i0 >= len(rows) or rows[i0][0] > lab._plus(W, 4) or iend <= i0 or rows[iend][0] < lab._plus(fri, -4):
        return None
    spy_end = spy.get((rows[iend][0], "close"))
    if not spy_end:
        return None
    past = [r[4] for r in rows[max(0, i0 - 61):i0]]
    rets = [b / a - 1.0 for a, b in zip(past, past[1:])]
    wsd = statistics.pstdev(rets) * 5 ** 0.5 if len(rets) >= 20 else None
    return rows, i0, iend, spy_end, sorted(cal.get(t) or []), wsd


# ---- statistics --------------------------------------------------------------------
def nw_t(xs, lags=NW_LAGS):
    n = len(xs)
    if n < 3:
        return None
    m = statistics.fmean(xs)
    d = [x - m for x in xs]
    s = sum(v * v for v in d) / n
    for j in range(1, min(lags, n - 1) + 1):
        s += 2 * (1 - j / (lags + 1)) * sum(d[i] * d[i - j] for i in range(j, n)) / n
    return m / (s / n) ** 0.5 if s > 0 else 0.0


def trade_stats(trades):
    if not trades:
        return None
    r = [x[0] for x in trades]
    wins, losses = [v for v in r if v > 0], [v for v in r if v <= 0]
    reasons = {}
    for _, _, why in trades:
        for k, f in why.items():
            reasons[k] = reasons.get(k, 0.0) + f / len(trades)
    return {"trades": len(r), "mean": statistics.fmean(r), "sd": statistics.pstdev(r),
            "win_rate": len(wins) / len(r), "avg_win": statistics.fmean(wins) if wins else None,
            "avg_loss": statistics.fmean(losses) if losses else None,
            "weeks_in": statistics.fmean(x[1] for x in trades),
            "stopped": sum(1 for _, _, why in trades if why.get("stop", 0) > 0 or why.get("trailing", 0) > 0) / len(r),
            "reasons": dict(sorted(reasons.items()))}


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
                            "value": statistics.fmean(val), "t": nw_t(val),
                            "median": statistics.median(val), "weeks_better": sum(1 for x in val if x > 0),
                            "halves": [statistics.fmean(val[:half]), statistics.fmean(val[half:])],
                            "on_random": statistics.fmean(rnd), "on_random_t": nw_t(rnd),
                            "skill": statistics.fmean(val) - statistics.fmean(rnd),
                            "vs_spy": statistics.fmean(spy), "vs_spy_t": nw_t(spy),
                            "edge_vs_random": statistics.fmean(edge), "edge_t": nw_t(edge),
                            "trades": trade_stats(trades[b][rule]), "random_trades": trade_stats(pool_trades[rule])}
    return out


# ---- a universe ------------------------------------------------------------------------
def run_universe(uname, names, weeks, smoke=False):
    end = lab._plus(lab.council_weeks(p9._last_friday())[-1][1], 5)
    tickers = sorted(set(names)) + lab.EXTRA
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, p4.HIST_START)).items()}
    bars = ohlc_by_ticker(lab.download(tickers, True, end, p4.HIST_START))
    spy = {}
    for d, o, h, lo, c in bars["SPY"]:
        spy[(d, "open")], spy[(d, "close")] = o, c
    cal = lab.earnings_calendar(names)
    books = books_for(uname)
    last_fri = bars["SPY"][-1][0]
    weeks = [w for w in weeks if lab._plus(w[1], 7 * (HORIZON_WEEKS - 1) + 4) <= last_fri and w[0] in books]
    if smoke:
        weeks = weeks[:6]
    cohorts = []
    trades = {b: {r: [] for r in RULES} for b in BOOKS}
    pool_trades = {r: [] for r in RULES}
    for label, W, _ in weeks:
        pool = pool_for(uname, names, raw, cal, W)
        rng = random.Random(f"{lab.SEED}-{W}-p15-{uname}")
        sample = sorted(rng.sample(pool, min(POOL_SAMPLE, len(pool))))
        wanted = set(sample) | {t for b in books[label].values() for t in b}
        sims = {}
        for t in wanted:
            pos = position(t, W, bars, spy, cal)
            if pos:
                sims[t] = {rule: simulate(spec, *pos[:2], pos[2], spy, pos[3], pos[4], pos[5]) for rule, spec in RULES.items()}
        s_rows = bars["SPY"]
        sd = [r[0] for r in s_rows]
        i0 = bisect.bisect_left(sd, W)
        iend = bisect.bisect_right(sd, lab._plus(W, 7 * (HORIZON_WEEKS - 1) + 4)) - 1
        coh = {"week": label, "spy": s_rows[iend][4] / s_rows[i0][1] - 1.0, "books": {}, "pool": {}}
        in_pool = [t for t in sample if t in sims]
        if len(in_pool) < 20:
            continue
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
    return cohorts, summarize(cohorts, trades, pool_trades, min_weeks=3 if smoke else 10)


def show(title, s, decides):
    print(f"\n  {title}")
    for b, rules in s.items():
        tag = " (decides)" if b in decides else ""
        p = rules[BASE]
        pt = p["trades"]
        print(f"  {b}{tag}: {p['weeks']} weeks; the plain quarter {p['ret']*100:+.2f}% (vs SPY {p['vs_spy']*100:+.2f}%, "
              f"t {p['vs_spy_t']:+.2f}), win rate {pt['win_rate']:.0%}")
        print(f"    {'rule':<28}{'vs plain':>9}{'t':>7}{'median':>8}{'better':>8}{'halves':>15}{'random':>9}{'vs SPY':>9}"
              f"{'win':>6}{'avg win':>9}{'avg loss':>9}{'wks in':>7}{'stopped':>8}")
        for rule, x in rules.items():
            if rule == BASE:
                continue
            tr = x["trades"]
            print(f"    {rule:<28}{x['value']*100:+8.2f}%{x['t']:+7.2f}{x['median']*100:+7.2f}%{x['weeks_better']:>4}/{x['weeks']:<3}"
                  f"{x['halves'][0]*100:+7.2f}/{x['halves'][1]*100:+.2f}"
                  f"{x['on_random']*100:+8.2f}%{x['vs_spy']*100:+8.2f}%{tr['win_rate']:6.0%}{(tr['avg_win'] or 0)*100:+8.1f}%"
                  f"{(tr['avg_loss'] or 0)*100:+8.1f}%{tr['weeks_in']:7.1f}{tr['stopped']:8.0%}")


def main(smoke=False):
    U = p9.universes()
    hweeks = lab.history_weeks(lab.HISTORY_FIRST_MONDAY, lab.HISTORY_LAST_MONDAY)
    universes = {p11.CLEAN: p9.sp500_asof(), p9.REFERENCE: U[p9.REFERENCE], p14.SMID: p14.smid_list()}
    if smoke:
        universes = {p9.REFERENCE: U[p9.REFERENCE]}
    result = {"rules": RULES, "horizon_weeks": HORIZON_WEEKS, "side": SIDE, "pool_sample": POOL_SAMPLE, "universes": {}}
    for uname, names in universes.items():
        print(f"  {uname}: {len(names)} names", flush=True)
        cohorts, s = run_universe(uname, names, hweeks, smoke)
        show(f"{uname}: {len(cohorts)} pick weeks, each held up to a quarter", s, DECIDES.get(uname, ()))
        result["universes"][uname] = {"summary": s, "cohorts": cohorts}
    v = {}
    for uname, books in DECIDES.items():
        s = result["universes"].get(uname, {}).get("summary", {})
        for b in books:
            for rule, x in (s.get(b) or {}).items():
                if rule != BASE:
                    v[f"{rule} helps {b} on {uname}"] = bool(x["t"] is not None and x["t"] >= 2 and x["value"] > 0
                                                             and x["median"] > 0 and all(h > 0 for h in x["halves"]))
    result["verdicts"] = v
    hits = [k for k, ok in v.items() if ok]
    print("\n  registered verdicts: " + (", ".join(hits) if hits else "none helps"))
    out = lab.CACHE / "pass15.smoke.json" if smoke else lab.RESULTS / "pass15_exits.json"
    with open(out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(result, fh, indent=1, default=float)
        fh.write("\n")


if __name__ == "__main__":
    main(smoke=sys.argv[1:] == ["smoke"])
