#!/usr/bin/env python3
"""Pass 53 -- other history: Pass 52's ten-slot books on 1996 to 2008, by
named period, and over every five-year window.

Registered in lab/README.md (Pass 53) before any run.

    python lab/pass53_other_history.py fetch    # bars from 1994
    python lab/pass53_other_history.py          # full run
    python lab/pass53_other_history.py smoke    # plumbing: 300 names
"""
from __future__ import annotations

import itertools
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass38_chart_stack as p38  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402
import pass48_screen_book as p48  # noqa: E402
import pass52_ten_good_channels as p52  # noqa: E402

START, END = "1994-01-01", "2026-11-14"
BARS = lab.CACHE / f"weekly_adj_{START}_{END}_all.pkl"
SLOTS = 10
DRAWS = 100
SEED = 20261153
WINDOW, STEP = 260, 26
OUT = lab.RESULTS / "pass53_other_history.json"
NEW = ("1996-07", "2008-07")
PERIODS = {"new: 1996-07 to 2008-06": NEW, "seen: 2008-07 to 2026": ("2008-07", "9"), "everything": ("0", "9"),
           "1996-99": ("1996", "2000"), "2000-02": ("2000", "2003"), "2003-07": ("2003", "2008"), "2008-09": ("2008", "2010"),
           "2010-16": ("2010", "2017"), "2017-19": ("2017", "2020"), "2020-21": ("2020", "2022"), "2022": ("2022", "2023"),
           "2023-26": ("2023", "9")}


def fetch():
    if BARS.exists():
        print("bars already cached")
        return
    import yfinance as yf
    names = [r["ticker"] for r in p43.read_universe(p43.universe_file())] + ["SPY"]
    frames = {}
    for i in range(0, len(names), 100):
        chunk = names[i:i + 100]
        df = None
        for attempt in range(3):
            try:
                df = yf.download([t.replace(".", "-") for t in chunk], start=START, end=END, interval="1wk",
                                 auto_adjust=True, progress=False, group_by="ticker", threads=True)
                break
            except Exception as e:                                  # noqa: BLE001
                print("retry", i, e)
                time.sleep(5 + 5 * attempt)
        if df is None:
            continue
        for t in chunk:
            y = t.replace(".", "-")
            if y in df.columns.get_level_values(0):
                sub = df[y].dropna(how="all")
                if len(sub) > 30:
                    frames[t] = sub[["Open", "High", "Low", "Close", "Volume"]].astype("float32")
        print(f"{min(i + 100, len(names))}/{len(names)} names, {len(frames)} with bars", flush=True)
        time.sleep(1.0)
    lab.CACHE.mkdir(parents=True, exist_ok=True)
    with open(BARS, "wb") as fh:
        pickle.dump(frames, fh)
    print(f"wrote {BARS.name}: {len(frames)} names")


def stat(rets, dates):
    if len(rets) < 26:
        return None
    st = p38.stats(rets, [0.0] * len(rets), dates)
    return {"cagr": st["cagr"], "sharpe": st["sharpe"], "max_drawdown": st["max_drawdown"], "weeks": len(rets)}


