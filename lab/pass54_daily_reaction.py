#!/usr/bin/env python3
"""Pass 54 -- quicker reactions: Pass 53's ten-slot book on daily bars over
the last ten years, acting weekly, daily, or daily only in a warm market,
with a channel counting after 26 weeks or after 8.

Registered in lab/README.md (Pass 54) before any run.

    python lab/pass54_daily_reaction.py fetch    # daily bars from 2014
    python lab/pass54_daily_reaction.py          # full run
    python lab/pass54_daily_reaction.py smoke    # plumbing: 150 names
"""
from __future__ import annotations

import itertools
import json
import math
import pickle
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass43_channel_by_size as p43  # noqa: E402
import pass48_screen_book as p48  # noqa: E402
import pass52_ten_good_channels as p52  # noqa: E402
import pass53_other_history as p53  # noqa: E402

START, END = "2014-06-01", "2026-11-14"
DAILY = lab.CACHE / f"daily_adj_{START}_{END}_top500ever.pkl"
BOOK_START = "2016-11-14"
HALF = "2021-11-14"
LOOKBACK = 520
AGE_MAX = 500
AGES = {"26 weeks": 130, "8 weeks": 40}
TOUCH_GAP = 20
COLD_DAYS = 200
SLOTS = 10
TOP = 500
DRAWS = 100
SEED = 20261154
FLOOR = math.log(1.10) / 252.0
DV_MIN_DAY = p43.DV_MIN / 5.0
OUT = lab.RESULTS / "pass54_daily_reaction.json"
PERIODS = {"ten years": (BOOK_START, "9"), "first half": (BOOK_START, HALF), "second half": (HALF, "9"),
           "2017-19": ("2017", "2020"), "2020-21": ("2020", "2022"), "2022": ("2022", "2023"), "2023-26": ("2023", "9")}


def weekly_members():
    """Top 500 by size each week, from the weekly bars of the whole list
    (Pass 53's cache). Returns Mondays, names, and a weeks x names table."""
    import pandas as pd
    uni = {r["ticker"]: r for r in p43.read_universe(p43.universe_file())}
    with open(p53.BARS, "rb") as fh:
        frames = pickle.load(fh)
    for t, f in frames.items():
        if len(f) and f.index[0].weekday() != 0:
            f.index = pd.DatetimeIndex([d + pd.Timedelta(days=(7 - d.weekday()) % 7) for d in f.index])
    names = sorted(t for t in frames if t in uni)
    idx = pd.DatetimeIndex([d for d in frames["SPY"].index if d.weekday() == 0 and d >= pd.Timestamp("2014-01-01")])
    Cw = np.column_stack([frames[t]["Close"].reindex(idx).to_numpy(dtype=float) for t in names])
    fridays = [(d + pd.Timedelta(days=4)).date().isoformat() for d in idx]
    cap_now = np.array([float(uni[t]["cap_m"]) for t in names])
    ref_px = np.full(len(names), np.nan)
    for j, t in enumerate(names):
        good = np.flatnonzero(~np.isnan(Cw[:, j]))
        if len(good):
            upto = [w for w in good if fridays[w] <= uni[t]["cap_date"]]
            ref_px[j] = Cw[upto[-1] if upto else good[0], j]
    with np.errstate(invalid="ignore", divide="ignore"):
        size = cap_now[None, :] * Cw / ref_px[None, :]
    member = np.zeros(Cw.shape, dtype=bool)
    for w in range(len(idx)):
        ok = np.flatnonzero(~np.isnan(size[w]))
        member[w, ok[np.argsort(-size[w, ok])][:TOP]] = True
    return idx, names, member


