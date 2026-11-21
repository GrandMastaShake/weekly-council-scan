#!/usr/bin/env python3
"""Pass 46 -- the Heikin-Ashi channel: starting candle, first decent pullback,
and two ways to treat a break.

Weekly Heikin-Ashi candles. The line runs from the starting candle's low
through the low of the first run of two or more red candles that begins four
or more weeks later. Two entries (at the bounce, or early at six weeks) and
two exits (sell on the first close under the line and restart; or flatten the
line through later pullbacks and sell only a cushion under it).

Registered in lab/README.md (Pass 46) before any run.

    python lab/pass46_ha_channel.py          # every arm, both sets
    python lab/pass46_ha_channel.py smoke    # plumbing: 300 names
"""
from __future__ import annotations

import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass38_chart_stack as p38  # noqa: E402
import pass42_who_breaks_first as p42  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402

LOOKBACK = 104
GAP = 4                 # weeks of trend before a red run can set the angle
RUN = 2                 # red candles in a decent pullback
EARLY_AGE, EARLY_GREEN = 6, 4
SWING_MIN = 0.015
FLOOR = math.log(1.10) / 52.0
DRAWS = 200
SEED = 20261126
HALF = p38.HALF
OUT = lab.RESULTS / "pass46_ha_channel.json"

#        name                 early  dynamic cushion (weekly swings)
ARMS = [("restart, bounce",   False, False,  0.0),
        ("restart, early",    True,  False,  0.0),
        ("dynamic 1, bounce", False, True,   1.0),
        ("dynamic 1, early",  True,  True,   1.0),
        ("dynamic 2, bounce", False, True,   2.0),
        ("dynamic 2, early",  True,  True,   2.0)]


def heikin_ashi(o, h, l, c):
    """Heikin-Ashi open, low, close from the first valid bar on; NaN before."""
    n = len(c)
    ho, hl, hc = (np.full(n, np.nan) for _ in range(3))
    ok = ~(np.isnan(o) | np.isnan(h) | np.isnan(l) | np.isnan(c))
    prev_o = prev_c = None
    for i in range(n):
        if not ok[i]:
            prev_o = prev_c = None
            continue
        hc[i] = (o[i] + h[i] + l[i] + c[i]) / 4.0
        ho[i] = (o[i] + c[i]) / 2.0 if prev_o is None else (prev_o + prev_c) / 2.0
        hl[i] = min(l[i], ho[i], hc[i])
        prev_o, prev_c = ho[i], hc[i]
    return ho, hl, hc