def main(argv):
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "fetch":
        return fetch()
    smoke = mode == "smoke"
    uni = {r["ticker"]: r for r in p43.read_universe(p43.universe_file())}
    with open(BARS, "rb") as fh:
        frames = pickle.load(fh)
    names = sorted(t for t in frames if t in uni)
    if smoke:
        names = names[::max(1, len(names) // 300)][:300]
    import pandas as pd
    # Yahoo keys a weekly bar on the request's start day for names that were
    # trading then (1994-01-01, a Saturday) and on Monday for names listed
    # later. Both are the same trading week: move every bar to its Monday.
    for t, f in frames.items():
        if len(f) and f.index[0].weekday() != 0:
            f.index = pd.DatetimeIndex([d + pd.Timedelta(days=(7 - d.weekday()) % 7) for d in f.index])
    idx = pd.DatetimeIndex([d for d in frames["SPY"].index if d.weekday() == 0])

    def mat(col):
        return np.column_stack([frames[t][col].reindex(idx).to_numpy(dtype=float) for t in names])
    Ow, Hw, Lw, Cw, Vw = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    nW, n = Cw.shape
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
    spy_c = frames["SPY"]["Close"].reindex(idx).ffill().to_numpy(dtype=float)
    print(f"{nW} weeks {fridays[0]} .. {fridays[-1]}, {n} names; with bars in the first week of 1996: "
          f"{int((~np.isnan(Cw[next(i for i, d in enumerate(fridays) if d >= '1996')])).sum())}", flush=True)
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
    for w in range(26, nW):
        with np.errstate(invalid="ignore"):
            med_dv[w] = np.nanmedian(dv[max(0, w - 51):w + 1], axis=0)
            hi52[w] = np.nanmax(Cw[max(0, w - 51):w + 1], axis=0)
            if w >= 52:
                win = wr[max(0, w - 104):w]
                cnt = (~np.isnan(win)).sum(axis=0)
                swing[w] = np.where(cnt >= 40, np.nanstd(win, axis=0), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        swings_off = (lC - np.log(hi52)) / swing
    tradeable = (Cw >= p43.PRICE_MIN) & (np.nan_to_num(med_dv) >= p43.DV_MIN) & (np.nan_to_num(swing) >= p48.SWING_MIN)
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
        order = ok[np.argsort(-size[w, ok])]
        member_size[w, order[:int(500 * scale)]] = True
    member = tradeable & member_size
    slip = float(p43.TIERS[1][3])

    print("drawing channels ...", flush=True)
    T = p52.quality_table(Cw, Hw, Lw)
    lower, slope = T["lower"], T["slope"]
    channel = ~np.isnan(lower) & (np.nan_to_num(slope, nan=-1.0) >= p48.FLOOR) & (np.nan_to_num(T["r2"], nan=0.0) >= p48.R2_MIN)
    near_high = np.nan_to_num(swings_off, nan=-99.0) >= -p48.SWINGS_MAX
    screen = member & channel & near_high

    w0 = 110
    weeks = list(range(w0, nW - 1))
    wk_dates = [fridays[w + 1] for w in weeks]
    Q = np.full((nW, n), np.nan)
    cands = {}
    for w in range(w0, nW):
        js = np.flatnonzero(screen[w])
        if len(js):
            with np.errstate(invalid="ignore", divide="ignore"):
                tight = T["height"][w, js] / (slope[w, js] * T["age"][w, js])
            q = (p52.ranks(T["r2"][w, js]) + p52.ranks(-tight) + p52.ranks(T["age"][w, js]) + p52.ranks(T["touches"][w, js])) / 4.0
            Q[w, js] = q
            js = js[np.argsort(-q, kind="stable")]
        cands[w] = js
    spy = [float(spy_c[w + 1] / spy_c[w] - 1.0) for w in weeks]
    cold = np.array([w >= p52.COLD_WEEKS - 1 and spy_c[w] < spy_c[w - p52.COLD_WEEKS + 1:w + 1].mean() for w in range(nW)])
    pool_ok = member[:-1] & ~np.isnan(R_hold)
    pool = [float(R_hold[w][pool_ok[w]].mean()) if pool_ok[w].any() else 0.0 for w in weeks]
    N = max(3, int(SLOTS * scale * 3)) if smoke else SLOTS

    def sim(exit_, market, pick, rng=None):
        held, prev_w, rets, holds = {}, {}, [], []
        for w in weeks:
            keep, gone = [], []
            for j, st in held.items():
                e, a_, b_, hi = st
                if np.isnan(R_hold[w, j]) or np.isnan(lC[w, j]):
                    gone.append(j)
                    continue
                st[3] = hi = max(hi, Cw[w, j])
                sell = (lC[w, j] < a_ + b_ * (w - e)) if exit_ == "line" else (Cw[w, j] / hi - 1.0 <= -p52.OFF_HIGH)
                (gone if sell else keep).append(j)
            r = 0.0
            for j in gone:
                holds.append(w - held.pop(j)[0])
                r += prev_w.get(j, 0.0) * (0.0 if np.isnan(R_out[w, j]) else R_out[w, j])
            free = N - len(keep)
            new = []
            if free > 0 and not (market == "cold" and cold[w]):
                cs = [int(j) for j in cands[w] if j not in held and j not in gone and not np.isnan(R_in[w, j])]
                new = cs[:free] if pick == "top" else [cs[i] for i in rng.permutation(len(cs))[:free]]
            for j in new:
                held[j] = [w, float(lower[w, j]), float(slope[w, j]), float(max(hi52[w, j], Cw[w, j]))]
            wts = {j: 1.0 / N for j in held}
            for j in held:
                r += (R_in[w, j] if j in new else R_hold[w, j]) / N
            r -= (len(new) + len(gone)) * slip / N
            rets.append(float(r))
            prev_w = wts
        return rets, (float(np.median(holds)) if holds else None)

    per_ix = {k: [i for i, d in enumerate(wk_dates) if a <= d < b] for k, (a, b) in PERIODS.items()}
    starts = list(range(0, len(weeks) - WINDOW + 1, STEP))

    def cg(x):
        x = np.asarray(x, dtype=float)
        return float(np.prod(1.0 + x) ** (52.0 / len(x)) - 1.0)

    def dd(x):
        c = np.cumprod(1.0 + np.asarray(x, dtype=float))
        return float((c / np.maximum.accumulate(c) - 1.0).min())

    out = {"generated": fridays[-1], "names": n, "weeks": len(weeks), "first_week": wk_dates[0], "slots": N,
           "five_year_windows": len(starts), "benchmarks": {}, "books": {}}
    for nm, series in (("SPY", spy), ("pool", pool)):
        out["benchmarks"][nm] = {k: stat([series[i] for i in ix], [wk_dates[i] for i in ix]) for k, ix in per_ix.items()}
    draws = 10 if smoke else DRAWS
    for exit_, market in itertools.product(("line", "20% off the high"), ("none", "cold")):
        name = f"{exit_} | market {market}"
        rets, hold = sim(exit_, market, "top")
        rng = np.random.default_rng(SEED)
        rand = np.array([sim(exit_, market, "random", rng=rng)[0] for _ in range(draws)])
        info = {"median_hold_weeks": hold, "periods": {}}
        for k, ix in per_ix.items():
            st = stat([rets[i] for i in ix], [wk_dates[i] for i in ix])
            if st:
                st["percentile_among_random_books"] = float((rand[:, ix].mean(axis=1) < np.mean([rets[i] for i in ix])).mean() * 100.0)
                st["random_median_cagr"] = float(np.median([cg(row[ix]) for row in rand]))
            info["periods"][k] = st
        win = {"beats_spy": 0, "beats_pool": 0, "beats_median_random": 0, "shallower_drawdown_than_spy": 0, "rows": []}
        for s0 in starts:
            sl = slice(s0, s0 + WINDOW)
            b, sp_, pl = cg(rets[sl]), cg(spy[sl]), cg(pool[sl])
            rm = float(np.median([cg(row[sl]) for row in rand]))
            bd, sd = dd(rets[sl]), dd(spy[sl])
            win["beats_spy"] += b > sp_
            win["beats_pool"] += b > pl
            win["beats_median_random"] += b > rm
            win["shallower_drawdown_than_spy"] += bd > sd
            win["rows"].append({"from": wk_dates[s0], "book": b, "spy": sp_, "pool": pl, "random_median": rm, "book_dd": bd, "spy_dd": sd})
        for k in ("beats_spy", "beats_pool", "beats_median_random", "shallower_drawdown_than_spy"):
            win[k] = float(win[k]) / max(1, len(starts))
        info["five_year"] = win
        out["books"][name] = info
        print("done:", name, flush=True)

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    for k in PERIODS:
        s_, p_ = out["benchmarks"]["SPY"][k], out["benchmarks"]["pool"][k]
        if not s_:
            continue
        print(f"== {k}: SPY {P(s_['cagr'])} Sharpe {s_['sharpe']:.2f} DD {P(s_['max_drawdown'])} | pool {P(p_['cagr'])} Sharpe {p_['sharpe']:.2f} DD {P(p_['max_drawdown'])}")
        for nm, r in out["books"].items():
            b = r["periods"][k]
            if b:
                print(f"     {nm:34} {P(b['cagr'])} Sharpe {b['sharpe']:.2f} DD {P(b['max_drawdown'])} pct {b['percentile_among_random_books']:4.0f} random {P(b['random_median_cagr'])}")
    print(f"five-year windows ({len(starts)}), share won:")
    for nm, r in out["books"].items():
        f = r["five_year"]
        print(f"     {nm:34} beats SPY {P(f['beats_spy'], 0)}  pool {P(f['beats_pool'], 0)}  median random {P(f['beats_median_random'], 0)}  shallower DD than SPY {P(f['shallower_drawdown_than_spy'], 0)}  median hold {r['median_hold_weeks']}")
    best = out["books"]["20% off the high | market cold"]["five_year"]["rows"]
    print("20%/cold by window start, book/SPY/pool: " + "  ".join(f"{r['from'][:7]} {100 * r['book']:+.0f}/{100 * r['spy']:+.0f}/{100 * r['pool']:+.0f}" for r in best[::2]))
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main(sys.argv)