def fetch():
    if DAILY.exists():
        print("bars already cached")
        return
    import yfinance as yf
    idx, names, member = weekly_members()
    want = [names[j] for j in np.flatnonzero(member.any(axis=0))] + ["SPY"]
    print(f"{len(want) - 1} names were in the top {TOP} in some week since 2014", flush=True)
    frames = {}
    for i in range(0, len(want), 100):
        chunk = want[i:i + 100]
        df = None
        for attempt in range(3):
            try:
                df = yf.download([t.replace(".", "-") for t in chunk], start=START, end=END, interval="1d",
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
                if len(sub) > 60:
                    frames[t] = sub[["Open", "High", "Low", "Close", "Volume"]].astype("float32")
        print(f"{min(i + 100, len(want))}/{len(want)} names, {len(frames)} with bars", flush=True)
        time.sleep(1.0)
    with open(DAILY, "wb") as fh:
        pickle.dump(frames, fh)
    print(f"wrote {DAILY.name}: {len(frames)} names")


def draw(lc, lh, ll):
    """The Pass 41 channel on daily bars: the steepest line from the lowest
    low under every low since, with the facts the score needs."""
    n = len(lc)
    a = int(np.argmin(ll))
    age = n - 1 - a
    if age < min(AGES.values()) or age > AGE_MAX:
        return None
    t = np.arange(1, age + 1)
    b = float(((ll[a + 1:] - ll[a]) / t).min())
    line = ll[a] + b * np.arange(0, age + 1)
    top = float((lh[a:] - line).max())
    if top <= 0 or b <= 0:
        return None
    y = lc[a:]
    x = np.arange(len(y)) - (len(y) - 1) / 2.0
    d = y - y.mean()
    sst = float((d * d).sum())
    if sst <= 0:
        return None
    k = float((x * d).sum() / (x * x).sum())
    r2 = 1.0 - float(((d - k * x) ** 2).sum()) / sst
    touches, last = 0, 0
    for i in np.flatnonzero((ll[a:] - line) <= p52.TOUCH_BAND * top):
        if i >= 1 and i - last >= TOUCH_GAP:
            touches += 1
            last = int(i)
    return b, r2, top, age, touches


def stat(r):
    r = np.asarray(r, dtype=float)
    if len(r) < 60:
        return None
    c = np.cumprod(1.0 + r)
    sd = float(r.std(ddof=1))
    return {"cagr": float(c[-1] ** (252.0 / len(r)) - 1.0), "sharpe": float(r.mean() / sd * 252 ** 0.5) if sd > 0 else None,
            "max_drawdown": float((c / np.maximum.accumulate(c) - 1.0).min()), "mean_day": float(r.mean()), "days": int(len(r))}


def main(argv):
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "fetch":
        return fetch()
    smoke = mode == "smoke"
    import pandas as pd
    wk_idx, wk_names, wk_member = weekly_members()
    with open(DAILY, "rb") as fh:
        frames = pickle.load(fh)
    names = sorted(t for t in frames if t != "SPY" and t in set(wk_names))
    if smoke:
        names = names[::max(1, len(names) // 150)][:150]
    days = frames["SPY"].index
    D, n = len(days), len(names)
    dates = [d.date().isoformat() for d in days]

    def mat(col):
        return np.column_stack([frames[t][col].reindex(days).to_numpy(dtype=float) for t in names])
    O, H, L, C, V = mat("Open"), mat("High"), mat("Low"), mat("Close"), mat("Volume")
    spy_c = frames["SPY"]["Close"].to_numpy(dtype=float)
    print(f"{D} sessions {dates[0]} .. {dates[-1]}, {n} names", flush=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        lC, lH, lL = np.log(C), np.log(H), np.log(L)
        R_hold = C[1:] / C[:-1] - 1.0
        R_in = C[1:] / O[1:] - 1.0
        R_out = O[1:] / C[:-1] - 1.0
    Cdf = pd.DataFrame(C)
    hi252 = Cdf.rolling(252, min_periods=120).max().to_numpy()
    med_dv = (Cdf * pd.DataFrame(V)).rolling(252, min_periods=120).median().to_numpy()
    swing = pd.DataFrame(lC).diff().rolling(504, min_periods=200).std().to_numpy() * 5 ** 0.5
    with np.errstate(invalid="ignore", divide="ignore"):
        swings_off = (lC - np.log(hi252)) / swing
    tradeable = (C >= p43.PRICE_MIN) & (np.nan_to_num(med_dv) >= DV_MIN_DAY) & (np.nan_to_num(swing) >= p48.SWING_MIN)
    # size membership: the last finished week's top 500
    col = {t: j for j, t in enumerate(wk_names)}
    pick_cols = [col[t] for t in names]
    wk_of_day = np.clip(np.searchsorted(wk_idx.values, days.values, side="right") - 2, 0, len(wk_idx) - 1)
    if smoke:
        sub = wk_member[:, pick_cols]
        member_size = sub[wk_of_day]
    else:
        member_size = wk_member[wk_of_day][:, pick_cols]
    member = tradeable & member_size
    near_high = np.nan_to_num(swings_off, nan=-99.0) >= -p48.SWINGS_MAX

    d0 = next(i for i, d in enumerate(dates) if d >= BOOK_START)
    bad = np.isnan(lC) | np.isnan(lH) | np.isnan(lL)
    run = np.zeros((D, n), dtype=int)
    for d in range(D):
        run[d] = np.where(bad[d], 0, (run[d - 1] if d else 0) + 1)
    print("drawing channels ...", flush=True)
    T = {k: np.full((D, n), np.nan) for k in ("slope", "r2", "height", "age", "touches")}
    todo = member & near_high
    for j in range(n):
        for d in np.flatnonzero(todo[d0 - 1:, j]) + d0 - 1:
            m = min(LOOKBACK, int(run[d, j]))
            if m <= min(AGES.values()):
                continue
            ch = draw(lC[d - m + 1:d + 1, j], lH[d - m + 1:d + 1, j], lL[d - m + 1:d + 1, j])
            if ch:
                T["slope"][d, j], T["r2"][d, j], T["height"][d, j], T["age"][d, j], T["touches"][d, j] = ch
    channel = (np.nan_to_num(T["slope"], nan=-1.0) >= FLOOR) & (np.nan_to_num(T["r2"], nan=0.0) >= p48.R2_MIN)
    cands = {}
    for label, min_age in AGES.items():
        screen = todo & channel & (np.nan_to_num(T["age"], nan=0.0) >= min_age)
        for d in range(d0 - 1, D):
            js = np.flatnonzero(screen[d])
            if len(js) > 1:
                tight = T["height"][d, js] / (T["slope"][d, js] * T["age"][d, js])
                q = (p52.ranks(T["r2"][d, js]) + p52.ranks(-tight) + p52.ranks(T["age"][d, js]) + p52.ranks(T["touches"][d, js])) / 4.0
                js = js[np.argsort(-q, kind="stable")]
            cands[(label, d)] = js
    cold = np.array([d >= COLD_DAYS - 1 and spy_c[d] < spy_c[d - COLD_DAYS + 1:d + 1].mean() for d in range(D)])
    week_end = np.array([d == D - 1 or days[d + 1].isocalendar()[:2] != days[d].isocalendar()[:2] for d in range(D)])
    sim_days = list(range(d0 - 1, D - 1))                # decide on close d, earn day d+1
    ret_dates = [dates[d + 1] for d in sim_days]
    spy = [float(spy_c[d + 1] / spy_c[d] - 1.0) for d in sim_days]
    pool_ok = member[:-1] & ~np.isnan(R_hold)
    pool = [float(R_hold[d][pool_ok[d]].mean()) if pool_ok[d].any() else 0.0 for d in sim_days]
    slip = float(p43.TIERS[1][3])
    N = 4 if smoke else SLOTS

    def sim(acts, age_label, pick, rng=None, detail=False):
        held, rets, holds, n_buys, cash_days = {}, [], [], 0, 0      # j -> [entry day, high close]
        for d in sim_days:
            act = acts == "daily" or week_end[d] or (acts == "switch" and not cold[d])
            gone, new = [], []
            for j, st in list(held.items()):
                if np.isnan(C[d, j]) or np.isnan(R_hold[d, j]):
                    gone.append(j)
                    continue
                st[1] = max(st[1], C[d, j])
                if act and C[d, j] / st[1] - 1.0 <= -p52.OFF_HIGH:
                    gone.append(j)
            r = 0.0
            for j in gone:
                holds.append(d - held.pop(j)[0])
                r += (0.0 if np.isnan(R_out[d, j]) else R_out[d, j]) / N
            if act and len(held) < N and not cold[d]:
                cs = [int(j) for j in cands[(age_label, d)] if j not in held and j not in gone and not np.isnan(R_in[d, j])]
                free = N - len(held)
                new = cs[:free] if pick == "top" else [cs[i] for i in rng.permutation(len(cs))[:free]]
            for j in held:
                r += R_hold[d, j] / N
            for j in new:
                held[j] = [d, float(max(hi252[d, j], C[d, j]))]
                r += R_in[d, j] / N
            n_buys += len(new)
            cash_days += not held
            rets.append(float(r - (len(new) + len(gone)) * slip / N))
        if not detail:
            return rets
        yrs = len(sim_days) / 252.0
        return rets, {"buys_a_year": n_buys / yrs, "median_hold_sessions": float(np.median(holds)) if holds else None,
                      "days_all_cash": int(cash_days)}

    per_ix = {k: [i for i, d in enumerate(ret_dates) if a <= d < b] for k, (a, b) in PERIODS.items()}
    out = {"generated": dates[-1], "names": n, "sessions": len(sim_days), "first_day": ret_dates[0], "slots": N,
           "cold_share_of_days": float(np.mean([cold[d] for d in sim_days])),
           "median_names_on_screen": {a: float(np.median([len(cands[(a, d)]) for d in sim_days])) for a in AGES},
           "benchmarks": {nm: {k: stat([s_[i] for i in ix]) for k, ix in per_ix.items()} for nm, s_ in (("SPY", spy), ("pool", pool))},
           "books": {}}
    draws = 8 if smoke else DRAWS
    for acts, age_label in itertools.product(("weekly", "daily", "switch"), AGES):
        name = f"{acts} | {age_label}"
        rets, info = sim(acts, age_label, "top", detail=True)
        rng = np.random.default_rng(SEED)
        rand = np.array([sim(acts, age_label, "random", rng=rng) for _ in range(draws)])
        info["periods"] = {}
        for k, ix in per_ix.items():
            st = stat([rets[i] for i in ix])
            if st:
                st["percentile_among_random_books"] = float((rand[:, ix].mean(axis=1) < st["mean_day"]).mean() * 100.0)
                st["random_median_cagr"] = float(np.median(np.prod(1.0 + rand[:, ix], axis=1) ** (252.0 / len(ix)) - 1.0))
            info["periods"][k] = st
        by_year = {}
        for d_, a_, c_ in zip(ret_dates, rets, spy):
            y = by_year.setdefault(d_[:4], [1.0, 1.0])
            y[0] *= 1 + a_
            y[1] *= 1 + c_
        info["by_year"] = {y: {"arm": v[0] - 1, "spy": v[1] - 1} for y, v in by_year.items()}
        out["books"][name] = info
        print("done:", name, flush=True)

    def P(x, d=1):
        return "    --" if x is None else f"{100 * x:6.{d}f}%"
    print(f"cold days {P(out['cold_share_of_days'], 0).strip()}; median names on screen {out['median_names_on_screen']}")
    for k in PERIODS:
        s_, p_ = out["benchmarks"]["SPY"][k], out["benchmarks"]["pool"][k]
        if not s_:
            continue
        print(f"== {k}: SPY {P(s_['cagr'])} Sharpe {s_['sharpe']:.2f} DD {P(s_['max_drawdown'])} | pool {P(p_['cagr'])} Sharpe {p_['sharpe']:.2f} DD {P(p_['max_drawdown'])}")
        for nm, r in out["books"].items():
            b = r["periods"][k]
            if b:
                print(f"     {nm:20} {P(b['cagr'])} Sharpe {b['sharpe']:.2f} DD {P(b['max_drawdown'])} pct {b['percentile_among_random_books']:4.0f} random {P(b['random_median_cagr'])}")
    for nm, r in out["books"].items():
        print(f"{nm:20} buys/yr {r['buys_a_year']:.1f}  median hold {r['median_hold_sessions']} sessions  days all cash {r['days_all_cash']}  by year arm/spy: "
              + "  ".join(f"{y} {100 * v['arm']:+.0f}/{100 * v['spy']:+.0f}" for y, v in r["by_year"].items()))
    if not smoke:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main(sys.argv)
