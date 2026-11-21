#!/usr/bin/env python3
"""Pass 57 -- the way back in, tested in the ten-slot book over thirty years.

Pass 53's book with a channel counting after 8 weeks and no price floor,
plus the two halves read off Pass 56: do not sell when the fall was the
market's, and buy a sold name back on a close above its 10-week average
unless its MACD line was deeply negative when it was sold.

Registered in lab/README.md (Pass 57) before any run.

    python lab/pass57_way_back_book.py          # full run
    python lab/pass57_way_back_book.py smoke    # plumbing: 300 names
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass38_chart_stack as p38  # noqa: E402
import pass41_owner_channel as p41  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402
import pass48_screen_book as p48  # noqa: E402
import pass52_ten_good_channels as p52  # noqa: E402
import pass53_other_history as p53  # noqa: E402
import pass56_back_in as p56  # noqa: E402

p41.MIN_AGE = 8                       # a channel counts after 8 weeks (Pass 54)
SLOTS = 10
OFF_HIGH = 0.20
MARKET_FALL = -0.135                  # the stock's fall less SPY's: above this, the fall is the market's
MACD_DEEP = -0.02                     # MACD line as a share of price at the sale: below this, no way back
BACK_WEEKS = 52
DRAWS = 100
SEED = 20261157
WINDOW, STEP = 260, 26
OUT = lab.RESULTS / "pass57_way_back_book.json"
PERIODS = {"unseen: 1996-07 to 2006-10": ("1996-07", "2006-11-10"), "2006-11 to 2016-11": ("2006-11-10", "2016-11-11"),
           "2016-11 to 2026-11": ("2016-11-11", "9"), "everything": ("0", "9")}
#        name                       half one, half two, MACD proviso
BOOKS = [("base", False, False, True), ("half one: market falls not sold", True, False, True),
         ("half two: back above the 10-week average", False, True, True), ("both", True, True, True),
         ("half two without the MACD proviso", False, True, False)]


def main(argv):
    smoke = len(argv) > 1 and argv[1] == "smoke"
    import pandas as pd
    uni = {r["ticker"]: r for r in p43.read_universe(p43.universe_file())}
    with open(p53.BARS, "rb") as fh:
        frames = pickle.load(fh)
    for t, f in frames.items():
        if len(f) and f.index[0].weekday() != 0:
            f.index = pd.DatetimeIndex([d + pd.Timedelta(days=(7 - d.weekday()) % 7) for d in f.index])
    names = sorted(t for t in frames if t in uni)
    if smoke:
        names = names[::max(1, len(names) // 300)][:300]
    idx = pd.DatetimeIndex([d for d in frames["SPY"].index if d.weekday() == 0])

    def mat(col):
        return np.column_stack([frames[t][col].reindex(idx).to_numpy(dtype=float) for t in names])
    Ow, Hw, Lw, Cw, Vw = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    nW, n = Cw.shape
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
    spy_c = frames["SPY"]["Close"].reindex(idx).ffill().to_numpy(dtype=float)
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
    hi52 = np.full((nW, n), np.nan)
    hi52_w = np.zeros((nW, n), dtype=int)
    ma10 = np.full((nW, n), np.nan)
    for w in range(26, nW):
        with np.errstate(invalid="ignore"):
            win = Cw[max(0, w - 51):w + 1]
            med_dv[w] = np.nanmedian(dv[max(0, w - 51):w + 1], axis=0)
            hi52[w] = np.nanmax(win, axis=0)
            hi52_w[w] = max(0, w - 51) + np.argmax(np.where(np.isnan(win), -np.inf, win), axis=0)
            ma10[w] = np.nanmean(Cw[w - 9:w + 1], axis=0)
            if w >= 52:
                wn = wr[max(0, w - 104):w]
                cnt = (~np.isnan(wn)).sum(axis=0)
                swing[w] = np.where(cnt >= 40, np.nanstd(wn, axis=0), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        swings_off = (lC - np.log(hi52)) / swing
    tradeable = (np.nan_to_num(med_dv) >= p43.DV_MIN) & (np.nan_to_num(swing) >= p48.SWING_MIN)
    macd = p56.ema(Cw, 12) - p56.ema(Cw, 26)
    with np.errstate(invalid="ignore", divide="ignore"):
        macd_share = macd / Cw
    cap_now = np.array([float(uni[t]["cap_m"]) for t in names])
    ref_px = np.full(n, np.nan)
    for j, t in enumerate(names):
        good = np.flatnonzero(~np.isnan(Cw[:, j]))
        if len(good):
            upto = [w for w in good if fridays[w] <= uni[t]["cap_date"]]
            ref_px[j] = Cw[upto[-1] if upto else good[0], j]
    with np.errstate(invalid="ignore", divide="ignore"):
        size = cap_now[None, :] * Cw / ref_px[None, :]
    scale = n / 3000.0 if smoke else 1.0
    member_size = np.zeros((nW, n), dtype=bool)
    for w in range(nW):
        ok = np.flatnonzero(~np.isnan(size[w]))
        member_size[w, ok[np.argsort(-size[w, ok])][:int(500 * scale)]] = True
    member = tradeable & member_size
    slip = float(p43.TIERS[1][3])

    print("drawing channels ...", flush=True)
    T = p52.quality_table(Cw, Hw, Lw)
    slope = T["slope"]
    channel = ~np.isnan(T["lower"]) & (np.nan_to_num(slope, nan=-1.0) >= p48.FLOOR) & (np.nan_to_num(T["r2"], nan=0.0) >= p48.R2_MIN)
    screen = member & channel & (np.nan_to_num(swings_off, nan=-99.0) >= -p48.SWINGS_MAX)
    w0 = 110
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    cands = {}
    for w in range(w0, nW):
        js = np.flatnonzero(screen[w])
        if len(js) > 1:
            with np.errstate(invalid="ignore", divide="ignore"):
                tight = T["height"][w, js] / (slope[w, js] * T["age"][w, js])
            q = (p52.ranks(T["r2"][w, js]) + p52.ranks(-tight) + p52.ranks(T["age"][w, js]) + p52.ranks(T["touches"][w, js])) / 4.0
            js = js[np.argsort(-q, kind="stable")]
        cands[w] = js
    spy = [float(spy_c[w + 1] / spy_c[w] - 1.0) for w in weeks]
    cold = np.array([w >= p52.COLD_WEEKS - 1 and spy_c[w] < spy_c[w - p52.COLD_WEEKS + 1:w + 1].mean() for w in range(nW)])
    pool_ok = member[:-1] & ~np.isnan(R_hold)
    pool = [float(R_hold[w][pool_ok[w]].mean()) if pool_ok[w].any() else 0.0 for w in weeks]
    N = max(3, int(SLOTS * scale * 3)) if smoke else SLOTS

    def sim(half1, half2, proviso, pick, rng=None, detail=False):
        held, sold, rets = {}, {}, []          # held: j -> [entry week, high, week of high]; sold: j -> (week, MACD share)
        holds, kept, backs, buys, inv = [], 0, 0, 0, []
        for w in weeks:
            gone = []
            for j, st in held.items():
                c = Cw[w, j]
                if c != c or np.isnan(R_hold[w, j]):
                    gone.append(j)
                    continue
                if c >= st[1]:
                    st[1], st[2] = c, w
                off = c / st[1] - 1.0
                if off <= -OFF_HIGH:
                    if half1 and off - (spy_c[w] / spy_c[st[2]] - 1.0) > MARKET_FALL:
                        kept += 1
                    else:
                        gone.append(j)
            r = 0.0
            for j in gone:
                st = held.pop(j)
                holds.append(w - st[0])
                sold[j] = (w, macd_share[w, j])
                r += (0.0 if np.isnan(R_out[w, j]) else R_out[w, j]) / N
            new, back = [], []
            free = N - len(held)
            if free > 0 and not cold[w]:
                if half2:
                    for j, (sw, ms) in sorted(sold.items(), key=lambda kv: -kv[1][0]):
                        if len(back) >= free:
                            break
                        if (j not in gone and w - sw <= BACK_WEEKS and member[w, j] and Cw[w, j] > ma10[w, j]
                                and not np.isnan(R_in[w, j]) and (not proviso or (ms == ms and ms >= MACD_DEEP))):
                            back.append(j)
                free -= len(back)
                if free > 0:
                    cs = [int(j) for j in cands[w] if j not in held and j not in gone and j not in back and not np.isnan(R_in[w, j])]
                    new = cs[:free] if pick == "top" else [cs[i] for i in rng.permutation(len(cs))[:free]]
            for j in held:
                r += R_hold[w, j] / N
            for j in back:
                held[j] = [w, float(Cw[w, j]), w]
                sold.pop(j, None)
                r += R_in[w, j] / N
            for j in new:
                held[j] = [w, float(max(hi52[w, j], Cw[w, j])), int(hi52_w[w, j])]
                sold.pop(j, None)
                r += R_in[w, j] / N
            backs += len(back)
            buys += len(new) + len(back)
            r -= (len(new) + len(back) + len(gone)) * slip / N
            rets.append(float(r))
            inv.append(len(held) / N)
            if w % 52 == 0:
                sold = {j: v for j, v in sold.items() if w - v[0] <= BACK_WEEKS}
        if not detail:
            return rets
        yrs = len(weeks) / 52.0
        return rets, {"buys_a_year": buys / yrs, "buy_backs_a_year": backs / yrs, "sales_not_made_a_year": kept / yrs,
                      "median_hold_weeks": float(np.median(holds)) if holds else None, "avg_invested": float(np.mean(inv))}

    def cg(x):
        x = np.asarray(x, dtype=float)
        return float(np.prod(1.0 + x) ** (52.0 / len(x)) - 1.0)

    def dd(x):
        c = np.cumprod(1.0 + np.asarray(x, dtype=float))
        return float((c / np.maximum.accumulate(c) - 1.0).min())

    per_ix = {k: [i for i, d in enumerate(wk_dates) if a <= d < b] for k, (a, b) in PERIODS.items()}
    starts = list(range(0, len(weeks) - WINDOW + 1, STEP))
    eras = {"starts 1996 to 2007": ("0", "2008"), "starts 2008 to 2015": ("2008", "2016"), "starts 2016 on": ("2016", "9")}
    out = {"generated": fridays[-1], "names": n, "weeks": len(weeks), "first_week": wk_dates[0], "slots": N,
           "benchmarks": {nm: {k: p53.stat([s_[i] for i in ix], [wk_dates[i] for i in ix]) for k, ix in per_ix.items()} for nm, s_ in (("SPY", spy), ("pool", pool))},
           "books": {}}
    draws = 8 if smoke else DRAWS
    for name, h1, h2, prov in BOOKS:
        rets, info = sim(h1, h2, prov, "top", detail=True)
        rng = np.random.default_rng(SEED)
        rand = np.array([sim(h1, h2, prov, "random", rng=rng) for _ in range(draws)])
        info["periods"] = {}
        for k, ix in per_ix.items():
            st = p53.stat([rets[i] for i in ix], [wk_dates[i] for i in ix])
            if st:
                st["percentile_among_random_books"] = float((rand[:, ix].mean(axis=1) < np.mean([rets[i] for i in ix])).mean() * 100.0)
                st["random_median_cagr"] = float(np.median([cg(row[ix]) for row in rand]))
            info["periods"][k] = st
        info["five_year"] = {}
        for era, (a, b) in eras.items():
            ss = [s0 for s0 in starts if a <= wk_dates[s0] < b]
            info["five_year"][era] = {"windows": len(ss),
                                      "beats_spy": int(sum(cg(rets[s0:s0 + WINDOW]) > cg(spy[s0:s0 + WINDOW]) for s0 in ss)),
                                      "beats_pool": int(sum(cg(rets[s0:s0 + WINDOW]) > cg(pool[s0:s0 + WINDOW]) for s0 in ss)),
                                      "shallower_drawdown_than_spy": int(sum(dd(rets[s0:s0 + WINDOW]) > dd(spy[s0:s0 + WINDOW]) for s0 in ss)),
                                      "median_gap_to_spy": float(np.median([cg(rets[s0:s0 + WINDOW]) - cg(spy[s0:s0 + WINDOW]) for s0 in ss])) if ss else None}
        by_year = {}
        for d_, a_, c_ in zip(wk_dates, rets, spy):
            y = by_year.setdefault(d_[:4], [1.0, 1.0])
            y[0] *= 1 + a_
            y[1] *= 1 + c_
        info["by_year"] = {y: {"arm": v[0] - 1, "spy": v[1] - 1} for y, v in by_year.items()}
        out["books"][name] = info
        print("done:", name, flush=True)

    def P(x, d_=1):
        return "    --" if x is None else f"{100 * x:6.{d_}f}%"
    for k in PERIODS:
        s_, p_ = out["benchmarks"]["SPY"][k], out["benchmarks"]["pool"][k]
        print(f"== {k}: SPY {P(s_['cagr'])} Sharpe {s_['sharpe']:.2f} DD {P(s_['max_drawdown'])} | pool {P(p_['cagr'])} Sharpe {p_['sharpe']:.2f} DD {P(p_['max_drawdown'])}")
        for nm, r in out["books"].items():
            b = r["periods"][k]
            print(f"     {nm:42} {P(b['cagr'])} Sharpe {b['sharpe']:.2f} DD {P(b['max_drawdown'])} pct {b['percentile_among_random_books']:4.0f} random {P(b['random_median_cagr'])}")
    for nm, r in out["books"].items():
        print(f"{nm:42} buys/yr {r['buys_a_year']:.1f} (back {r['buy_backs_a_year']:.1f}), sales not made/yr {r['sales_not_made_a_year']:.1f}, median hold {r['median_hold_weeks']}w, invested {P(r['avg_invested'], 0).strip()} | "
              + "; ".join(f"{era}: SPY {v['beats_spy']}/{v['windows']}, pool {v['beats_pool']}/{v['windows']}, DD {v['shallower_drawdown_than_spy']}/{v['windows']}, gap {P(v['median_gap_to_spy']).strip()}" for era, v in r["five_year"].items()))
    for nm in ("base", "both"):
        print(f"{nm} by year arm/spy: " + "  ".join(f"{y} {100 * v['arm']:+.0f}/{100 * v['spy']:+.0f}" for y, v in out["books"][nm]["by_year"].items()))
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main(sys.argv)