def signals(ho, hl, hc, swing, early, dynamic, cushion):
    """One name's trades as (decision week in, decision week out or None, how it ended)."""
    n = len(hc)
    lhl, lhc = np.log(hl), np.log(hc)
    red = hc < ho
    trades = []
    first = next((i for i in range(n) if hc[i] == hc[i]), None)
    if first is None:
        return trades
    brk = first                       # no starting candle may predate this week
    s = None                          # the starting candle
    line = None                       # (log low at s, slope) once a pullback is established
    run_start = None                  # an open red run that could set or flatten the line
    held_since = None
    w = first
    while w < n:
        if hc[w] != hc[w]:            # a gap in the bars: forget everything
            if held_since is not None:
                trades.append((held_since, w - 1, "gap"))
            brk, s, line, run_start, held_since = w + 1, None, None, None, None
            w += 1
            continue
        if line is None:
            lo = max(brk, w - LOOKBACK + 1)
            cand = lo + int(np.argmin(hl[lo:w + 1]))
            if cand != s:
                if held_since is not None:                # an early position whose starting low was undercut
                    trades.append((held_since, w, "under the start"))
                    held_since, brk = None, w
                    lo = w
                    cand = w
                s, run_start = cand, None
            age = w - s
            if held_since is not None and lhc[w] < lhl[s]:
                trades.append((held_since, w, "under the start"))
                held_since, brk, s, run_start = None, w, w, None
                w += 1
                continue
            # the first decent pullback
            if red[w]:
                if run_start is None and age >= GAP:
                    run_start = w
            elif run_start is not None:
                if w - run_start >= RUN:
                    p = run_start + int(np.argmin(hl[run_start:w]))
                    b = (lhl[p] - lhl[s]) / (p - s)
                    if b >= FLOOR and lhc[w] >= lhl[s] + b * (w - s):
                        line = (lhl[s], b)
                        if held_since is None:
                            held_since = w                 # bought at the bounce
                run_start = None
            if (early and held_since is None and line is None and age >= EARLY_AGE and not red[w]
                    and int((~red[s + 1:w + 1]).sum()) >= EARLY_GREEN and age == EARLY_AGE):
                held_since = w
            w += 1
            continue
        # a line exists
        a, b = line
        level = a + b * (w - s)
        if not dynamic:
            if lhc[w] < level:
                if held_since is not None:
                    trades.append((held_since, w, "break"))
                held_since, brk, s, line, run_start = None, w, None, None, None
        else:
            cush = cushion * (swing[w] if swing[w] == swing[w] else 0.03)
            if lhc[w] < level - cush:
                if held_since is not None:
                    trades.append((held_since, w, "break"))
                held_since, brk, s, line, run_start = None, w, None, None, None
            elif red[w]:
                if run_start is None:
                    run_start = w
            elif run_start is not None:
                p = run_start + int(np.argmin(hl[run_start:w]))
                if lhl[p] < a + b * (p - s):
                    nb = (lhl[p] - a) / (p - s)
                    if nb < FLOOR:
                        if held_since is not None:
                            trades.append((held_since, w, "flattened out"))
                        held_since, brk, s, line = None, w, None, None
                    else:
                        line = (a, nb)
                run_start = None
        w += 1
    if held_since is not None:
        trades.append((held_since, None, "open"))
    return trades


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    uf = p43.universe_file()
    uni = {r["ticker"]: r for r in p43.read_universe(uf)}
    with open(p43.BARS, "rb") as fh:
        frames = pickle.load(fh)
    names = sorted(t for t in frames if t in uni)
    if smoke:
        names = names[::max(1, len(names) // 300)][:300]
    import pandas as pd
    idx = sorted(set().union(*[set(frames[t].index) for t in names[:200]]))
    idx = pd.DatetimeIndex([d for d in idx if d.weekday() == 0])

    def mat(col):
        return np.column_stack([frames[t][col].reindex(idx).to_numpy(dtype=float) for t in names])
    Ow, Hw, Lw, Cw, Vw = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    nW, n = Cw.shape
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names", flush=True)

    with np.errstate(invalid="ignore", divide="ignore"):
        lC = np.log(Cw)
        R_hold = Cw[1:] / Cw[:-1] - 1.0
        R_in = Cw[1:] / Ow[1:] - 1.0
        R_out = Ow[1:] / Cw[:-1] - 1.0
        dv = Cw * Vw
        wr = np.diff(lC, axis=0)
    med_dv = np.full((nW, n), np.nan)
    swing = np.full((nW, n), np.nan)
    for w in range(26, nW):
        with np.errstate(invalid="ignore"):
            med_dv[w] = np.nanmedian(dv[max(0, w - 51):w + 1], axis=0)
            if w >= 52:
                win = wr[max(0, w - 104):w]
                cnt = (~np.isnan(win)).sum(axis=0)
                swing[w] = np.where(cnt >= 40, np.nanstd(win, axis=0), np.nan)
    tradeable = (Cw >= p43.PRICE_MIN) & (np.nan_to_num(med_dv) >= p43.DV_MIN) & (np.nan_to_num(swing) >= SWING_MIN)

    cap_now = np.array([float(uni[t]["cap_m"]) for t in names])
    ref_px = np.full(n, np.nan)
    for j, t in enumerate(names):
        good = np.flatnonzero(~np.isnan(Cw[:, j]))
        if len(good):
            upto = [w for w in good if fridays[w] <= uni[t]["cap_date"]]
            ref_px[j] = Cw[upto[-1] if upto else good[0], j]
    with np.errstate(invalid="ignore", divide="ignore"):
        size = cap_now[None, :] * Cw / ref_px[None, :]
    tier = np.full((nW, n), -1, dtype=int)
    scale = n / 3000.0 if smoke else 1.0
    for w in range(nW):
        ok = np.flatnonzero(~np.isnan(size[w]))
        order = ok[np.argsort(-size[w, ok])]
        for k, (_, lo, hi, _) in enumerate(p43.TIERS):
            tier[w, order[int(lo * scale):int(min(hi * scale, len(order)))]] = k
    slip_of = np.array([t[3] for t in p43.TIERS] + [p43.TIERS[-1][3]])
    sets = {"top 500": tradeable & (tier >= 0) & (tier <= 1), "every tradeable name": tradeable}

    ha = [heikin_ashi(Ow[:, j], Hw[:, j], Lw[:, j], Cw[:, j]) for j in range(n)]
    w0 = 66
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]

    def fwd(k):
        f = np.full((nW, n), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            f[:nW - k - 1] = Cw[k + 1:] / Ow[1:nW - k] - 1.0
        return f
    F13, F26 = fwd(13), fwd(26)

    # SPY over the same weeks, from the lab's daily cache
    import pass32_stop_random as p32
    sdf = lab.download(sorted(p32.members()) + ["SPY"], True, p32.DATA_END, start=p32.DATA_START)["Close"]["SPY"].dropna()
    spy_w = sdf.groupby([sdf.index.isocalendar().year, sdf.index.isocalendar().week]).last()
    spy_keys = [(int(y), int(k)) for y, k in spy_w.index]
    spy_ret = dict(zip(spy_keys[1:], spy_w.pct_change().to_numpy()[1:]))
    from datetime import date as _date
    spy = [float(spy_ret.get(tuple(_date.fromisoformat(d).isocalendar()[:2]), 0.0)) for d in wk_dates]
    assert sum(1 for d in wk_dates if tuple(_date.fromisoformat(d).isocalendar()[:2]) not in spy_ret) <= 2

    spans = {"all": ("0", "9"), "to 2016": ("0", HALF), "2017 on": (HALF, "9")}
    draws = 20 if smoke else DRAWS
    out = {"generated": fridays[-1], "names": n, "weeks": len(weeks), "first_week": wk_dates[0], "last_week": wk_dates[-1],
           "spy": {sp: None for sp in spans}, "sets": {}}
    for sp, (a, b) in spans.items():
        ix = [i for i, d in enumerate(wk_dates) if a <= d < b]
        st = p38.stats([spy[i] for i in ix], [spy[i] for i in ix], [wk_dates[i] for i in ix])
        out["spy"][sp] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"]}

    all_trades = {}
    for name, early, dynamic, cushion in ARMS:
        tr = []
        for j in range(n):
            ho, hl, hc = ha[j]
            for e, x, why in signals(ho, hl, hc, swing[:, j], early, dynamic, cushion):
                tr.append((e, x, j, why))
        all_trades[name] = tr
        print(f"  signals {name}: {len(tr)}", flush=True)

    for sname, member in sets.items():
        pool_ok = member[:-1] & ~np.isnan(R_hold)
        pool_mean = np.array([float(R_hold[w][pool_ok[w]].mean()) if pool_ok[w].any() else 0.0 for w in range(nW - 1)])
        P13 = np.array([np.nanmean(np.where(member[w], F13[w], np.nan)) if member[w].any() else np.nan for w in range(nW)])
        P26 = np.array([np.nanmean(np.where(member[w], F26[w], np.nan)) if member[w].any() else np.nan for w in range(nW)])
        res_set = {"median_names_a_week": float(np.median(member[w0:].sum(axis=1))), "arms": {}}
        for name, early, dynamic, cushion in ARMS:
            rng = np.random.default_rng(SEED)
            enter_at, exit_at = {}, {}
            taken = []
            for e, x, j, why in all_trades[name]:
                if e < w0 or e >= nW - 1 or not member[e, j] or np.isnan(R_in[e, j]):
                    continue
                enter_at.setdefault(e, []).append(j)
                if x is not None and x < nW - 1:
                    exit_at.setdefault(x, []).append(j)
                taken.append((e, x, j, why))
            held = set()
            rets, counts = [], []
            rand = np.zeros((draws, len(weeks)))
            for i, w in enumerate(weeks):
                gone = [j for j in exit_at.get(w, []) if j in held]
                for j in gone:
                    held.discard(j)
                keep = [j for j in held if not np.isnan(R_hold[w, j])]
                new = [j for j in enter_at.get(w, []) if j not in held]
                r = sum(R_hold[w, j] for j in keep)
                r += sum((0.0 if np.isnan(R_out[w, j]) else R_out[w, j]) - slip_of[tier[w, j]] for j in gone)
                r += sum(R_in[w, j] - slip_of[tier[w, j]] for j in new)
                k = len(keep) + len(gone) + len(new)
                rets.append(float(r) / k if k else 0.0)
                held = set(keep) | set(new)
                kk = len(held)
                counts.append(kk)
                pool = np.flatnonzero(pool_ok[w])
                if kk and len(pool) >= kk:
                    if kk * 3 > len(pool):
                        rand[:, i] = [R_hold[w][rng.choice(pool, kk, replace=False)].mean() for _ in range(draws)]
                    else:
                        pick = rng.random((draws, len(pool))).argpartition(kk - 1, axis=1)[:, :kk]
                        rand[:, i] = R_hold[w][pool][pick].mean(axis=1)
            holds, gains, ends = [], [], {}
            for e, x, j, why in taken:
                ends[why] = ends.get(why, 0) + 1
                if x is None or x >= nW - 1:
                    continue
                px_in, px_out = Ow[e + 1, j], Ow[x + 1, j]
                if px_in == px_in and px_out == px_out:
                    holds.append(x - e)
                    gains.append(float(px_out / px_in - 1.0))
            res = {"avg_names_held": float(np.mean(counts)), "weeks_in_cash": int(sum(1 for c in counts if c == 0)),
                   "entries": len(taken), "entries_a_year": len(taken) / (len(weeks) / 52.0),
                   "median_hold_weeks": float(np.median(holds)) if holds else None,
                   "share_closed_at_a_gain": float(np.mean([g > 0 for g in gains])) if gains else None,
                   "mean_closed_gain": float(np.mean(gains)) if gains else None,
                   "median_closed_gain": float(np.median(gains)) if gains else None, "how_holds_ended": ends,
                   "book": {}, "cards": {}}
            for sp, (a, b) in spans.items():
                ix = [i for i, d in enumerate(wk_dates) if a <= d < b]
                rr = [rets[i] for i in ix]
                st = p38.stats(rr, [spy[i] for i in ix], [wk_dates[i] for i in ix])
                pl = p38.stats([pool_mean[weeks[i]] for i in ix], [spy[i] for i in ix], [wk_dates[i] for i in ix])
                means = rand[:, ix].mean(axis=1)
                res["book"][sp] = {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"],
                                   "pool_cagr": pl["cagr"], "pool_sharpe": pl["sharpe"],
                                   "percentile_among_random": float((means < np.mean(rr)).mean() * 100.0)}
                cs = [(e, F13[e, j] - P13[e], F26[e, j] - P26[e]) for e, x, j, why in taken if a <= fridays[e] < b]
                by_week = {}
                for c in cs:
                    by_week.setdefault(c[0], []).append(c[1])
                s13 = [np.nanmean(v) for _, v in sorted(by_week.items())]
                s13 = [v for v in s13 if v == v]
                m13, se13 = p42.nw_se(s13) if len(s13) > 20 else (None, None)
                x13 = [c[1] for c in cs if c[1] == c[1]]
                x26 = [c[2] for c in cs if c[2] == c[2]]
                res["cards"][sp] = {"cards": len(cs), "excess_13w": float(np.mean(x13)) if x13 else None,
                                    "excess_26w": float(np.mean(x26)) if x26 else None,
                                    "share_beating_pool_13w": float(np.mean([v > 0 for v in x13])) if x13 else None,
                                    "t": (m13 / se13) if se13 else None}
            res_set["arms"][name] = res
        out["sets"][sname] = res_set

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print("SPY: " + "; ".join(f"{sp} {P(v['cagr']).strip()} Sharpe {v['sharpe']:.2f} DD {P(v['max_drawdown']).strip()}" for sp, v in out["spy"].items()))
    for sname, rs in out["sets"].items():
        print(f"=== {sname} (median {rs['median_names_a_week']:.0f} names a week)")
        print(f"{'arm':19} {'CAGR':>7} {'pool':>7} {'Sharpe':>6} {'maxDD':>7} {'pct':>4} {'h1':>4} {'h2':>4} | {'held':>5} {'in/yr':>6} {'hold':>5} {'won':>5} {'mean':>7} {'median':>7} | {'13w':>7} {'t':>5} {'h1':>7} {'h2':>7}")
        for nm, r in rs["arms"].items():
            b, c = r["book"], r["cards"]
            t = c["all"]["t"]
            print(f"{nm:19} {P(b['all']['cagr'])} {P(b['all']['pool_cagr'])} {b['all']['sharpe']:6.2f} {P(b['all']['max_drawdown'])} "
                  f"{b['all']['percentile_among_random']:4.0f} {b['to 2016']['percentile_among_random']:4.0f} {b['2017 on']['percentile_among_random']:4.0f} | "
                  f"{r['avg_names_held']:5.0f} {r['entries_a_year']:6.0f} {r['median_hold_weeks'] or 0:5.0f} {P(r['share_closed_at_a_gain'], 0)[1:]} "
                  f"{P(r['mean_closed_gain'])} {P(r['median_closed_gain'])} | {P(c['all']['excess_13w'], 2)} {'   --' if t is None else f'{t:5.1f}'} "
                  f"{P(c['to 2016']['excess_13w'], 2)} {P(c['2017 on']['excess_13w'], 2)}")
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
